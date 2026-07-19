#!/usr/bin/env python3

"""Run the official Downloader integration test for every database bundle."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from db_helpers import DB_NAMESPACE
from generate_all import ROOT, discover_folders


def run_downloader_tests(tester: Path, directory: Path, *, root: Path = ROOT) -> None:
    tester = tester.resolve()
    folders = discover_folders(root, exclude=(directory,))

    for folder in folders:
        database = (directory / folder / "db.json").resolve()
        if not database.is_file():
            raise RuntimeError(f"Missing database output for {folder}: {database}")

        db_id = f"{DB_NAMESPACE}/{folder}"
        print(f"Testing {db_id} with MiSTer Downloader...", flush=True)
        subprocess.run(
            [sys.executable, str(tester), db_id, str(database)],
            check=True,
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Test generated bundles with MiSTer Downloader"
    )
    parser.add_argument("tester", type=Path, help="Path to downloader_test.py")
    parser.add_argument("directory", nargs="?", type=Path, default=Path("dist"))
    args = parser.parse_args()

    if not args.tester.is_file():
        raise RuntimeError(f"Downloader tester not found: {args.tester}")

    run_downloader_tests(args.tester, args.directory)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
