#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import re
import sys
import zlib
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".github"))

from db_helpers import (  # noqa: E402
    ArchiveMember,
    build_selective_archive_database,
    generation_timestamp,
    generator_parser,
    github_releases,
    http_get_bytes,
    read_archive_members,
    release_asset_url,
    release_tag,
    write_bundle,
)


FOLDER = "sm64-h2x"
UPSTREAM = "DavidFallows/sm64"
INSTALL_FOLDER = "games/N64/SM64 H2X"

VERSION = r"v\d+(?:\.\d+)+(?:-[0-9A-Za-z]+(?:[.-][0-9A-Za-z]+)*)?"
PATCH_VERSION = r"v\d+(?:\.\d+)+(?:[ -][0-9A-Za-z]+(?:[. -][0-9A-Za-z]+)*)?"
TAG_PATTERN = re.compile(VERSION, re.IGNORECASE)
ASSET_PATTERN = re.compile(
    rf"SM64-H2X-Hi-res-Hack-dataDave-({VERSION})\.zip",
    re.IGNORECASE,
)
PATCH_PATTERN = re.compile(
    rf"SM64 - H2X Hi-res \(Hack\) dataDave ({PATCH_VERSION})\.bps",
    re.IGNORECASE,
)

# Upstream's first public build is intentionally marked as a release candidate.
# Follow non-draft prereleases as a reviewed policy so this entry can track it
# and later release candidates instead of remaining empty until a stable build.
FOLLOW_PRERELEASES = True

MIN_ARCHIVE_SIZE = 100_000
MAX_ARCHIVE_SIZE = 5_000_000
EXPECTED_SOURCE_SIZE = 8 * 1024 * 1024
EXPECTED_TARGET_SIZE = 8 * 1024 * 1024
# CRC-32 embedded by BPS for the documented clean Super Mario 64 (USA) .z64
# source whose SHA-1 is 9bef1128717f958171a4afac3ed78ee2bb4e86ce.
CLEAN_ROM_CRC32 = 0x3CE60709


def publication_date(release: Mapping[str, Any]) -> str:
    value = str(release.get("published_at") or "")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value):
        raise RuntimeError(
            f"{UPSTREAM} release {release_tag(release)} has an invalid "
            f"publication date: {value or 'missing'}"
        )
    return value


def release_asset(release: Mapping[str, Any]) -> dict[str, Any]:
    """Return the one versioned H2X ZIP and tie it to its release tag."""
    tag = release_tag(release)
    if not TAG_PATTERN.fullmatch(tag):
        raise RuntimeError(f"SM64 H2X release has an invalid tag: {tag}")

    matches: list[tuple[dict[str, Any], re.Match[str]]] = []
    for value in release.get("assets") or []:
        if not isinstance(value, dict):
            continue
        match = ASSET_PATTERN.fullmatch(str(value.get("name") or ""))
        if match is not None:
            matches.append((value, match))

    if len(matches) != 1:
        shipped = ", ".join(
            sorted(
                str(value.get("name") or "unnamed asset")
                for value in release.get("assets") or []
                if isinstance(value, dict)
            )
        ) or "none"
        raise RuntimeError(
            f"SM64 H2X release {tag} must publish exactly one versioned H2X "
            f"ZIP, found: {shipped}"
        )

    asset, match = matches[0]
    if match.group(1).casefold() != tag.casefold():
        raise RuntimeError(
            "SM64 H2X release tag and bundle version differ: "
            f"{tag} vs {asset.get('name') or 'unnamed asset'}"
        )

    url = release_asset_url(asset)
    expected_url = (
        f"https://github.com/{UPSTREAM}/releases/download/{tag}/"
        f"{asset['name']}"
    )
    if url != expected_url:
        raise RuntimeError(
            f"SM64 H2X bundle URL does not belong to release {tag}: {url}"
        )
    return asset


