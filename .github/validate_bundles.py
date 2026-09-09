#!/usr/bin/env python3

"""Validate every generated database bundle."""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

from db_helpers import DB_NAMESPACE, validate_database
from generate_all import ROOT, discover_folders


# Entries that republish the official distribution under Downloader's reserved
# ID. Their document is upstream's, not this repository's layout, so the shared
# validation does not apply, and Downloader refuses a drop-in for that section.
DISTRIBUTION_CLONES = {"stale-distribution-mister": "distribution_mister"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate generated DB bundles")
    parser.add_argument("directory", nargs="?", type=Path, default=Path("dist"))
    args = parser.parse_args()
    folders = discover_folders(ROOT, exclude=(args.directory,))

    for folder in folders:
        bundle = args.directory / folder
        if not bundle.is_dir():
            # Its generator failed and it never published a database before.
            print(f"Skipping {folder}: nothing to publish", flush=True)
            continue

        json_path = bundle / "db.json"
        zip_path = bundle / "db.json.zip"
        if not json_path.is_file() or not zip_path.is_file():
            raise RuntimeError(f"Missing database output for {folder}")

        encoded = json_path.read_bytes()
        database = json.loads(encoded)
        expected_id = DISTRIBUTION_CLONES.get(folder, f"{DB_NAMESPACE}/{folder}")
        if database["db_id"] != expected_id:
            raise RuntimeError(f"Unexpected db_id for {folder}: {database['db_id']}")

        with zipfile.ZipFile(zip_path) as archive:
            if archive.namelist() != ["db.json"]:
                raise RuntimeError(f"Unexpected files in {zip_path}")
            if archive.read("db.json") != encoded:
                raise RuntimeError(f"ZIP and JSON differ for {folder}")

        if folder in DISTRIBUTION_CLONES:
            print(f"Validated {database['db_id']}", flush=True)
            continue

        validate_database(database)
        sanitized = database["db_id"].replace("/", "_")
        ini_path = bundle / f"downloader_{sanitized}.ini"
        drop_in_zip = bundle / f"downloader_{sanitized}.zip"
        if not ini_path.is_file() or not drop_in_zip.is_file():
            raise RuntimeError(f"Missing drop-in files for {folder}")
        with zipfile.ZipFile(drop_in_zip) as archive:
            if archive.read(ini_path.name) != ini_path.read_bytes():
                raise RuntimeError(f"Drop-in ZIP and INI differ for {folder}")

        print(f"Validated {database['db_id']}", flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
