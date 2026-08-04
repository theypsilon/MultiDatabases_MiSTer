#!/usr/bin/env python3

"""Record every published db branch commit on the db-releases branch."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
import traceback
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator, Sequence

from db_helpers import GIT_COMMIT_RE


ROOT = Path(__file__).resolve().parents[1]
RELEASES_BRANCH = "db-releases"
COMMITS_FILE = "commits.txt"
ENTRY_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
BOT_NAME = "github-actions[bot]"
BOT_EMAIL = "github-actions[bot]@users.noreply.github.com"


def git(*arguments: str, cwd: Path, check: bool = True) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=cwd,
        check=check,
        capture_output=True,
        text=True,
    )
    return result.stdout


@contextmanager
def temporary_worktree(root: Path) -> Iterator[Path]:
    """A detached worktree, so tracking never disturbs the build checkout."""
    with tempfile.TemporaryDirectory() as directory:
        worktree = Path(directory) / RELEASES_BRANCH
        git("worktree", "add", "--detach", str(worktree), cwd=root)
        try:
            yield worktree
        finally:
            git("worktree", "remove", "--force", str(worktree), cwd=root, check=False)


def remote_branch_exists(root: Path, remote: str, branch: str) -> bool:
    listing = git("ls-remote", "--heads", remote, branch, cwd=root)
    return f"refs/heads/{branch}" in listing


def log_files(entries: Iterable[str]) -> list[str]:
    """The whole-branch log, plus one log per database that changed."""
    logs = [COMMITS_FILE]
    for entry in sorted(set(entries)):
        if not ENTRY_RE.fullmatch(entry):
            raise RuntimeError(f"Not a database entry name: {entry}")
        logs.append(f"{entry}/{COMMITS_FILE}")
    return logs


def track_release(
    commit: str,
    *,
    entries: Sequence[str] = (),
    root: Path = ROOT,
    remote: str = "origin",
    now: datetime | None = None,
) -> str:
    """Append `commit` to db-releases and push it, returning the tracked line."""
    if not GIT_COMMIT_RE.fullmatch(commit):
        raise RuntimeError(f"Expected a full Git commit SHA, got: {commit}")

    logs = log_files(entries)
    root = root.resolve()
    with temporary_worktree(root) as worktree:
        if remote_branch_exists(root, remote, RELEASES_BRANCH):
            git("fetch", remote, RELEASES_BRANCH, cwd=worktree)
            git("checkout", "--detach", "FETCH_HEAD", cwd=worktree)
        else:
            # The branch is orphan: it carries the release log, nothing else.
            git("checkout", "--orphan", f"track-release-{uuid.uuid4().hex}", cwd=worktree)
            git("rm", "-rf", "--quiet", ".", cwd=worktree, check=False)

        timestamp = (now or datetime.now(timezone.utc)).strftime(
            "%Y-%m-%d %H:%M:%S UTC"
        )
        line = f"{timestamp}: {commit}"
        for log in logs:
            path = worktree / log
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8", newline="\n") as commits:
                commits.write(f"{line}\n")

        git("add", "--", *logs, cwd=worktree)
        git(
            "-c",
            f"user.name={BOT_NAME}",
            "-c",
            f"user.email={BOT_EMAIL}",
            "commit",
            "-m",
            f"Track release {commit}",
            cwd=worktree,
        )
        # Never forced: the log of published databases only ever grows.
        git("push", remote, f"HEAD:refs/heads/{RELEASES_BRANCH}", cwd=worktree)

    return line


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Track a published db branch commit on the db-releases branch"
    )
    parser.add_argument("commit", help="Commit pushed to the db branch")
    parser.add_argument(
        "--entries",
        nargs="*",
        default=(),
        help="Entries whose database changed in that commit",
    )
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--remote", default="origin")
    args = parser.parse_args()

    if os.getenv("TRACK_RELEASE", "true").strip().lower() == "false":
        print("TRACK_RELEASE is false: skipping release tracking", flush=True)
        return 0

    try:
        line = track_release(
            args.commit,
            entries=args.entries,
            root=args.root,
            remote=args.remote,
        )
    except Exception:  # noqa: BLE001 - the databases are already published
        # Losing the log entry must not turn a successful publication red.
        print("Warning: failed to track the published release", file=sys.stderr)
        traceback.print_exc()
        return 0

    changed = ", ".join(sorted(set(args.entries))) or "none"
    print(f"Tracked on {RELEASES_BRANCH}: {line} (changed: {changed})", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
