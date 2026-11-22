#!/usr/bin/env python3

from __future__ import annotations

import posixpath
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Sequence

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

# The FPGA half of this hybrid port, inside `_Other`, where upstream publishes
# it in the release ZIP and where this database installs it: the `_Other`
# mapping below passes that folder through unchanged.
#
# MiSTer names a core `<Core>_YYYYMMDD.rbf` and derives the core's identity --
# and with it the `MiSTer.ini` section that configures it -- from the name with
# that datecode stripped, so `[3S-ARM] main=MiSTer_3S-ARM` keeps working as the
# date moves. Upstream shipped this core undated as `_Other/3S-ARM.rbf` up to
# v20260417 and joined that convention in v20261117 (2026-11-18) with
# `_Other/3S-ARM_20261021.rbf`.
#
# Reviewed on pull request #23 (2026-11-22): this entry installs whichever
# dated core the release ships, so a rebuilt core no longer needs a human. The
# date is all that may move. The folder, the spelling and the count stay a
# reviewed contract and `sole_core` fails the generator on anything else -- the
# undated name coming back, a differently cased or punctuated name, a datecode
# that is not a calendar date, a core outside `_Other`, or a second core beside
# the first -- rather than silently moving the core file users have installed or
# listing 3S-ARM twice in the MiSTer menu.
CORE_DIRECTORY = "_Other"
CORE_PATTERN = re.compile(r"3S-ARM_(\d{8})\.rbf")

# What a release has to install for this database to be worth publishing: the
# ARM executable MiSTer.ini points `main=` at, and the game binary that
# executable runs. The core the MiSTer menu launches it with is held to
# `sole_core` instead, because its name carries a date.
REQUIRED = ("MiSTer_3S-ARM", "games/3s-arm/bin/3s-arm")


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
    if CORE_PATTERN.fullmatch(basename):
        return posixpath.join(CORE_DIRECTORY, basename)
    return None


def core_datecode(destination: str) -> str | None:
    """The `YYYYMMDD` of `destination` when it is named like this core."""
    directory, _, filename = destination.rpartition("/")
    if directory != CORE_DIRECTORY:
        return None
    match = CORE_PATTERN.fullmatch(filename)
    return match.group(1) if match else None


def sole_core(destinations: Sequence[str]) -> str:
    """The one dated core a release installs, or a loud failure."""
    cores = sorted({path for path in destinations if path.lower().endswith(".rbf")})
    datecodes = [core_datecode(path) for path in cores]
    for path, datecode in zip(cores, datecodes):
        if datecode is None:
            continue
        try:
            datetime.strptime(datecode, "%Y%m%d")
        except ValueError:
            raise RuntimeError(
                f"3S-ARM core is not dated with a calendar date: {path}. Only "
                f"the date in {CORE_DIRECTORY}/3S-ARM_YYYYMMDD.rbf may change, "
                "so this fails instead of installing it."
            ) from None

    if len(cores) != 1 or datecodes[0] is None:
        raise RuntimeError(
            f"3S-ARM ZIP must ship exactly one {CORE_DIRECTORY}/"
            "3S-ARM_YYYYMMDD.rbf core, found: "
            + (", ".join(cores) or "none")
            + ". Upstream renaming, moving or doubling the core is a reviewed "
            "change, so this fails instead of following it."
        )
    return cores[0]


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

    destinations = [destination for destination, _ in selected]
    core = sole_core(destinations)
    missing = [path for path in REQUIRED if path not in destinations]
    if missing:
        raise RuntimeError(
            "3S-ARM ZIP is missing required files: "
            + ", ".join(missing)
            + ". Upstream renaming or dropping one of them is a reviewed "
            "change, so this fails instead of following it."
        )

    tag = str(release.get("tag_name") or release.get("name") or "latest")
    print(f"3S-ARM {tag} installs {core}", flush=True)
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
