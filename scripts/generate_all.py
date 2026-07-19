#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path


FOLDERS = (
    "dreamster",
    "duke3d",
    "mister-quake",
    "sonic-mania",
    "paprium",
)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Generate all MiSTer databases")
    parser.add_argument("--output", type=Path, default=root / "dist")
    parser.add_argument(
        "--repository",
        default=os.getenv("TARGET_REPOSITORY")
        or os.getenv("GITHUB_REPOSITORY")
        or "theypsilon/MultiDatabases_MiSTer",
    )
    parser.add_argument("--timestamp", type=int, default=int(time.time()))
    args = parser.parse_args()

    for folder in FOLDERS:
        command = [
            sys.executable,
            str(root / folder / "generate_db.py"),
            "--output",
            str(args.output / folder),
            "--repository",
            args.repository,
            "--timestamp",
            str(args.timestamp),
        ]
        print(f"Generating {folder}...", flush=True)
        subprocess.run(command, cwd=root, check=True)

    print(f"Generated {len(FOLDERS)} databases in {args.output}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
