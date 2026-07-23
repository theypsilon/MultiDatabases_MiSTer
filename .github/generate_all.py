#!/usr/bin/env python3

"""Generate every database bundle."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
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


def generate_folder(
    folder: str,
    *,
    output: Path,
    repository: str,
    timestamp: int,
    environment: dict[str, str],
) -> int:
    command = [
        sys.executable,
        str(ROOT / folder / "generate_db.py"),
        "--output",
        str(output / folder),
        "--repository",
        repository,
        "--timestamp",
        str(timestamp),
    ]
    print(f"Generating {folder}...", flush=True)
    return subprocess.run(command, cwd=ROOT, env=environment).returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate all MiSTer databases")
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    parser.add_argument(
        "--failures", type=Path, default=ROOT / ".build" / "failures.txt"
    )
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

    failures: list[str] = []
    with tempfile.TemporaryDirectory() as backup:
        for folder in folders:
            bundle = args.output / folder
            published = Path(backup) / folder
            if bundle.is_dir():
                shutil.copytree(bundle, published)

            exit_code = generate_folder(
                folder,
                output=args.output,
                repository=args.repository,
                timestamp=args.timestamp,
                environment=environment,
            )
            if exit_code == 0:
                continue

            # A broken generator must not hold back the databases that work, so
            # the entry falls back to whatever it published before this run.
            shutil.rmtree(bundle, ignore_errors=True)
            if published.is_dir():
                shutil.copytree(published, bundle)
                outcome = "kept the previously published database"
            else:
                outcome = "nothing was published for it"
            failures.append(f"{folder}: {outcome}")
            print(
                f"Failed to generate {folder} with exit code {exit_code}: {outcome}",
                file=sys.stderr,
                flush=True,
            )

    # The build publishes the healthy databases first and only goes red at the
    # end, so the failures outlive this process in a file.
    args.failures.parent.mkdir(parents=True, exist_ok=True)
    args.failures.write_text(
        "".join(f"{failure}\n" for failure in failures), encoding="utf-8"
    )

    print(
        f"Generated {len(folders) - len(failures)} of {len(folders)} databases "
        f"in {args.output}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
