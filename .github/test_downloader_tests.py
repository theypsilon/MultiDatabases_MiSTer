#!/usr/bin/env python3

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import call, patch

from run_downloader_tests import run_downloader_tests


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
                database.touch()

            with patch("run_downloader_tests.subprocess.run") as run:
                run_downloader_tests(tester, output, root=root)

            self.assertEqual(
                [
                    call(
                        [
                            sys.executable,
                            str(tester.resolve()),
                            "MultiDatabases/dreamster",
                            str((output / "dreamster" / "db.json").resolve()),
                        ],
                        check=True,
                    ),
                    call(
                        [
                            sys.executable,
                            str(tester.resolve()),
                            "MultiDatabases/duke3d",
                            str((output / "duke3d" / "db.json").resolve()),
                        ],
                        check=True,
                    ),
                ],
                run.call_args_list,
            )

    def test_rejects_a_missing_database_before_invoking_the_tester(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            output = root / "dist"
            tester = root / ".github" / "downloader_test.py"
            tester.parent.mkdir()
            tester.touch()
            (root / "dreamster").mkdir()

            with patch("run_downloader_tests.subprocess.run") as run:
                with self.assertRaisesRegex(
                    RuntimeError, "Missing database output for dreamster"
                ):
                    run_downloader_tests(tester, output, root=root)

            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
