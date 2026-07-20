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


FOLDER = "3s-arm"
UPSTREAM = "kimchiman52/3s-mister-arm"


def destination_for(member_path: str) -> str | None:
    basename = posixpath.basename(member_path)
    lower_basename = basename.lower()
    if lower_basename in {"readme.txt", "readme.md", "sf33rd.afs"}:
        return None
    if basename == "MiSTer_3S-ARM":
        return "MiSTer_3S-ARM"

    parts = [part for part in member_path.split("/") if part]
    if "_Other" in parts:
        relative = parts[parts.index("_Other") + 1 :]
        return posixpath.join("_Other", *relative) if relative else None
    if "games" in parts:
        relative = parts[parts.index("games") + 1 :]
        if not relative or relative[-1].lower() == "sf33rd.afs":
            return None
        return posixpath.join("games", *relative)
    if basename == "3S-ARM.rbf":
        return "_Other/3S-ARM.rbf"
    return None


def main() -> int:
    args = generator_parser(FOLDER, "Generate the 3S-ARM database").parse_args()
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
    required = {
        "mister_3s-arm",
        "_other/3s-arm.rbf",
        "games/3s-arm/bin/3s-arm",
    }
    missing = required - names
    if missing:
        raise RuntimeError(
            "3S-ARM ZIP is missing required files: " + ", ".join(sorted(missing))
        )

    tag = str(release.get("tag_name") or release.get("name") or "latest")
    database = build_selective_archive_database(
        folder=FOLDER,
        repository=args.repository,
        timestamp=generation_timestamp(args.timestamp),
        archive_url=archive_url,
        archive_data=archive_data,
        selected_files=selected,
        description=f"Installing 3S-ARM {tag}",
        filter_terms=(FOLDER, "other"),
        extra_folders=("games/3s-arm/resources",),
    )
    write_bundle(database, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
