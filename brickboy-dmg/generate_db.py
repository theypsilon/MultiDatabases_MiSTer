#!/usr/bin/env python3

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".github"))

from db_helpers import (  # noqa: E402
    build_empty_database,
    generation_timestamp,
    generator_parser,
    write_bundle,
)


FOLDER = "brickboy-dmg"
# Retired: this entry publishes an empty database and follows no upstream.
#
# 2026-09-28: `kandowontu/brickboy-dmg-fpgacore` stopped existing. The
# repository and the `kandowontu` account both answer 404 over the API and over
# HTTPS with no redirect, so it was removed rather than renamed; GitHub
# redirects renamed owners and repositories. The v0.2.0 `BrickBoy_DMG.rbf` this
# database published went with it and its release URL answers 404 too, so every
# install was failing on the core download. There is nothing left to follow,
# nothing left to install, and no bytes left to hash, so the entry keeps its
# published `db_url` alive with a database that lists nothing instead of
# advertising a payload that cannot be fetched.
#
# Do not revive this entry by pointing it at the identically named
# `kathoc/brickboy-dmg-fpgacore`. That is the Analogue Pocket project the
# withdrawn upstream was a fork of: it publishes `brickboy-dmg-pocket.zip`
# under its own v0.1.0 and v0.2.0 tags and no MiSTer `.rbf`. A different
# repository is a different project and needs its own upstream review even
# under an identical name, so reviving this core is a fresh entry review and
# not an edit to this file.


def main() -> int:
    args = generator_parser(
        FOLDER, "Generate the retired BrickBoy DMG database"
    ).parse_args()
    database = build_empty_database(
        folder=FOLDER,
        repository=args.repository,
        timestamp=generation_timestamp(args.timestamp),
    )
    write_bundle(database, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
