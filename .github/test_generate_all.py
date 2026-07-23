#!/usr/bin/env python3

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import generate_all


GOOD_GENERATOR = """
import argparse
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path)
parser.add_argument("--repository")
parser.add_argument("--timestamp")
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
(args.output / "db.json").write_text(args.timestamp, encoding="utf-8")
"""

BROKEN_GENERATOR = """
import argparse
import sys
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path)
parser.add_argument("--repository")
parser.add_argument("--timestamp")
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
(args.output / "db.json").write_text("half written", encoding="utf-8")
print("upstream release is missing its ZIP", file=sys.stderr)
raise SystemExit(3)
"""


def make_entry(root: Path, folder: str, source: str) -> None:
    (root / folder).mkdir(parents=True)
    (root / folder / "generate_db.py").write_text(source, encoding="utf-8")


def publish(root: Path, folder: str) -> None:
    bundle = root / "dist" / folder
    bundle.mkdir(parents=True)
    (bundle / "db.json").write_text("published", encoding="utf-8")


class GenerateAllTests(unittest.TestCase):
    def generate(self, root: Path, timestamp: str) -> str:
        argv = [
            "generate_all.py",
            "--output",
            str(root / "dist"),
            "--failures",
            str(root / ".build" / "failures.txt"),
            "--repository",
            "theypsilon/MultiDatabases_MiSTer",
            "--timestamp",
            timestamp,
        ]
        with patch.object(generate_all, "ROOT", root):
            with patch.object(
                generate_all, "prepare_db_operator", return_value=root / "operator.py"
            ):
                with patch.object(sys, "argv", argv):
                    self.assertEqual(0, generate_all.main())
        return (root / ".build" / "failures.txt").read_text(encoding="utf-8")

    def test_a_broken_generator_does_not_hold_back_the_other_databases(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            make_entry(root, "dreamster", GOOD_GENERATOR)
            make_entry(root, "duke3d", BROKEN_GENERATOR)
            publish(root, "dreamster")
            publish(root, "duke3d")

            failures = self.generate(root, "777")

            self.assertEqual(
                "777",
                (root / "dist" / "dreamster" / "db.json").read_text(encoding="utf-8"),
            )
            self.assertEqual(
                "published",
                (root / "dist" / "duke3d" / "db.json").read_text(encoding="utf-8"),
            )
            self.assertEqual(
                "duke3d: kept the previously published database\n", failures
            )

    def test_a_new_entry_that_never_generated_publishes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            make_entry(root, "duke3d", BROKEN_GENERATOR)

            failures = self.generate(root, "777")

            self.assertFalse((root / "dist" / "duke3d").exists())
            self.assertEqual("duke3d: nothing was published for it\n", failures)

    def test_a_healthy_run_records_no_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            make_entry(root, "dreamster", GOOD_GENERATOR)

            self.assertEqual("", self.generate(root, "777"))


if __name__ == "__main__":
    unittest.main()
