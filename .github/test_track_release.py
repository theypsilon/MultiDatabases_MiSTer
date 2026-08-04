#!/usr/bin/env python3

from __future__ import annotations

import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import track_release
from track_release import COMMITS_FILE, RELEASES_BRANCH


COMMITS = (
    "0123456789abcdef0123456789abcdef01234567",
    "89abcdef0123456789abcdef0123456789abcdef",
)


def git(*arguments: str, cwd: Path) -> str:
    return subprocess.run(
        ["git", *arguments], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout


class TrackReleaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        base = Path(self.temporary.name)

        self.remote = base / "remote.git"
        git("init", "--bare", "--initial-branch=main", str(self.remote), cwd=base)

        self.root = base / "source"
        git("init", "--initial-branch=main", str(self.root), cwd=base)
        git("config", "user.name", "Test", cwd=self.root)
        git("config", "user.email", "test@example.com", cwd=self.root)
        (self.root / "README.md").write_text("source branch\n", encoding="utf-8")
        git("add", "README.md", cwd=self.root)
        git("commit", "-m", "Initial", cwd=self.root)
        git("remote", "add", "origin", str(self.remote), cwd=self.root)
        git("push", "origin", "main", cwd=self.root)

    def track(
        self,
        commit: str,
        *entries: str,
        now: datetime | None = None,
    ) -> str:
        return track_release.track_release(
            commit, entries=entries, root=self.root, now=now
        )

    def published(self, log: str = COMMITS_FILE) -> str:
        return git("show", f"origin/{RELEASES_BRANCH}:{log}", cwd=self.root)

    def fetch(self) -> None:
        git("fetch", "origin", RELEASES_BRANCH, cwd=self.root)
        git(
            "update-ref",
            f"refs/remotes/origin/{RELEASES_BRANCH}",
            "FETCH_HEAD",
            cwd=self.root,
        )

    def test_creates_the_orphan_branch_with_the_first_release(self) -> None:
        line = self.track(
            COMMITS[0], now=datetime(2026, 8, 4, 17, 5, 9, tzinfo=timezone.utc)
        )

        self.assertEqual(f"2026-08-04 17:05:09 UTC: {COMMITS[0]}", line)
        self.fetch()
        self.assertEqual(f"{line}\n", self.published())
        # Orphan: the log is all the branch carries, and it starts a history.
        self.assertEqual(
            [COMMITS_FILE],
            git(
                "ls-tree", "--name-only", "-r", f"origin/{RELEASES_BRANCH}", cwd=self.root
            ).split(),
        )
        self.assertEqual(
            1,
            len(
                git(
                    "log", "--format=%H", f"origin/{RELEASES_BRANCH}", cwd=self.root
                ).split()
            ),
        )

    def test_appends_to_the_existing_log_without_losing_history(self) -> None:
        first = self.track(
            COMMITS[0], now=datetime(2026, 8, 4, 17, 5, 9, tzinfo=timezone.utc)
        )
        second = self.track(
            COMMITS[1], now=datetime(2026, 8, 4, 17, 25, 30, tzinfo=timezone.utc)
        )

        self.fetch()
        self.assertEqual(f"{first}\n{second}\n", self.published())
        self.assertEqual(
            ["Track release " + COMMITS[1], "Track release " + COMMITS[0]],
            git(
                "log", "--format=%s", f"origin/{RELEASES_BRANCH}", cwd=self.root
            ).splitlines(),
        )

    def test_logs_each_changed_database_on_its_own(self) -> None:
        first = self.track(
            COMMITS[0],
            "mister-hifi",
            "collection-launcher",
            now=datetime(2026, 8, 4, 17, 5, 9, tzinfo=timezone.utc),
        )
        second = self.track(
            COMMITS[1],
            "mister-hifi",
            now=datetime(2026, 8, 4, 18, 40, 1, tzinfo=timezone.utc),
        )

        self.fetch()
        # The whole-branch log keeps every published commit...
        self.assertEqual(f"{first}\n{second}\n", self.published())
        # ...while each database only records the pushes that moved it.
        self.assertEqual(
            f"{first}\n{second}\n", self.published(f"mister-hifi/{COMMITS_FILE}")
        )
        self.assertEqual(
            f"{first}\n", self.published(f"collection-launcher/{COMMITS_FILE}")
        )
        self.assertEqual(
            [
                f"collection-launcher/{COMMITS_FILE}",
                COMMITS_FILE,
                f"mister-hifi/{COMMITS_FILE}",
            ],
            sorted(
                git(
                    "ls-tree", "--name-only", "-r", f"origin/{RELEASES_BRANCH}", cwd=self.root
                ).split()
            ),
        )

    def test_rejects_an_entry_name_that_is_not_a_folder(self) -> None:
        for entry in ("../evil", "nested/entry", ".hidden"):
            with self.subTest(entry=entry):
                with self.assertRaisesRegex(RuntimeError, "database entry name"):
                    self.track(COMMITS[0], entry)

    def test_leaves_the_build_checkout_alone(self) -> None:
        self.track(COMMITS[0])

        self.assertEqual("main", git("branch", "--show-current", cwd=self.root).strip())
        self.assertEqual("", git("status", "--porcelain", cwd=self.root))
        self.assertFalse((self.root / COMMITS_FILE).exists())

    def test_rejects_something_that_is_not_a_commit(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "full Git commit SHA"):
            self.track("HEAD")

    def test_the_command_skips_tracking_when_it_is_turned_off(self) -> None:
        with patch.dict("os.environ", {"TRACK_RELEASE": "false"}):
            with patch.object(track_release, "track_release") as tracker:
                self.assertEqual(0, self.main(COMMITS[0]))

        tracker.assert_not_called()

    def test_the_command_warns_instead_of_failing_a_published_build(self) -> None:
        # The databases are already on the db branch by then, so a tracking
        # failure must not turn the run red.
        with patch.dict("os.environ", {}, clear=False):
            exit_code = self.main(COMMITS[0], "--remote", "missing")

        self.assertEqual(0, exit_code)

    def main(self, *arguments: str) -> int:
        argv = ["track_release.py", *arguments, "--root", str(self.root)]
        with patch("sys.argv", argv):
            return track_release.main()


if __name__ == "__main__":
    unittest.main()
