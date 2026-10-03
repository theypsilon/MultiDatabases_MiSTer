#!/usr/bin/env python3

"""Run the official Downloader integration test for every database bundle."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from db_helpers import DOWNLOAD_RETRY_DELAYS_SECONDS
from generate_all import ROOT, discover_folders


def run_tester(tester: Path, db_id: str, database: Path) -> None:
    # The tester pins downloader_retries = 0, so a retryable HTTP status from a
    # payload host sinks the run, and the Downloader reports that fetch the same
    # way it reports a wrong hash: its exit code cannot tell the two apart. The
    # whole run is repeated instead, under the same delays the generators use for
    # transient downloads. This keeps the publication gate intact, because a
    # database that is really broken stays broken through every attempt.
    attempts = len(DOWNLOAD_RETRY_DELAYS_SECONDS) + 1
    for attempt in range(attempts):
        try:
            subprocess.run(
                [sys.executable, str(tester), db_id, str(database)],
                check=True,
            )
            return
        except subprocess.CalledProcessError as exc:
            if attempt == attempts - 1:
                raise
            delay = DOWNLOAD_RETRY_DELAYS_SECONDS[attempt]
            print(
                f"Downloader test for {db_id} failed with exit code "
                f"{exc.returncode}; retrying in {delay}s "
                f"(attempt {attempt + 2}/{attempts})",
                file=sys.stderr,
                flush=True,
            )
            time.sleep(delay)


def run_downloader_tests(tester: Path, directory: Path, *, root: Path = ROOT) -> None:
    tester = tester.resolve()
    folders = discover_folders(root, exclude=(directory,))

    for folder in folders:
        database = (directory / folder / "db.json").resolve()
        if not database.is_file():
            # Its generator failed and it never published a database before.
            print(f"Skipping {folder}: nothing to publish", flush=True)
            continue

        # The tester needs the section name Downloader will match against the
        # database's own ID, so it is read from the bundle instead of assumed.
        db_id = json.loads(database.read_bytes())["db_id"]
        print(f"Testing {db_id} with MiSTer Downloader...", flush=True)
        run_tester(tester, db_id, database)


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
