#!/usr/bin/env python3

from __future__ import annotations

import posixpath
import re
import sys
import zipfile
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".github"))

from db_helpers import (  # noqa: E402
    ArchiveMember,
    SelectiveArchive,
    build_multi_selective_archive_database,
    generation_timestamp,
    generator_parser,
    github_latest_release,
    http_get_bytes,
    read_archive_members,
    release_asset_url,
    write_bundle,
)


FOLDER = "mister-hifi"
UPSTREAM = "Anime0t4ku/MiSTer_Hi-Fi"
ARCHIVE_ID = "release"
SCRIPTS_FOLDER = "Scripts"
CONFIG_FOLDER = "Scripts/.config"
# Everything installs below /media/fat, so that is what absolute paths inside
# the launcher have to resolve to.
INSTALL_PREFIX = "/media/fat/"
# MiSTer Hi-Fi writes these itself: config.json holds the user's settings and
# smb.json their share credentials. The release only ships smb.example.json,
# and a release that started packing the real files would overwrite them on
# every downloader run.
USER_OWNED = ("config.json", "smb.json")

ASSIGNMENT = re.compile(
    r"^[ \t]*([A-Za-z_][A-Za-z0-9_]*)="
    r"""(?:"([^"\n]*)"|'([^'\n]*)'|([^\s;#]*))[ \t]*$""",
    re.MULTILINE,
)
VARIABLE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}|\$([A-Za-z_][A-Za-z0-9_]*)")
VERSION = re.compile(r"""^[ \t]*VERSION=["']?([^"'\s]+)""", re.MULTILINE)


