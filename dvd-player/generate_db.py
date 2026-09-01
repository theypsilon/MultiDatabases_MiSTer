#!/usr/bin/env python3

"""Generate the DVD-Player database from its latest install release."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".github"))

from db_helpers import (  # noqa: E402
    ArchiveMember,
    build_selective_archive_database,
    generation_timestamp,
    generator_parser,
    github_latest_release,
    http_get_bytes,
    read_archive_members,
    release_asset_url,
    write_bundle,
)

FOLDER = "dvd-player"
UPSTREAM = "joedaniels198512-gif/dvd-core"
VERSION_PATTERN = r"\d+\.\d+\.\d+(?:-[0-9A-Za-z]+(?:\.[0-9A-Za-z]+)*)?"
ASSET_PATTERN = re.compile(rf"MiSTer_DVD_Player_({VERSION_PATTERN})\.zip", re.I)
TAG_PATTERN = re.compile(rf"v?({VERSION_PATTERN})", re.I)
INSTALL_FILES = {
    "DVD/VERSION",
    "DVD/bin/dvd_av_threaded_test",
    "DVD/bin/dvd_player",
    "DVD/lib/libdvdnav.so.4",
    "DVD/lib/libdvdnav.so.4.3.0",
    "DVD/lib/libdvdread.so.8",
    "DVD/lib/libdvdread.so.8.0.0",
    "MiSTer_DVD",
    "_Other/DVD_Player.rbf",
}
PLACEHOLDER_FILES = {
    "DVD/config/.keep",
    "DVD/logs/.keep",
    "games/DVD-Player/.keep",
}
EXPECTED_FILES = INSTALL_FILES | PLACEHOLDER_FILES


def unique_install_asset(release: Mapping[str, Any]) -> tuple[dict[str, Any], str]:
    matches: list[tuple[dict[str, Any], str]] = []
    for asset in release.get("assets") or []:
        if not isinstance(asset, dict):
            continue
        name = str(asset.get("name") or "")
        url = str(asset.get("browser_download_url") or "")
        match = ASSET_PATTERN.fullmatch(name)
        if match and url.startswith("https://"):
            matches.append((asset, match.group(1)))

    tag = str(release.get("tag_name") or release.get("name") or "unknown")
    if len(matches) != 1:
        raise RuntimeError(
            f"DVD-Player release {tag} must contain exactly one install ZIP; "
            f"found {len(matches)}"
        )
    asset, version = matches[0]
    tag_match = TAG_PATTERN.fullmatch(str(release.get("tag_name") or ""))
    if not tag_match or tag_match.group(1).lower() != version.lower():
        raise RuntimeError(
            f"DVD-Player release tag {tag} does not match install ZIP version {version}"
        )
    return asset, version


def selected_files(
    members: Sequence[ArchiveMember], version: str
) -> tuple[tuple[str, ArchiveMember], ...]:
    by_path = {member.path: member for member in members}
    unexpected = set(by_path) - EXPECTED_FILES
    missing = EXPECTED_FILES - set(by_path)
    if unexpected:
        raise RuntimeError(
            "DVD-Player ZIP contains unexpected files: "
            + ", ".join(sorted(unexpected))
        )
    if missing:
        raise RuntimeError(
            "DVD-Player ZIP is missing required files: " + ", ".join(sorted(missing))
        )
    packaged_version = by_path["DVD/VERSION"].data.decode("utf-8").strip()
    if packaged_version.lower() != version.lower():
        raise RuntimeError(
            f"DVD-Player VERSION is {packaged_version!r}, expected {version!r}"
        )
    for path in PLACEHOLDER_FILES:
        if by_path[path].data:
            raise RuntimeError(f"DVD-Player placeholder is not empty: {path}")
    return tuple((path, by_path[path]) for path in sorted(INSTALL_FILES))


def main() -> int:
    args = generator_parser(FOLDER, "Generate the DVD-Player database").parse_args()
    release = github_latest_release(UPSTREAM)
    asset, version = unique_install_asset(release)
    archive_url = release_asset_url(asset)
    archive_data = http_get_bytes(archive_url)
    selected = selected_files(read_archive_members(archive_data), version)
    database = build_selective_archive_database(
        folder=FOLDER,
        repository=args.repository,
        timestamp=generation_timestamp(args.timestamp),
        archive_url=archive_url,
        archive_data=archive_data,
        selected_files=selected,
        description=f"Installing DVD-Player {version}",
        filter_terms=(FOLDER, "other"),
        tag_aliases=(("dvd", FOLDER),),
        extra_folders=("DVD/config", "DVD/logs", "games/DVD-Player"),
    )
    write_bundle(database, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
