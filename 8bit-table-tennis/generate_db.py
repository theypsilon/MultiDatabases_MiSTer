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
    github_latest_release,
    http_get_bytes,
    matching_release_asset,
    release_asset_url,
    write_bundle,
)


FOLDER = "8bit-table-tennis"
UPSTREAM = "mike42/8bit-table-tennis"
ASSET_PATTERN = re.compile(r"table_tennis_v?(.+)\.nes", re.IGNORECASE)


def main() -> int:
    args = generator_parser(
        FOLDER, "Generate the 8-Bit Table Tennis database"
    ).parse_args()
    release = github_latest_release(UPSTREAM)
    asset = matching_release_asset(release, ASSET_PATTERN)
    rom_url = release_asset_url(asset)
    rom_data = http_get_bytes(rom_url)
    filename = str(asset["name"])

    database = build_direct_database(
        folder=FOLDER,
        repository=args.repository,
        timestamp=generation_timestamp(args.timestamp),
        filter_terms=(FOLDER, "console", "nes"),
        direct_files=(
            DirectFile(
                path=f"games/NES/{filename}",
                url=rom_url,
                data=rom_data,
                tangles=("8bit_table_tennis_rom",),
            ),
        ),
    )
    write_bundle(database, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
