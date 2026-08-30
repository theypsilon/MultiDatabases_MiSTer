#!/usr/bin/env python3

from __future__ import annotations

import re
import sys
from pathlib import Path

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


FOLDER = "mister-dvd"
UPSTREAM = "owenb321/MiSTer_DVD"
ASSET_PATTERN = re.compile(r"MiSTer_DVD_(v\d+\.\d+\.\d+)\.zip", re.IGNORECASE)
CORE_PATTERN = re.compile(r"DVD_\d{8}\.rbf", re.IGNORECASE)
FIXED_FILES = {
    "DVD_INSTALL.txt",
    "MiSTer_DVDcss",
    "Scripts/install_dvdcss.sh",
}


def selected_files(members):
    selected = []
    core_paths = []
    unexpected = []

    for member in members:
        if CORE_PATTERN.fullmatch(member.path.removeprefix("_Other/")):
            if not member.path.startswith("_Other/"):
                unexpected.append(member.path)
                continue
            core_paths.append(member.path)
            selected.append((member.path, member))
        elif member.path in FIXED_FILES:
            selected.append((member.path, member))
        else:
            unexpected.append(member.path)

    if unexpected:
        raise RuntimeError(
            "MiSTer DVD ZIP contains unexpected files: "
            + ", ".join(sorted(unexpected))
        )
    if len(core_paths) != 1:
        raise RuntimeError(
            "MiSTer DVD ZIP must contain exactly one _Other/DVD_YYYYMMDD.rbf"
        )

    names = {destination for destination, _ in selected}
    missing = FIXED_FILES - names
    if missing:
        raise RuntimeError(
            "MiSTer DVD ZIP is missing required files: "
            + ", ".join(sorted(missing))
        )
    return sorted(selected, key=lambda item: item[0])


def main() -> int:
    args = generator_parser(FOLDER, "Generate the MiSTer DVD database").parse_args()
    release = github_latest_release(UPSTREAM)
    asset = matching_release_asset(release, ASSET_PATTERN)
    archive_url = release_asset_url(asset)
    archive_data = http_get_bytes(archive_url)
    members = read_archive_members(archive_data)
    selected = selected_files(members)

    version = ASSET_PATTERN.fullmatch(str(asset["name"])).group(1)
    database = build_selective_archive_database(
        folder=FOLDER,
        repository=args.repository,
        timestamp=generation_timestamp(args.timestamp),
        archive_url=archive_url,
        archive_data=archive_data,
        selected_files=selected,
        description=f"Installing MiSTer DVD {version}",
        filter_terms=(FOLDER, "other", "scripts"),
        tag_aliases=((FOLDER, "dvd"),),
    )
    write_bundle(database, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
