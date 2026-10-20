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
    write_bundle,
)


FOLDER = "misteremby"
UPSTREAM = "freemchr/MiSTerEmby"
ASSET_PATTERN = re.compile(r"misteremby-(v\d+(?:\.\d+)+)\.zip", re.IGNORECASE)
ARCHIVE_ROOT = "misteremby/"
LAUNCHER = "misteremby/MiSTerEmby.sh"
# The user writes their own emby.conf next to the app (server URL, and possibly
# a password or API key), and the app saves the sign-in to token.conf and a
# per-MiSTer id to device.conf. A packaged copy of any of them would overwrite
# the user's on every downloader run.
USER_FILES = (
    "misteremby/emby.conf",
    "misteremby/token.conf",
    "misteremby/device.conf",
)
REQUIRED = (
    LAUNCHER,
    "misteremby/font/font.desc",
    "misteremby/misteremby-arm",
    "misteremby/mplayer-arm",
    "misteremby/subfont/font.desc",
)


def destination_for(member_path: str) -> str:
    if member_path == LAUNCHER:
        # The app tree installs under /media/fat/misteremby, but the launcher
        # only reaches the MiSTer menu from Scripts.
        return "Scripts/MiSTerEmby.sh"
    return member_path


def selected_files(
    members: Sequence[ArchiveMember],
) -> tuple[tuple[str, ArchiveMember], ...]:
    """Validate the release layout and install every file it publishes."""
    outside = sorted(
        member.path
        for member in members
        if not member.path.startswith(ARCHIVE_ROOT)
    )
    if outside:
        raise RuntimeError(
            f"MiSTerEmby ZIP installs outside {ARCHIVE_ROOT}: " + ", ".join(outside)
        )

    shipped = sorted(member.path for member in members if member.path in USER_FILES)
    if shipped:
        raise RuntimeError(
            "MiSTerEmby ZIP ships " + ", ".join(shipped) + ", which would "
            "overwrite the user's own server settings and sign-in"
        )

    missing = sorted(set(REQUIRED).difference(member.path for member in members))
    if missing:
        raise RuntimeError(
            "MiSTerEmby ZIP is missing required files: " + ", ".join(missing)
        )

    return tuple(
        (destination_for(member.path), member)
        for member in sorted(members, key=lambda member: member.path)
    )


def main() -> int:
    args = generator_parser(FOLDER, "Generate the MiSTerEmby database").parse_args()
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
        selected_files=selected_files(members),
        description=f"Installing MiSTerEmby {version}",
        filter_terms=(FOLDER, "utility"),
        tag_aliases=((FOLDER, "emby"),),
        # One JSON entry per bundled asset: far past the 10 KB threshold.
        compressed_db_url=True,
    )
    write_bundle(database, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