def select_release_asset(
    releases: Sequence[Mapping[str, Any]],
) -> tuple[Mapping[str, Any], dict[str, Any]]:
    """Follow the newest published release, including reviewed prereleases."""
    published = [
        release
        for release in releases
        if not release.get("draft")
        and (FOLLOW_PRERELEASES or not release.get("prerelease"))
    ]
    if not published:
        raise RuntimeError(f"No published {UPSTREAM} release found")

    newest_date = max(publication_date(release) for release in published)
    newest = [
        release for release in published if publication_date(release) == newest_date
    ]
    if len(newest) != 1:
        raise RuntimeError(
            f"Multiple {UPSTREAM} releases share the newest publication date "
            f"{newest_date}"
        )

    release = newest[0]
    return release, release_asset(release)


def validate_archive_download(asset: Mapping[str, Any], data: bytes) -> None:
    if asset.get("state") != "uploaded":
        raise RuntimeError("SM64 H2X release bundle is not fully uploaded")
    if asset.get("content_type") != "application/zip":
        raise RuntimeError(
            "SM64 H2X release bundle does not have the application/zip type"
        )

    size = asset.get("size")
    if not isinstance(size, int) or isinstance(size, bool):
        raise RuntimeError("SM64 H2X release bundle has no integer size")
    if not MIN_ARCHIVE_SIZE <= size <= MAX_ARCHIVE_SIZE:
        raise RuntimeError(
            f"SM64 H2X release bundle has an implausible size: {size}"
        )
    if len(data) != size:
        raise RuntimeError(
            "SM64 H2X release bundle size differs from GitHub metadata: "
            f"expected {size}, downloaded {len(data)}"
        )

    digest = str(asset.get("digest") or "")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        raise RuntimeError(
            f"SM64 H2X release bundle has an invalid SHA-256 digest: "
            f"{digest or 'missing'}"
        )
    if hashlib.sha256(data).hexdigest() != digest.removeprefix("sha256:"):
        raise RuntimeError(
            "SM64 H2X release bundle does not match its GitHub SHA-256 digest"
        )


def read_bps_number(data: bytes, offset: int, limit: int) -> tuple[int, int]:
    value = 0
    shift = 1
    while offset < limit:
        byte = data[offset]
        offset += 1
        value += (byte & 0x7F) * shift
        if byte & 0x80:
            return value, offset
        shift <<= 7
        value += shift
    raise RuntimeError("SM64 H2X BPS patch has a truncated variable-length number")


def read_bps_offset(data: bytes, offset: int, limit: int) -> tuple[int, int]:
    value, offset = read_bps_number(data, offset, limit)
    distance = value >> 1
    return (-distance if value & 1 else distance), offset


def validate_bps_patch(data: bytes) -> None:
    """Validate the BPS stream and its clean-ROM source fingerprint."""
    if len(data) < 19 or not data.startswith(b"BPS1"):
        raise RuntimeError("SM64 H2X patch is not a BPS1 file")

    payload_end = len(data) - 12
    offset = 4
    source_size, offset = read_bps_number(data, offset, payload_end)
    target_size, offset = read_bps_number(data, offset, payload_end)
    metadata_size, offset = read_bps_number(data, offset, payload_end)
    if source_size != EXPECTED_SOURCE_SIZE:
        raise RuntimeError(
            f"SM64 H2X patch expects an unexpected source size: {source_size}"
        )
    if target_size != EXPECTED_TARGET_SIZE:
        raise RuntimeError(
            f"SM64 H2X patch produces an unexpected target size: {target_size}"
        )
    if offset + metadata_size > payload_end:
        raise RuntimeError("SM64 H2X BPS patch has truncated metadata")
    offset += metadata_size

    output_offset = 0
    source_relative = 0
    target_relative = 0
    while offset < payload_end:
        command, offset = read_bps_number(data, offset, payload_end)
        action = command & 3
        length = (command >> 2) + 1
        if output_offset + length > target_size:
            raise RuntimeError("SM64 H2X BPS action exceeds its target size")

        if action == 0:  # SourceRead uses the output position as its source.
            if output_offset + length > source_size:
                raise RuntimeError("SM64 H2X BPS SourceRead exceeds its source")
        elif action == 1:  # TargetRead stores literal bytes in the patch.
            if offset + length > payload_end:
                raise RuntimeError("SM64 H2X BPS TargetRead data is truncated")
            offset += length
        elif action == 2:  # SourceCopy uses a signed relative source offset.
            change, offset = read_bps_offset(data, offset, payload_end)
            source_relative += change
            if source_relative < 0 or source_relative + length > source_size:
                raise RuntimeError("SM64 H2X BPS SourceCopy exceeds its source")
            source_relative += length
        else:  # TargetCopy may overlap, but must begin in produced output.
            change, offset = read_bps_offset(data, offset, payload_end)
            target_relative += change
            if target_relative < 0 or target_relative >= output_offset:
                raise RuntimeError(
                    "SM64 H2X BPS TargetCopy does not reference produced output"
                )
            target_relative += length
        output_offset += length

    if offset != payload_end or output_offset != target_size:
        raise RuntimeError("SM64 H2X BPS patch does not produce its target size")

    source_crc = int.from_bytes(data[-12:-8], "little")
    if source_crc != CLEAN_ROM_CRC32:
        raise RuntimeError(
            "SM64 H2X BPS patch does not target the reviewed clean USA .z64 ROM"
        )
    expected_patch_crc = int.from_bytes(data[-4:], "little")
    if zlib.crc32(data[:-4]) != expected_patch_crc:
        raise RuntimeError("SM64 H2X BPS patch has an invalid patch checksum")


