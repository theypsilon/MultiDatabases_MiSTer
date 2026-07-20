#!/usr/bin/env python3

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".github"))

from db_helpers import (  # noqa: E402
    DirectFile,
    build_direct_database,
    generation_timestamp,
    generator_parser,
    git_file_revision,
    github_latest_release,
    github_raw_url,
    http_get_bytes,
    matching_release_asset,
    release_asset_url,
    write_bundle,
)


FOLDER = "paprium"
UPSTREAM = "MisterPezz82/Paprium_MegaDrive_MiSTer"
ASSET_PATTERN = re.compile(r"MegaDrive_Paprium_(\d{8})\.rbf", re.IGNORECASE)


def main() -> int:
    args = generator_parser(FOLDER, "Generate the Paprium MegaDrive database").parse_args()
    release = github_latest_release(UPSTREAM)
    asset = matching_release_asset(release, ASSET_PATTERN, highest_match=True)
    rbf_url = release_asset_url(asset)
    rbf_data = http_get_bytes(rbf_url)
    mgl_path = Path(__file__).with_name("PapriumMD.mgl")
    mgl_url = github_raw_url(
        args.repository,
        git_file_revision(mgl_path),
        "paprium/PapriumMD.mgl",
    )
    mgl_data = mgl_path.read_bytes()
    filename = str(asset["name"])

    database = build_direct_database(
        folder=FOLDER,
        repository=args.repository,
        timestamp=generation_timestamp(args.timestamp),
        filter_terms=(FOLDER, "console", "megadrive"),
        tag_aliases=((FOLDER, "papriummd", "megadrive-paprium"),),
        direct_files=(
            DirectFile(
                path=f"_Custom Cores/Cores/{filename}",
                url=rbf_url,
                data=rbf_data,
                reboot=True,
                tangles=("paprium_megadrive_core",),
            ),
            DirectFile(
                path="_Custom Cores/PapriumMD.mgl",
                url=mgl_url,
                data=mgl_data,
            ),
        ),
        extra_folders=("games/PapriumMD",),
    )
    write_bundle(database, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
