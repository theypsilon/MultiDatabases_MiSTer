#!/usr/bin/env python3

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

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
    release_asset_url,
    write_bundle,
)


FOLDER = "brickboy-dmg"
UPSTREAM = "kandowontu/brickboy-dmg-fpgacore"
RBF_PATTERN = re.compile(r"BrickBoy_DMG\.rbf", re.IGNORECASE)


def select_rbf_asset(release: dict[str, Any]) -> dict[str, Any]:
    matches = []
    for asset in release.get("assets") or []:
        if not isinstance(asset, dict):
            continue
        name = str(asset.get("name") or "")
        url = str(asset.get("browser_download_url") or "")
        if RBF_PATTERN.fullmatch(name) and url.startswith("https://"):
            matches.append(asset)

    if len(matches) != 1:
        tag = release.get("tag_name") or release.get("name") or "unknown"
        raise RuntimeError(
            f"BrickBoy DMG release {tag} must contain exactly one "
            f"BrickBoy_DMG.rbf asset; found {len(matches)}"
        )
    return matches[0]


def main() -> int:
    args = generator_parser(
        FOLDER, "Generate the BrickBoy DMG database"
    ).parse_args()
    release = github_latest_release(UPSTREAM)
    asset = select_rbf_asset(release)
    rbf_url = release_asset_url(asset)
    rbf_data = http_get_bytes(rbf_url)

    mgl_path = Path(__file__).with_name("BrickBoy_DMG.mgl")
    mgl_url = github_raw_url(
        args.repository,
        git_file_revision(mgl_path),
        "brickboy-dmg/BrickBoy_DMG.mgl",
    )
    mgl_data = mgl_path.read_bytes()

    database = build_direct_database(
        folder=FOLDER,
        repository=args.repository,
        timestamp=generation_timestamp(args.timestamp),
        filter_terms=(FOLDER, "console", "gb", "gbc"),
        tag_aliases=((FOLDER, "brickboy"),),
        direct_files=(
            DirectFile(
                path="_Custom Cores/Cores/BrickBoy_DMG.rbf",
                url=rbf_url,
                data=rbf_data,
            ),
            DirectFile(
                path="Custom Cores/BrickBoy_DMG.mgl",
                url=mgl_url,
                data=mgl_data,
            ),
        ),
    )
    write_bundle(database, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
