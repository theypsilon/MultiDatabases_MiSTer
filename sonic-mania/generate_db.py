#!/usr/bin/env python3

from __future__ import annotations

import posixpath
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".github"))

from db_helpers import (  # noqa: E402
    build_selective_archive_database,
    first_zip_asset,
    generation_timestamp,
    generator_parser,
    github_latest_release,
    http_get_bytes,
    read_archive_members,
    release_asset_url,
    write_bundle,
)


FOLDER = "sonic-mania"
UPSTREAM = "kimchiman52/sonic-mania-mister"


def destination_for(member_path: str) -> str | None:
    basename = posixpath.basename(member_path)
    lower_basename = basename.lower()
    if lower_basename in {"readme.txt", "readme.md", "license.txt", "license.md"}:
        return None
    if basename == "MiSTer_SonicMania":
        return "MiSTer_SonicMania"

    parts = [part for part in member_path.split("/") if part]
    if "_Other" in parts:
        relative = parts[parts.index("_Other") + 1 :]
        return posixpath.join("_Other", *relative) if relative else None
    if "games" in parts:
        relative = parts[parts.index("games") + 1 :]
        if not relative:
            return None
        if [part.lower() for part in relative] == ["sonic-mania", "data.rsdk"]:
            return None
        return posixpath.join("games", *relative)
    return None


def main() -> int:
    args = generator_parser(FOLDER, "Generate the Sonic Mania MiSTer database").parse_args()
    release = github_latest_release(UPSTREAM)
    asset = first_zip_asset(release)
    archive_url = release_asset_url(asset)
    archive_data = http_get_bytes(archive_url)
    members = read_archive_members(archive_data)

    selected = []
    for member in members:
        destination = destination_for(member.path)
        if destination:
            selected.append((destination, member))

    names = {destination.lower() for destination, _ in selected}
    if "mister_sonicmania" not in names:
        raise RuntimeError("Sonic Mania ZIP is missing MiSTer_SonicMania")
    if not any(
        name.startswith("_other/sonic_mania") and name.endswith(".rbf")
        for name in names
    ):
        raise RuntimeError("Sonic Mania ZIP is missing its RBF")
    if not any(name.startswith("games/sonic-mania/") for name in names):
        raise RuntimeError("Sonic Mania ZIP is missing its runtime")

    tag = str(release.get("tag_name") or release.get("name") or "latest")
    database = build_selective_archive_database(
        folder=FOLDER,
        repository=args.repository,
        timestamp=generation_timestamp(args.timestamp),
        archive_url=archive_url,
        archive_data=archive_data,
        selected_files=selected,
        description=f"Installing Sonic Mania MiSTer {tag}",
        extra_folders=("games/sonic-mania",),
    )
    write_bundle(database, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