def normalized_version(value: str) -> str:
    return re.sub(r"[ _-]+", "-", value).casefold()


def selected_files(
    members: Sequence[ArchiveMember], tag: str
) -> list[tuple[str, ArchiveMember]]:
    """Validate the release layout and map it to stable MiSTer paths."""
    if len(members) != 3:
        raise RuntimeError(
            "SM64 H2X release ZIP must contain exactly three files, found: "
            + ", ".join(sorted(member.path for member in members))
        )

    split_paths = [member.path.split("/") for member in members]
    if any(len(parts) != 2 for parts in split_paths):
        raise RuntimeError("SM64 H2X release files must share one top-level folder")
    roots = {parts[0] for parts in split_paths}
    if len(roots) != 1:
        raise RuntimeError("SM64 H2X release files do not share one top-level folder")

    by_name = {parts[1]: member for parts, member in zip(split_paths, members)}
    if len(by_name) != len(members):
        raise RuntimeError("SM64 H2X release ZIP contains duplicate filenames")

    patch_matches = [
        (name, match)
        for name in by_name
        if (match := PATCH_PATTERN.fullmatch(name)) is not None
    ]
    if len(patch_matches) != 1:
        raise RuntimeError(
            "SM64 H2X release ZIP must contain exactly one versioned BPS patch"
        )
    patch_name, match = patch_matches[0]
    if normalized_version(match.group(1)) != normalized_version(tag):
        raise RuntimeError(
            f"SM64 H2X release tag and patch version differ: {tag} vs {patch_name}"
        )
    if next(iter(roots)) != patch_name.removesuffix(".bps"):
        raise RuntimeError(
            "SM64 H2X release folder name does not match its BPS patch name"
        )

    required = {patch_name, "README.txt", "CHANGELOG.txt"}
    if set(by_name) != required:
        raise RuntimeError(
            "SM64 H2X release ZIP has an unexpected file layout: "
            + ", ".join(sorted(by_name))
        )
    validate_bps_patch(by_name[patch_name].data)

    return [
        (f"{INSTALL_FOLDER}/README.txt", by_name["README.txt"]),
        (f"{INSTALL_FOLDER}/SM64 H2X.bps", by_name[patch_name]),
    ]


def main() -> int:
    args = generator_parser(FOLDER, "Generate the SM64 H2X database").parse_args()
    release, asset = select_release_asset(github_releases(UPSTREAM))
    archive_url = release_asset_url(asset)
    archive_data = http_get_bytes(archive_url)
    validate_archive_download(asset, archive_data)
    tag = release_tag(release)
    selected = selected_files(read_archive_members(archive_data), tag)

    database = build_selective_archive_database(
        folder=FOLDER,
        repository=args.repository,
        timestamp=generation_timestamp(args.timestamp),
        archive_url=archive_url,
        archive_data=archive_data,
        selected_files=selected,
        description=f"Installing SM64 H2X {tag}",
        filter_terms=(FOLDER, "console", "n64"),
    )
    write_bundle(database, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
