#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import call, patch

from db_helpers import DOWNLOAD_RETRY_DELAYS_SECONDS
from run_downloader_tests import run_downloader_tests


def tester_call(
    tester: Path, output: Path, folder: str, db_id: str | None = None
) -> call:
    return call(
        [
            sys.executable,
            str(tester.resolve()),
            db_id or f"MultiDatabases/{folder}",
            str((output / folder / "db.json").resolve()),
        ],
        check=True,
    )


class RunDownloaderTestsTests(unittest.TestCase):
    def test_runs_the_official_tester_for_every_discovered_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            output = root / "dist"
            tester = root / ".github" / "downloader_test.py"
            tester.parent.mkdir()
            tester.touch()

            for folder in ("duke3d", "dreamster"):
                (root / folder).mkdir()
                database = output / folder / "db.json"
                database.parent.mkdir(parents=True)
                database.write_text(
                    json.dumps({"db_id": f"MultiDatabases/{folder}"}), encoding="utf-8"
                )

            with patch("run_downloader_tests.subprocess.run") as run:
                run_downloader_tests(tester, output, root=root)

            self.assertEqual(
                [
                    tester_call(tester, output, "dreamster"),
                    tester_call(tester, output, "duke3d"),
                ],
                run.call_args_list,
            )

    def test_passes_the_bundles_own_id_to_the_tester(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            output = root / "dist"
            tester = root / ".github" / "downloader_test.py"
            tester.parent.mkdir()
            tester.touch()
            (root / "distribution-mister-pinned-linux").mkdir()
            database = output / "distribution-mister-pinned-linux" / "db.json"
            database.parent.mkdir(parents=True)
            database.write_text(
                json.dumps({"db_id": "distribution_mister"}), encoding="utf-8"
            )

            with patch("run_downloader_tests.subprocess.run") as run:
                run_downloader_tests(tester, output, root=root)

            self.assertEqual(
                [
                    tester_call(
                        tester,
                        output,
                        "distribution-mister-pinned-linux",
                        db_id="distribution_mister",
                    )
                ],
                run.call_args_list,
            )

    def test_retries_the_tester_until_a_transient_failure_clears(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            output = root / "dist"
            tester = root / ".github" / "downloader_test.py"
            tester.parent.mkdir()
            tester.touch()
            (root / "mister-dvd").mkdir()
            database = output / "mister-dvd" / "db.json"
            database.parent.mkdir(parents=True)
            database.write_text(
                json.dumps({"db_id": "MultiDatabases/mister-dvd"}), encoding="utf-8"
            )

            failure = subprocess.CalledProcessError(21, "downloader.sh")
            with patch(
                "run_downloader_tests.subprocess.run", side_effect=[failure, None]
            ) as run, patch("run_downloader_tests.time.sleep") as sleep:
                run_downloader_tests(tester, output, root=root)

            attempt = tester_call(tester, output, "mister-dvd")
            self.assertEqual([attempt, attempt], run.call_args_list)
            self.assertEqual(
                [call(DOWNLOAD_RETRY_DELAYS_SECONDS[0])], sleep.call_args_list
            )

    def test_keeps_failing_a_database_that_is_broken_on_every_attempt(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            output = root / "dist"
            tester = root / ".github" / "downloader_test.py"
            tester.parent.mkdir()
            tester.touch()
            (root / "mister-dvd").mkdir()
            database = output / "mister-dvd" / "db.json"
            database.parent.mkdir(parents=True)
            database.write_text(
                json.dumps({"db_id": "MultiDatabases/mister-dvd"}), encoding="utf-8"
            )

            failure = subprocess.CalledProcessError(21, "downloader.sh")
            with patch(
                "run_downloader_tests.subprocess.run", side_effect=failure
            ) as run, patch("run_downloader_tests.time.sleep") as sleep:
                with self.assertRaises(subprocess.CalledProcessError):
                    run_downloader_tests(tester, output, root=root)

            self.assertEqual(len(DOWNLOAD_RETRY_DELAYS_SECONDS) + 1, run.call_count)
            self.assertEqual(
                [call(delay) for delay in DOWNLOAD_RETRY_DELAYS_SECONDS],
                sleep.call_args_list,
            )

    def test_skips_an_entry_that_published_no_database(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            output = root / "dist"
            tester = root / ".github" / "downloader_test.py"
            tester.parent.mkdir()
            tester.touch()
            (root / "dreamster").mkdir()

            with patch("run_downloader_tests.subprocess.run") as run:
                run_downloader_tests(tester, output, root=root)

            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
