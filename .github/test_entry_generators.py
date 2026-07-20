#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from types import ModuleType
from unittest.mock import patch


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


class PhysicalDiscGeneratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.generator = load_generator("physical-disc")

    def member(self, path: str, data: bytes = b"data"):
        return self.generator.ArchiveMember(
            archive_path=path,
            path=path,
            data=data,
        )

    def test_discovers_every_matching_repository_across_pages(self) -> None:
        first_page = [
            {
                "name": f"Unrelated_{index}",
                "full_name": f"Anime0t4ku/Unrelated_{index}",
            }
            for index in range(99)
        ]
        first_page.append(
            {
                "name": "PSX_MiSTer_Physical_Disc",
                "full_name": "Anime0t4ku/PSX_MiSTer_Physical_Disc",
            }
        )
        second_page = [
            {
                "name": "Main_MiSTer_Physical_Disc",
                "full_name": "Anime0t4ku/Main_MiSTer_Physical_Disc",
            },
            {
                "name": "Almost_Physical_Disc_old",
                "full_name": "Anime0t4ku/Almost_Physical_Disc_old",
            },
        ]
        pages = iter((first_page, second_page))

        repositories = self.generator.discover_repositories(
            fetch_json=lambda _url: next(pages)
        )

        self.assertEqual(
            (
                "Anime0t4ku/Main_MiSTer_Physical_Disc",
                "Anime0t4ku/PSX_MiSTer_Physical_Disc",
            ),
            repositories,
        )

    def test_allows_multiple_release_zips(self) -> None:
        release = {
            "tag_name": "v1",
            "assets": [
                {"name": "first.zip"},
                {"name": "second.ZIP"},
            ],
        }
        self.assertEqual(
            tuple(release["assets"]),
            self.generator.zip_assets(release, "Anime0t4ku/example"),
        )

    def test_requires_at_least_one_release_zip(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "does not contain a ZIP"):
            self.generator.zip_assets(
                {"tag_name": "v1", "assets": [{"name": "core.rbf"}]},
                "Anime0t4ku/example",
            )

    def test_selects_the_compatible_zip_from_multiple_assets(self) -> None:
        root = "_Physical Disc Cores"
        rbf = self.member(f"{root}/Cores/PSX.rbf")
        mgl = self.member(
            f"{root}/PSX Physical Disc.mgl",
            (
                b"<mistergamedescription>"
                b"<rbf>_Physical Disc Cores/Cores/PSX</rbf>"
                b'<setname same_dir="1">CD-PSX</setname>'
                b"</mistergamedescription>"
            ),
        )
        release = {
            "tag_name": "v1",
            "assets": [
                {
                    "name": "documentation.zip",
                    "browser_download_url": (
                        "https://github.com/example/project/releases/"
                        "download/v1/documentation.zip"
                    ),
                },
                {
                    "name": "PSX.zip",
                    "browser_download_url": (
                        "https://github.com/example/project/releases/"
                        "download/v1/PSX.zip"
                    ),
                },
            ],
        }
        with patch.object(
            self.generator,
            "github_latest_release",
            return_value=release,
        ):
            with patch.object(
                self.generator,
                "http_get_bytes",
                side_effect=(b"documentation", b"core"),
            ):
                with patch.object(
                    self.generator,
                    "read_archive_members",
                    side_effect=(
                        [self.member("README.md")],
                        [rbf, mgl],
                    ),
                ):
                    archive = self.generator.release_archive(
                        "Anime0t4ku/PSX_MiSTer_Physical_Disc"
                    )

        self.assertTrue(archive.url.endswith("/PSX.zip"))

    def test_requires_the_custom_main_repository(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "Main repository is missing"):
            self.generator.discover_repositories(
                fetch_json=lambda _url: [
                    {
                        "name": "PSX_MiSTer_Physical_Disc",
                        "full_name": "Anime0t4ku/PSX_MiSTer_Physical_Disc",
                    }
                ]
            )

    def test_validates_main_zip_against_release_ini_instructions(self) -> None:
        member = self.member("MiSTer_Physical-CD")
        archive = self.generator.main_archive(
            "Main_MiSTer_Physical_Disc",
            {
                "tag_name": "v0.8",
                "body": (
                    "Add this to MiSTer.ini:\n\n"
                    "```ini\n[CD-*]\nmain=MiSTer_Physical-CD\n```\n"
                ),
            },
            (
                "https://github.com/Anime0t4ku/Main_MiSTer_Physical_Disc/"
                "releases/download/v0.8/MiSTer_Physical-CD.zip"
            ),
            b"zip",
            [member],
        )

        self.assertEqual("main", archive.archive_id)
        self.assertEqual((("MiSTer_Physical-CD", member),), archive.selected_files)
        self.assertEqual(("MiSTer_Physical-CD",), archive.reboot_paths)

    def test_rejects_main_zip_that_differs_from_release_instructions(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "but the ZIP contains"):
            self.generator.main_archive(
                "Main_MiSTer_Physical_Disc",
                {
                    "tag_name": "v1",
                    "body": "[CD-*]\nmain=MiSTer_Physical-CD",
                },
                "https://github.com/example/releases/download/v1/main.zip",
                b"zip",
                [self.member("MiSTer_Different")],
            )

    def test_mirrors_valid_core_zip_and_checks_mgl_target(self) -> None:
        root = "_Physical Disc Cores"
        rbf = self.member(f"{root}/Cores/PSX.rbf")
        mgl = self.member(
            f"{root}/PSX Physical Disc.mgl",
            (
                b"<mistergamedescription>"
                b"<rbf>_Physical Disc Cores/Cores/PSX</rbf>"
                b'<setname same_dir="1">CD-PSX</setname>'
                b"</mistergamedescription>"
            ),
        )
        archive = self.generator.core_archive(
            "PSX_MiSTer_Physical_Disc",
            {"tag_name": "v1.0.0"},
            (
                "https://github.com/Anime0t4ku/PSX_MiSTer_Physical_Disc/"
                "releases/download/v1.0.0/PSX.zip"
            ),
            b"zip",
            [rbf, mgl],
        )

        self.assertEqual("psx", archive.archive_id)
        self.assertEqual(
            ((rbf.path, rbf), (mgl.path, mgl)),
            archive.selected_files,
        )
        self.assertEqual((rbf.path,), archive.reboot_paths)

    def test_rejects_core_zip_with_mismatched_mgl(self) -> None:
        root = "_Physical Disc Cores"
        rbf = self.member(f"{root}/Cores/PSX.rbf")
        mgl = self.member(
            f"{root}/PSX Physical Disc.mgl",
            (
                b"<mistergamedescription>"
                b"<rbf>_Physical Disc Cores/Cores/Other</rbf>"
                b'<setname same_dir="1">CD-PSX</setname>'
                b"</mistergamedescription>"
            ),
        )
        with self.assertRaisesRegex(RuntimeError, "MGL selects"):
            self.generator.core_archive(
                "PSX_MiSTer_Physical_Disc",
                {"tag_name": "v1"},
                "https://github.com/example/releases/download/v1/PSX.zip",
                b"zip",
                [rbf, mgl],
            )


if __name__ == "__main__":
    unittest.main()
