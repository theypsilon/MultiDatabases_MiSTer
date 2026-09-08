#!/usr/bin/env python3

"""Run the official Downloader integration test for every database bundle."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from db_helpers import DB_NAMESPACE, http_get_bytes
from generate_all import ROOT, discover_folders


DOWNLOADER_SCRIPT_URL = (
    "https://raw.githubusercontent.com/MiSTer-devel/Downloader_MiSTer/main/"
    "dont_download.sh"
)


def fetch_downloader_script(path: Path) -> Path:
    source = http_get_bytes(DOWNLOADER_SCRIPT_URL, accept="text/plain")
    if not source.startswith(b"#!") or b"DOWNLOADER_LAUNCHER_PATH" not in source:
        raise RuntimeError(
            f"Downloaded file is not the MiSTer Downloader: {DOWNLOADER_SCRIPT_URL}"
        )

    path.write_bytes(source)
    return path


def run_downloader_tests(tester: Path, directory: Path, *, root: Path = ROOT) -> None:
    tester = tester.resolve()
    databases: list[tuple[str, Path]] = []
    for folder in discover_folders(root, exclude=(directory,)):
        database = (directory / folder / "db.json").resolve()
        if not database.is_file():
            # Its generator failed and it never published a database before.
            print(f"Skipping {folder}: nothing to publish", flush=True)
            continue
        databases.append((folder, database))

    if not databases:
        return

    with tempfile.TemporaryDirectory() as temporary_directory:
        # The tester fetches the Downloader itself, once per database, so a
        # single reset connection out of those fetches fails a build that had
        # already generated and validated every bundle. Fetch it once through
        # the retrying downloader and hand every entry the same local copy.
        script = fetch_downloader_script(Path(temporary_directory) / "downloader.sh")
        environment = {**os.environ, "DOWNLOADER_SOURCE": str(script)}

        for folder, database in databases:
            db_id = f"{DB_NAMESPACE}/{folder}"
            print(f"Testing {db_id} with MiSTer Downloader...", flush=True)
            subprocess.run(
                [sys.executable, str(tester), db_id, str(database)],
                check=True,
                env=environment,
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
