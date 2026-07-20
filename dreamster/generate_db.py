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
    github_releases,
    http_get_bytes,
    read_archive_members,
    release_asset_url,
    write_bundle,
)


FOLDER = "dreamster"
UPSTREAM = "skmp/DreamSTer"
PREFERRED_ASSET = re.compile(r"DreamSTer-.*\.zip", re.IGNORECASE)


def select_release_asset():
    for release in github_releases(UPSTREAM):
        if release.get("draft"):
            continue
        assets = [
            asset
            for asset in release.get("assets") or []
            if str(asset.get("browser_download_url") or "").startswith("https://")
            and str(asset.get("name") or "").lower().endswith(".zip")
        ]
        preferred = sorted(
            (asset for asset in assets if PREFERRED_ASSET.fullmatch(str(asset["name"]))),
            key=lambda asset: str(asset["name"]).lower(),
        )
        fallback = sorted(
            (
                asset
                for asset in assets
                if "dreamster" in str(asset.get("name") or "").lower()
            ),
            key=lambda asset: str(asset["name"]).lower(),
        )
        candidates = preferred or fallback
        if candidates:
            return release, candidates[0]
    raise RuntimeError("No published DreamSTer release contains a ZIP asset")


def main() -> int:
    args = generator_parser(FOLDER, "Generate the DreamSTer database").parse_args()
    release, asset = select_release_asset()
    archive_url = release_asset_url(asset)
    archive_data = http_get_bytes(archive_url)

    members = [
        member
        for member in read_archive_members(archive_data)
        if not member.path.startswith("__MACOSX/")
        and not Path(member.path).name.startswith("._")
    ]
    names = {member.path.lower() for member in members}
    required = {"scripts/dreamster.sh", "minicast/minicast.elf"}
    if not required.issubset(names):
        raise RuntimeError("DreamSTer ZIP is missing its script or runtime")

    tag = str(release.get("tag_name") or release.get("name") or "latest")
    database = build_selective_archive_database(
        folder=FOLDER,
        repository=args.repository,
        timestamp=generation_timestamp(args.timestamp),
        archive_url=archive_url,
        archive_data=archive_data,
        selected_files=[(member.path, member) for member in members],
        description=f"Installing DreamSTer {tag}",
        filter_terms=(FOLDER, "console", "dreamcast"),
        extra_folders=("games/Dreamcast",),
    )
    write_bundle(database, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
