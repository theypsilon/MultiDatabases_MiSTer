#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import call, patch

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
            (root / "stale-distribution-mister").mkdir()
            database = output / "stale-distribution-mister" / "db.json"
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
                        "stale-distribution-mister",
                        db_id="distribution_mister",
                    )
                ],
                run.call_args_list,
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
