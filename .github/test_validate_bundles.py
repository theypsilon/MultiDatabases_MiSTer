#!/usr/bin/env python3

from __future__ import annotations

import sys
import tempfile
import unittest
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


if __name__ == "__main__":
    unittest.main()
