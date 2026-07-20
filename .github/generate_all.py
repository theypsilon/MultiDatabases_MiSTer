#!/usr/bin/env python3

"""Generate every database bundle."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Iterable

from db_helpers import prepare_db_operator


ROOT = Path(__file__).resolve().parents[1]


def discover_folders(root: Path, *, exclude: Iterable[Path] = ()) -> tuple[str, ...]:
    excluded = {path.resolve() for path in exclude}
    return tuple(
        path.name
        for path in sorted(root.iterdir(), key=lambda path: path.name)
        if path.is_dir()
        and not path.name.startswith(".")
        and path.resolve() not in excluded
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate all MiSTer databases")
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    parser.add_argument(
        "--repository",
        default=os.getenv("TARGET_REPOSITORY")
        or os.getenv("GITHUB_REPOSITORY")
        or "theypsilon/MultiDatabases_MiSTer",
    )
    parser.add_argument("--timestamp", type=int, default=int(time.time()))
    args = parser.parse_args()
    folders = discover_folders(ROOT, exclude=(args.output,))
    environment = os.environ.copy()
    environment["DB_OPERATOR_PATH"] = str(prepare_db_operator())

    for folder in folders:
        command = [
            sys.executable,
            str(ROOT / folder / "generate_db.py"),
            "--output",
            str(args.output / folder),
            "--repository",
            args.repository,
            "--timestamp",
            str(args.timestamp),
        ]
        print(f"Generating {folder}...", flush=True)
        subprocess.run(command, cwd=ROOT, check=True, env=environment)

    print(f"Generated {len(folders)} databases in {args.output}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
