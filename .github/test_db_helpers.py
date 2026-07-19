#!/usr/bin/env python3

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from db_helpers import database_id, database_url, write_bundle


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


if __name__ == "__main__":
    unittest.main()
