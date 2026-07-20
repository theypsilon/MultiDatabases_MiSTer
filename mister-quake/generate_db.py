#!/usr/bin/env python3

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".github"))

from db_helpers import (  # noqa: E402
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


FOLDER = "mister-quake"
UPSTREAM = "neofreno/Mister_Quake"
ASSET_PATTERN = re.compile(r"MiSTer_Quake_(\d{8})\.zip", re.IGNORECASE)


def main() -> int:
    args = generator_parser(FOLDER, "Generate the MiSTer Quake database").parse_args()
    release = github_latest_release(UPSTREAM)
    asset = matching_release_asset(release, ASSET_PATTERN, highest_match=True)
    archive_url = release_asset_url(asset)
    archive_data = http_get_bytes(archive_url)
    members = read_archive_members(archive_data)

    selected = [
        (member.path, member)
        for member in members
        if Path(member.path).name.lower() not in {"pak0.pak", "pak1.pak"}
    ]
    names = {destination.lower() for destination, _ in selected}
    required = {
        "mister_quake",
        "_other/quake.rbf",
        "games/quake/bin/quake-mister",
    }
    if not required.issubset(names):
        raise RuntimeError("MiSTer Quake ZIP is missing required files")

    version = ASSET_PATTERN.fullmatch(str(asset["name"])).group(1)
    database = build_selective_archive_database(
        folder=FOLDER,
        repository=args.repository,
        timestamp=generation_timestamp(args.timestamp),
        archive_url=archive_url,
        archive_data=archive_data,
        selected_files=selected,
        description=f"Installing MiSTer Quake {version}",
        filter_terms=(FOLDER, "other"),
        tag_aliases=((FOLDER, "quake"),),
    )
    write_bundle(database, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
