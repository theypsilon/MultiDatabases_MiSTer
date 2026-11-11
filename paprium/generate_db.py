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

# Upstream retired, and this constant deliberately has not followed it
# (pull request #22, 2026-11-11, awaiting review).
#
# On 2026-11-11 at 20:21 UTC MisterPezz82/Paprium_MegaDrive_MiSTer published
# the release `final`, "Retired: Paprium for MiSTer is now thekoalakoa's
# Paprium_MiSTer", carrying no assets at all and marked neither draft nor
# prerelease, and the repository now reports archived: true, read-only.
# releases/latest answers `final` from here on, ASSET_PATTERN finds no dated
# core in it, and the generator fails closed with this database parked on
# V.08's MegaDrive_Paprium_20261013.rbf from 2026-10-13. Nothing is broken for
# users while it waits: archiving keeps release assets served, so the V.08
# payload URL the published database points at still answers 200.
#
# That failure must not be turned green by skipping a release that carries
# nothing this entry can install. What usually makes that skip safe -- the
# entry stays on the newest release that does carry a core -- is gone here,
# because an archived repository can never publish one. The skip would not
# keep this database current, it would freeze it on a dead upstream and do it
# in silence, which is the outcome a loud failure exists to prevent.
#
# The successor is named only in the retirement notice and in the repository
# description, which are prose, so this generator does not follow them and
# this constant stays put until a human accepts or rejects the move. The
# structured metadata for that review: thekoalakoa/Paprium_MiSTer was created
# 2026-09-08, is not a fork, has no parent, and GitHub records no lineage to
# this repository; its owner (id 118791477) is a different account from
# MisterPezz82 (id 295477100), which authored every release here, `final`
# included. The only tie is that the V.07 and V.08 release names credit
# @thekoalakoa for the work -- prose again.
#
# Accepting the move is also not a repoint of this one line. v0.3.0 ships a
# single Paprium_MiSTer_0.3.0.zip holding _Console/Paprium.rbf,
# _Console/Paprium.mgl and games/Paprium/little_man_firmware.bin, so: the core
# is undated, which retires ASSET_PATTERN, the paprium_megadrive_core tangle
# chain and the MegaDrive_Paprium prefix PapriumMD.mgl launches; the core
# leaves this entry's "_Custom Cores/Cores" folder for "_Console"; a firmware
# blob becomes a third payload; and upstream's own MGL reads the ROM from
# games/Paprium/Paprium/, where this entry's PapriumMD setname has users keep
# theirs in games/PapriumMD/. Moving an existing user's ROM and save directory
# is a reviewed decision of its own, the one brickboy-dmg answered when its
# core was renamed. If review decides not to follow the new project instead,
# the other answer is a reviewed pin to V.08, in the shape megavgmdrive's
# PINNED_RELEASE takes. Either way the value is a human's to set.
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
