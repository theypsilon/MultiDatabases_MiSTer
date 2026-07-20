#!/usr/bin/env python3

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from db_helpers import (
    database_id,
    database_url,
    github_raw_url,
    validate_payload_url,
    write_bundle,
)


def database(folder: str, timestamp: int, *, changed: bool = False) -> dict:
    folders = {"games/changed": {}} if changed else {}
    return {
        "v": 1,
        "db_id": database_id(folder),
        "db_url": database_url("theypsilon/MultiDatabases_MiSTer", folder),
        "timestamp": timestamp,
        "files": {},
        "folders": folders,
        "tag_dictionary": {},
    }


def snapshot(directory: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(directory)): path.read_bytes()
        for path in sorted(directory.rglob("*"))
        if path.is_file()
    }


class WriteBundleTests(unittest.TestCase):
    def test_unchanged_bundle_is_preserved_byte_for_byte(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "dreamster"
            self.assertTrue(write_bundle(database("dreamster", 100), output))
            before = snapshot(output)
            drop_in = output / "downloader_MultiDatabases_dreamster.ini"
            self.assertIn("/dreamster/db.json\n", drop_in.read_text(encoding="utf-8"))
            self.assertNotIn("db.json.zip", drop_in.read_text(encoding="utf-8"))

            self.assertFalse(write_bundle(database("dreamster", 200), output))

            self.assertEqual(before, snapshot(output))
            self.assertEqual(100, json.loads((output / "db.json").read_bytes())["timestamp"])

    def test_entries_are_checked_and_updated_independently(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory)
            dreamster = output / "dreamster"
            duke3d = output / "duke3d"
            write_bundle(database("dreamster", 100), dreamster)
            write_bundle(database("duke3d", 100), duke3d)
            dreamster_before = snapshot(dreamster)
            duke3d_before = snapshot(duke3d)
            (duke3d / "stale-drop-in.ini").write_text("stale", encoding="utf-8")

            self.assertFalse(write_bundle(database("dreamster", 200), dreamster))
            self.assertTrue(
                write_bundle(database("duke3d", 200, changed=True), duke3d)
            )

            self.assertEqual(dreamster_before, snapshot(dreamster))
            self.assertNotEqual(duke3d_before, snapshot(duke3d))
            self.assertFalse((duke3d / "stale-drop-in.ini").exists())
            self.assertEqual(
                200, json.loads((duke3d / "db.json").read_bytes())["timestamp"]
            )


class PayloadUrlTests(unittest.TestCase):
    def test_accepts_concrete_release_and_commit_urls(self) -> None:
        validate_payload_url(
            "https://github.com/example/project/releases/download/v1.2/file.zip"
        )
        validate_payload_url(
            github_raw_url(
                "example/project",
                "0123456789abcdef0123456789abcdef01234567",
                "folder/file name.mgl",
            )
        )

    def test_rejects_moving_branch_and_latest_urls(self) -> None:
        for url in (
            "https://raw.githubusercontent.com/example/project/main/file.rbf",
            "https://raw.githubusercontent.com/example/project/master/file.rbf",
            "https://github.com/example/project/releases/download/latest/file.zip",
        ):
            with self.subTest(url=url):
                with self.assertRaisesRegex(RuntimeError, "commit|concrete"):
                    validate_payload_url(url)


if __name__ == "__main__":
    unittest.main()
