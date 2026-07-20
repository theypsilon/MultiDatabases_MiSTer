#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]


def load_generator(folder: str) -> ModuleType:
    path = ROOT / folder / "generate_db.py"
    spec = importlib.util.spec_from_file_location(
        f"test_{folder.replace('-', '_')}_generator", path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ThreeSArmMappingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.generator = load_generator("3s-arm")

    def test_maps_release_payload_to_mister_paths(self) -> None:
        destination_for = self.generator.destination_for
        self.assertEqual(
            "MiSTer_3S-ARM",
            destination_for("release/MiSTer_3S-ARM"),
        )
        self.assertEqual(
            "_Other/3S-ARM.rbf",
            destination_for("release/_Other/3S-ARM.rbf"),
        )
        self.assertEqual(
            "_Other/3S-ARM.rbf",
            destination_for("release/3S-ARM.rbf"),
        )
        self.assertEqual(
            "games/3s-arm/bin/3s-arm",
            destination_for("release/games/3s-arm/bin/3s-arm"),
        )

    def test_excludes_documentation_and_game_data(self) -> None:
        destination_for = self.generator.destination_for
        self.assertIsNone(destination_for("release/README.txt"))
        self.assertIsNone(
            destination_for("release/games/3s-arm/resources/SF33RD.AFS")
        )
        self.assertIsNone(destination_for("release/SF33RD.AFS"))


class Mms2GbReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.generator = load_generator("mms2-gb")

    def test_selects_newest_dated_rbf(self) -> None:
        entries = [
            {
                "name": "Gameboy_20251023.rbf",
                "download_url": "https://example.com/Gameboy_20251023.rbf",
                "type": "file",
            },
            {
                "name": "GameboyColor.mgl",
                "download_url": "https://example.com/GameboyColor.mgl",
                "type": "file",
            },
            {
                "name": "Gameboy_20260623.rbf",
                "download_url": "https://example.com/Gameboy_20260623.rbf",
                "type": "file",
            },
        ]

        self.assertEqual(
            "Gameboy_20260623.rbf",
            self.generator.latest_rbf(entries)["name"],
        )

    def test_rejects_a_listing_without_a_dated_rbf(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "Gameboy_YYYYMMDD"):
            self.generator.latest_rbf(
                [
                    {
                        "name": "GameboyColor.mgl",
                        "download_url": "https://example.com/GameboyColor.mgl",
                        "type": "file",
                    }
                ]
            )


if __name__ == "__main__":
    unittest.main()
