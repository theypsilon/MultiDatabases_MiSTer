#!/usr/bin/env python3

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".github"))

from db_helpers import (  # noqa: E402
    ArchiveMember,
    build_selective_archive_database,
    generation_timestamp,
    generator_parser,
    github_latest_release,
    http_get_bytes,
    matching_release_asset,
    read_archive_members,
    release_asset_url,
    validate_arm_binary,
    write_bundle,
)


FOLDER = "mister-vision"
UPSTREAM = "trentnix/mistervision"
# Each release ships a progressive and an interlaced ZIP with the same binaries
# and core. They differ only in the display mode the launcher seeds on a first
# run, and upstream documents progressive as the default, so that is the one
# followed here. 480i stays one settings.json switch away.
ASSET_PATTERN = re.compile(
    r"mistervision-(v\d+(?:\.\d+)+)-progressive\.zip", re.IGNORECASE
)
ARCHIVE_ROOT = "mistervision/"
LAUNCHER = "Scripts/MiSTerVision.sh"
VERSION_FILE = "mistervision/VERSION"
# Install notes and the checksum list for the extracted tree: reading material
# for a manual install, nothing the MiSTer runs.
ARCHIVE_DOCS = frozenset({"INSTALL.txt", "SHA256SUMS"})
ARM_BINARIES = (
    "mistervision/mistervision",
    "mistervision/mplayer-arm",
)
REQUIRED = (
    LAUNCHER,
    VERSION_FILE,
    # The app loads this Menu core itself when 480i output is enabled.
    "mistervision/InterlacedMenu.rbf",
    *ARM_BINARIES,
)
# The app writes these next to its binaries: server address, linked accounts,
# display mode and playback state. A packaged copy would overwrite them on
# every downloader run.
USER_OWNED = (
    "mistervision/settings.json",
    "mistervision/jellyfin.conf",
    "mistervision/state/",
)


def is_user_owned(path: str) -> bool:
    return any(
        path.startswith(owned) if owned.endswith("/") else path == owned
        for owned in USER_OWNED
    )


def selected_files(
    members: Sequence[ArchiveMember],
    version: str,
) -> tuple[tuple[str, ArchiveMember], ...]:
    """Validate the release layout and install every file meant for MiSTer."""
    installable = [
        member for member in members if member.path not in ARCHIVE_DOCS
    ]

    unexpected = sorted(
        member.path
        for member in installable
        if member.path != LAUNCHER and not member.path.startswith(ARCHIVE_ROOT)
    )
    if unexpected:
        raise RuntimeError(
            f"MiSTerVision ZIP installs outside {ARCHIVE_ROOT} and {LAUNCHER}: "
            + ", ".join(unexpected)
        )

    user_owned = sorted(
        member.path for member in installable if is_user_owned(member.path)
    )
    if user_owned:
        raise RuntimeError(
            "MiSTerVision ZIP ships files that would overwrite the user's own "
            "settings and saved state: " + ", ".join(user_owned)
        )

    by_path = {member.path: member for member in installable}
    missing = sorted(set(REQUIRED).difference(by_path))
    if missing:
        raise RuntimeError(
            "MiSTerVision ZIP is missing required files: " + ", ".join(missing)
        )

    packaged_version = by_path[VERSION_FILE].data.decode("utf-8", "replace").strip()
    if packaged_version != version:
        raise RuntimeError(
            f"MiSTerVision ZIP is named {version} but packages {packaged_version!r}"
        )

    for path in ARM_BINARIES:
        validate_arm_binary(path, by_path[path].data)

    return tuple((path, by_path[path]) for path in sorted(by_path))


def main() -> int:
    args = generator_parser(FOLDER, "Generate the MiSTerVision database").parse_args()
    release = github_latest_release(UPSTREAM)
    asset = matching_release_asset(release, ASSET_PATTERN)
    archive_url = release_asset_url(asset)
    archive_data = http_get_bytes(archive_url)
    members = read_archive_members(archive_data)

    version = ASSET_PATTERN.fullmatch(str(asset["name"])).group(1)
    database = build_selective_archive_database(
        folder=FOLDER,
        repository=args.repository,
        timestamp=generation_timestamp(args.timestamp),
        archive_url=archive_url,
        archive_data=archive_data,
        selected_files=selected_files(members, version),
        description=f"Installing MiSTerVision {version}",
        filter_terms=(FOLDER, "utility"),
        tag_aliases=((FOLDER, "jellyfin", "plex"),),
    )
    write_bundle(database, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