def zip_assets(release: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    """Every ZIP of the release, so a renamed asset still gets picked up."""
    assets = tuple(
        asset
        for asset in release.get("assets") or []
        if isinstance(asset, dict)
        and str(asset.get("name") or "").lower().endswith(".zip")
    )
    if not assets:
        tag = release.get("tag_name") or release.get("name") or "unknown"
        raise RuntimeError(f"{UPSTREAM} release {tag} does not contain a ZIP asset")
    return assets


def validate_binary(path: str, data: bytes) -> None:
    if not data.startswith(b"\x7fELF"):
        raise RuntimeError(f"{path} is not an ELF binary")
    # 32-bit, little-endian, EM_ARM: what the MiSTer's ARMv7 userland runs.
    if data[4:6] != b"\x01\x01" or data[18:20] != b"\x28\x00":
        raise RuntimeError(f"{path} is not a 32-bit little-endian ARM binary")
    if not 500_000 < len(data) < 64_000_000:
        raise RuntimeError(f"{path} has an implausible size: {len(data)}")


def expand_shell_variables(text: str) -> str:
    """Resolve the launcher's own `NAME=value` assignments inside its text."""
    values: dict[str, str] = {}

    def expand(raw: str) -> str:
        return VARIABLE.sub(
            lambda match: values.get(match.group(1) or match.group(2), match.group(0)),
            raw,
        )

    for match in ASSIGNMENT.finditer(text):
        raw = next(group for group in match.groups()[1:] if group is not None)
        values[match.group(1)] = expand(raw)

    return expand(text)


def launcher_version(text: str) -> str:
    match = VERSION.search(text)
    return match.group(1) if match else "unknown"


def application_folder(binary_path: str) -> str:
    """The app folder the release picked under Scripts/.config."""
    folder = posixpath.dirname(binary_path)
    if posixpath.dirname(folder) != CONFIG_FOLDER:
        raise RuntimeError(
            f"MiSTer Hi-Fi binary must sit in a {CONFIG_FOLDER}/<app> folder: "
            f"{binary_path}"
        )
    return folder


def selected_files(
    members: Sequence[ArchiveMember],
) -> tuple[tuple[str, ArchiveMember], ...]:
    """Validate the release layout and install every file it publishes."""
    outside = sorted(
        member.path
        for member in members
        if not member.path.startswith(f"{SCRIPTS_FOLDER}/")
    )
    if outside:
        raise RuntimeError(
            f"MiSTer Hi-Fi ZIP installs outside {SCRIPTS_FOLDER}/: "
            + ", ".join(outside)
        )

    launchers = [
        member
        for member in members
        if posixpath.dirname(member.path) == SCRIPTS_FOLDER
        and member.path.lower().endswith(".sh")
    ]
    if len(launchers) != 1:
        raise RuntimeError(
            f"MiSTer Hi-Fi ZIP must ship exactly one {SCRIPTS_FOLDER}/*.sh "
            "launcher, found: "
            + (", ".join(sorted(member.path for member in launchers)) or "none")
        )
    launcher = launchers[0]
    if not launcher.data.startswith(b"#!"):
        raise RuntimeError(f"MiSTer Hi-Fi launcher is not a script: {launcher.path}")

    binaries = [member for member in members if member.data.startswith(b"\x7fELF")]
    if len(binaries) != 1:
        raise RuntimeError(
            "MiSTer Hi-Fi ZIP must ship exactly one ARM binary, found: "
            + (", ".join(sorted(member.path for member in binaries)) or "none")
        )
    binary = binaries[0]
    validate_binary(binary.path, binary.data)
    app_folder = application_folder(binary.path)

    stray = sorted(
        member.path
        for member in members
        if member.path != launcher.path
        and not member.path.startswith(f"{app_folder}/")
    )
    if stray:
        raise RuntimeError(
            f"MiSTer Hi-Fi ZIP installs outside {app_folder}/: " + ", ".join(stray)
        )

    packaged_user_files = sorted(
        member.path
        for member in members
        if member.path in {f"{app_folder}/{name}" for name in USER_OWNED}
    )
    if packaged_user_files:
        raise RuntimeError(
            "MiSTer Hi-Fi ZIP ships files the application owns, which would "
            "overwrite the user's settings and SMB credentials: "
            + ", ".join(packaged_user_files)
        )

    # The launcher runs the binary from its absolute install path, so that path
    # has to be exactly where this database installs it. The lookarounds keep a
    # neighbouring path such as mister_hifi_debug from passing as a match.
    expected = f"{INSTALL_PREFIX}{binary.path}"
    reference = re.compile(rf"(?<![\w./-]){re.escape(expected)}(?![\w./-])")
    if not reference.search(
        expand_shell_variables(launcher.data.decode("utf-8", "replace"))
    ):
        raise RuntimeError(
            f"MiSTer Hi-Fi launcher {launcher.path} does not run {expected}"
        )

    return tuple(
        (member.path, member)
        for member in sorted(members, key=lambda member: member.path)
    )


def release_archive(release: dict[str, Any]) -> SelectiveArchive:
    tag = str(release.get("tag_name") or release.get("name") or "unknown")
    compatible: list[SelectiveArchive] = []
    rejected: list[str] = []

    for asset in zip_assets(release):
        name = str(asset.get("name") or "unnamed ZIP")
        try:
            archive_url = release_asset_url(asset)
            archive_data = http_get_bytes(archive_url)
            files = selected_files(read_archive_members(archive_data))
        except (RuntimeError, zipfile.BadZipFile) as exc:
            rejected.append(f"{name}: {exc}")
            continue

        launcher = next(
            member for destination, member in files if destination.endswith(".sh")
        )
        version = launcher_version(launcher.data.decode("utf-8", "replace"))
        print(f"MiSTer Hi-Fi {tag} ({name}) declares version {version}", flush=True)
        compatible.append(
            SelectiveArchive(
                archive_id=ARCHIVE_ID,
                url=archive_url,
                data=archive_data,
                selected_files=files,
                description=f"Installing MiSTer Hi-Fi {tag}",
            )
        )

    if len(compatible) == 1:
        return compatible[0]
    if len(compatible) > 1:
        raise RuntimeError(
            f"{UPSTREAM} release {tag} contains multiple compatible ZIP assets"
        )
    raise RuntimeError(
        f"{UPSTREAM} release {tag} has no compatible ZIP asset: " + "; ".join(rejected)
    )


def main() -> int:
    args = generator_parser(
        FOLDER, "Generate the MiSTer Hi-Fi database"
    ).parse_args()
    database = build_multi_selective_archive_database(
        folder=FOLDER,
        repository=args.repository,
        timestamp=generation_timestamp(args.timestamp),
        archives=(release_archive(github_latest_release(UPSTREAM)),),
        filter_terms=(FOLDER, "utility"),
        tag_aliases=((FOLDER, "hifi"),),
    )
    write_bundle(database, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
