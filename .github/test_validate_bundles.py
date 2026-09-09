#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import validate_bundles
from db_helpers import write_bundle
from test_db_helpers import database


def publish(root: Path, folder: str) -> Path:
    (root / folder).mkdir()
    bundle = root / "dist" / folder
    write_bundle(database(folder, 100), bundle)
    return bundle


class ValidateBundlesTests(unittest.TestCase):
    def validate(self, root: Path) -> None:
        argv = ["validate_bundles.py", str(root / "dist")]
        with patch.object(validate_bundles, "ROOT", root):
            with patch.object(sys, "argv", argv):
                self.assertEqual(0, validate_bundles.main())

    def test_an_entry_without_a_bundle_does_not_fail_the_build(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            publish(root, "dreamster")
            (root / "duke3d").mkdir()

            self.validate(root)

    def test_an_incomplete_bundle_fails_the_build(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            bundle = publish(root, "duke3d")
            (bundle / "db.json.zip").unlink()

            with self.assertRaisesRegex(
                RuntimeError, "Missing database output for duke3d"
            ):
                self.validate(root)

    def test_a_distribution_clone_keeps_upstreams_layout_and_id(self) -> None:
        # Upstream's document as is: reserved ID, system files, no per-file
        # URLs, no drop-in. Only its bundle consistency is checked here.
        document = {
            "v": 1,
            "db_id": "distribution_mister",
            "timestamp": 1,
            "files": {"MiSTer": {"hash": "0" * 32, "size": 1, "path": "system"}},
            "folders": {},
            "tag_dictionary": {},
            "linux": {"hash": "0" * 32, "size": 1, "url": "https://x/", "version": "250402"},
        }
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "stale-distribution-mister").mkdir()
            bundle = root / "dist" / "stale-distribution-mister"
            bundle.mkdir(parents=True)
            encoded = json.dumps(document).encode("utf-8")
            (bundle / "db.json").write_bytes(encoded)
            with zipfile.ZipFile(bundle / "db.json.zip", "w") as archive:
                archive.writestr("db.json", encoded)

            self.validate(root)

            (bundle / "db.json").write_bytes(encoded + b"\n")
            with self.assertRaisesRegex(RuntimeError, "ZIP and JSON differ"):
                self.validate(root)

    def test_an_entry_may_not_publish_another_id(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "dreamster").mkdir()
            write_bundle(database("duke3d", 100), root / "dist" / "dreamster")

            with self.assertRaisesRegex(RuntimeError, "Unexpected db_id for dreamster"):
                self.validate(root)


if __name__ == "__main__":
    unittest.main()
