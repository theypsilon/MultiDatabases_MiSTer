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

# The FPGA half of this hybrid port, at the path upstream publishes it inside
# the release ZIP and the path this database installs it to: the `_Other`
# mapping below passes that folder through unchanged. REQUIRED holds upstream
# to this exact name, so a rename fails the generator instead of quietly
# moving the core file users already have installed.
#
# That gate is what the build is red on, and this name is the value a human
# has to accept or reject (pull request #23). Every release up to v20260417 --
# the one the published database still installs -- shipped the core under the
# undated name below. v20261117, published 2026-11-18, renamed it to
# `_Other/3S-ARM_20261021.rbf`, the dated form MiSTer uses for cores, and
# v20261119, published 2026-11-20, ships the same core bytes under the same
# name (2,569,392 bytes, md5 d4a8e7ab1305f62b7c32cce83617213a). Neither
# release is a draft or a prerelease and both carry a complete payload, so
# neither qualifies for the silent skip, and the generator fails closed with
# this database parked on v20260417 until the rename is reviewed. The value
# proposed for review is `_Other/3S-ARM_20261021.rbf`; it is deliberately not
# recorded here.
CORE_PATH = "_Other/3S-ARM.rbf"

# What a release has to install for this database to be worth publishing: the
# ARM executable MiSTer.ini points `main=` at, the core the MiSTer menu
# launches it with, and the game binary that executable runs.
REQUIRED = ("MiSTer_3S-ARM", CORE_PATH, "games/3s-arm/bin/3s-arm")


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
    if basename == posixpath.basename(CORE_PATH):
        return CORE_PATH
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
    missing = [path for path in REQUIRED if path.lower() not in names]
    if missing:
        raise RuntimeError(
            "3S-ARM ZIP is missing required files: "
            + ", ".join(missing)
            + ". Upstream renaming or dropping one of them is a reviewed "
            "change, so this fails instead of following it."
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
