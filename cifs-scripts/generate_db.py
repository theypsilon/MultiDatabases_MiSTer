#!/usr/bin/env python3

from __future__ import annotations

import sys
import urllib.parse
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".github"))

from db_helpers import (  # noqa: E402
    GIT_COMMIT_RE,
    DirectFile,
    build_direct_database,
    generation_timestamp,
    generator_parser,
    github_json,
    github_raw_url,
    http_get_bytes,
    write_bundle,
)


FOLDER = "cifs-scripts"
UPSTREAM = "MiSTer-devel/Scripts_MiSTer"
UPSTREAM_BRANCH = "master"
SCRIPTS = ("cifs_mount.sh", "cifs_umount.sh")


def latest_commit_sha(commits: Any, script: str) -> str:
    if not isinstance(commits, list):
        raise RuntimeError(f"Unexpected commits response for {script}")
    if not commits:
        raise RuntimeError(
            f"{script} has no commits on {UPSTREAM} {UPSTREAM_BRANCH}; "
            "it was removed or renamed upstream"
        )
    newest = commits[0]
    sha = str(newest.get("sha") or "") if isinstance(newest, dict) else ""
    if not GIT_COMMIT_RE.fullmatch(sha):
        raise RuntimeError(f"Unable to resolve the latest commit of {script}")
    return sha


def validate_script(script: str, data: bytes) -> None:
    if not data.startswith(b"#!"):
        raise RuntimeError(f"{script} is not a shell script")


def script_file(script: str) -> DirectFile:
    # The newest commit touching the script, not the branch head, so the URL
    # only changes when the script itself does.
    commits = github_json(
        f"https://api.github.com/repos/{UPSTREAM}/commits"
        f"?path={urllib.parse.quote(script, safe='')}"
        f"&sha={UPSTREAM_BRANCH}&per_page=1"
    )
    url = github_raw_url(UPSTREAM, latest_commit_sha(commits, script), script)
    data = http_get_bytes(url)
    validate_script(script, data)
    return DirectFile(path=f"Scripts/{script}", url=url, data=data)


def main() -> int:
    args = generator_parser(FOLDER, "Generate the CIFS Scripts database").parse_args()
    database = build_direct_database(
        folder=FOLDER,
        repository=args.repository,
        timestamp=generation_timestamp(args.timestamp),
        filter_terms=(FOLDER, "utility"),
        direct_files=tuple(script_file(script) for script in SCRIPTS),
    )
    write_bundle(database, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
