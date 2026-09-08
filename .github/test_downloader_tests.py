#!/usr/bin/env python3

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from run_downloader_tests import DOWNLOADER_SCRIPT_URL, run_downloader_tests


DOWNLOADER_SCRIPT = (
    b"#!/usr/bin/env bash\n"
    b'export DOWNLOADER_LAUNCHER_PATH="${DOWNLOADER_LAUNCHER_PATH:-${0}}"\n'
)


def tester_command(tester: Path, output: Path, folder: str) -> list[str]:
    return [
        sys.executable,
        str(tester.resolve()),
        f"MultiDatabases/{folder}",
        str((output / folder / "db.json").resolve()),
    ]


def build_tree(root: Path, folders: tuple[str, ...]) -> tuple[Path, Path]:
    output = root / "dist"
    tester = root / ".github" / "downloader_test.py"
    tester.parent.mkdir()
    tester.touch()

    for folder in folders:
        (root / folder).mkdir()
        database = output / folder / "db.json"
        database.parent.mkdir(parents=True)
        database.touch()

    return tester, output


class RunDownloaderTestsTests(unittest.TestCase):
    def test_runs_the_official_tester_for_every_discovered_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            tester, output = build_tree(root, ("duke3d", "dreamster"))

            with patch(
                "run_downloader_tests.http_get_bytes",
                return_value=DOWNLOADER_SCRIPT,
            ), patch("run_downloader_tests.subprocess.run") as run:
                run_downloader_tests(tester, output, root=root)

            self.assertEqual(
                [
                    tester_command(tester, output, "dreamster"),
                    tester_command(tester, output, "duke3d"),
                ],
                [invocation.args[0] for invocation in run.call_args_list],
            )
            for invocation in run.call_args_list:
                self.assertTrue(invocation.kwargs["check"])

    def test_downloads_the_downloader_once_for_every_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            tester, output = build_tree(root, ("duke3d", "dreamster"))
            sources: list[tuple[Path, bytes]] = []

            def record(command: list[str], **kwargs: object) -> object:
                source = Path(str(kwargs["env"]["DOWNLOADER_SOURCE"]))  # type: ignore[index]
                sources.append((source, source.read_bytes()))
                return subprocess.CompletedProcess(command, 0)

            with patch(
                "run_downloader_tests.http_get_bytes",
                return_value=DOWNLOADER_SCRIPT,
            ) as download, patch(
                "run_downloader_tests.subprocess.run", side_effect=record
            ):
                run_downloader_tests(tester, output, root=root)

            download.assert_called_once_with(DOWNLOADER_SCRIPT_URL, accept="text/plain")
            self.assertEqual(2, len(sources))
            self.assertEqual(
                [(sources[0][0], DOWNLOADER_SCRIPT)] * 2,
                sources,
            )

    def test_rejects_a_download_that_is_not_the_downloader(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            tester, output = build_tree(root, ("duke3d",))

            with patch(
                "run_downloader_tests.http_get_bytes",
                return_value=b"<html>404: Not Found</html>",
            ), patch("run_downloader_tests.subprocess.run") as run:
                with self.assertRaises(RuntimeError):
                    run_downloader_tests(tester, output, root=root)

            run.assert_not_called()

    def test_skips_an_entry_that_published_no_database(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            tester, output = build_tree(root, ())
            (root / "dreamster").mkdir()

            with patch(
                "run_downloader_tests.http_get_bytes"
            ) as download, patch("run_downloader_tests.subprocess.run") as run:
                run_downloader_tests(tester, output, root=root)

            run.assert_not_called()
            download.assert_not_called()


if __name__ == "__main__":
    unittest.main()
