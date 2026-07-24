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


class MisterFinGeneratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.generator = load_generator("misterfin")

    def member(self, path: str):
        return self.generator.ArchiveMember(
            archive_path=path,
            path=path,
            data=b"data",
        )

    def release_members(self, *extra: str):
        return [
            self.member(path)
            for path in (
                "misterfin/MiSTerFin.sh",
                "misterfin/about.png",
                "misterfin/font/font.desc",
                "misterfin/jellyfin.conf.example",
                "misterfin/misterfin-arm",
                "misterfin/mplayer-arm",
                "misterfin/subfont/font.desc",
                "misterfin/toasty/asset1/asset1_1.png",
                *extra,
            )
        ]

    def test_moves_only_the_launcher_into_the_scripts_menu(self) -> None:
        destination_for = self.generator.destination_for
        self.assertEqual(
            "Scripts/MiSTerFin.sh", destination_for("misterfin/MiSTerFin.sh")
        )
        self.assertEqual(
            "misterfin/misterfin-arm", destination_for("misterfin/misterfin-arm")
        )
        self.assertEqual(
            "misterfin/toasty/asset1/asset1_1.png",
            destination_for("misterfin/toasty/asset1/asset1_1.png"),
        )

    def test_installs_every_published_file(self) -> None:
        members = self.release_members()
        selected = self.generator.selected_files(list(reversed(members)))

        self.assertEqual(len(members), len(selected))
        self.assertEqual(
            [
                "Scripts/MiSTerFin.sh",
                "misterfin/about.png",
                "misterfin/font/font.desc",
                "misterfin/jellyfin.conf.example",
                "misterfin/misterfin-arm",
                "misterfin/mplayer-arm",
                "misterfin/subfont/font.desc",
                "misterfin/toasty/asset1/asset1_1.png",
            ],
            [destination for destination, _ in selected],
        )

    def test_rejects_files_outside_the_app_folder(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "outside misterfin/"):
            self.generator.selected_files(self.release_members("docs/README.md"))

    def test_rejects_a_packaged_user_config(self) -> None:
        # Installing it would overwrite the user's Jellyfin URL and API key on
        # every downloader run.
        with self.assertRaisesRegex(RuntimeError, "server URL and API key"):
            self.generator.selected_files(
                self.release_members("misterfin/jellyfin.conf")
            )

    def test_rejects_a_release_missing_the_player(self) -> None:
        members = [
            member
            for member in self.release_members()
            if member.path != "misterfin/mplayer-arm"
        ]
        with self.assertRaisesRegex(RuntimeError, "misterfin/mplayer-arm"):
            self.generator.selected_files(members)

    def test_asset_pattern_accepts_two_and_three_part_versions(self) -> None:
        pattern = self.generator.ASSET_PATTERN
        self.assertEqual("v0.9", pattern.fullmatch("misterfin-v0.9.zip").group(1))
        self.assertEqual(
            "v0.9.1", pattern.fullmatch("misterfin-v0.9.1.zip").group(1)
        )
        self.assertIsNone(pattern.fullmatch("misterfin-source.zip"))


class PhysicalDiscGeneratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.generator = load_generator("physical-disc")

    ROOT_FOLDER = "_Physical Disc Cores"
    MAIN_BODY = "```ini\n[CD-*]\nmain=MiSTer_Physical-CD\n```\n"

    def member(self, path: str, data: bytes = b"data"):
        return self.generator.ArchiveMember(
            archive_path=path,
            path=path,
            data=data,
        )

    def mgl(self, rbf: str, setname: str, same_dir: str = "1"):
        attribute = f' same_dir="{same_dir}"' if same_dir is not None else ""
        return self.member(
            f"{self.ROOT_FOLDER}/{setname}.mgl",
            (
                "<mistergamedescription>"
                f"<rbf>{rbf}</rbf>"
                f"<setname{attribute}>{setname}</setname>"
                "</mistergamedescription>"
            ).encode("utf-8"),
        )

    def bundle_members(self):
        # Most launchers point at official stable cores that ship with the
        # standard MiSTer distribution; CD-i is the exception whose forked core
        # is bundled inside the ZIP.
        return [
            self.member("MiSTer_Physical-CD"),
            self.mgl("_Console/PSX", "CD-PSX"),
            self.mgl("_Console/MegaCD", "CD-MegaCD"),
            self.mgl(f"{self.ROOT_FOLDER}/Cores/CDi", "CD-CDi"),
            self.member(f"{self.ROOT_FOLDER}/Cores/CDi.rbf"),
        ]

    def build_main(self, members):
        return self.generator.main_archive(
            "Main_MiSTer_Physical_Disc",
            {"tag_name": "v0.30", "body": self.MAIN_BODY},
            (
                "https://github.com/Anime0t4ku/Main_MiSTer_Physical_Disc/"
                "releases/download/v0.30/MiSTer_Physical-CD.zip"
            ),
            b"zip",
            members,
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

    def test_bundles_main_launchers_and_forked_core(self) -> None:
        members = self.bundle_members()
        archive = self.build_main(members)

        self.assertEqual(self.generator.ARCHIVE_ID, archive.archive_id)
        self.assertEqual(("MiSTer_Physical-CD",), archive.reboot_paths)
        destinations = [destination for destination, _ in archive.selected_files]
        # Every packaged file installs: the main, all MGLs, and the CD-i core.
        self.assertEqual(sorted(member.path for member in members), sorted(destinations))
        self.assertIn(f"{self.ROOT_FOLDER}/Cores/CDi.rbf", destinations)
        self.assertIn(f"{self.ROOT_FOLDER}/CD-PSX.mgl", destinations)

    def test_selects_the_compatible_zip_from_multiple_assets(self) -> None:
        release = {
            "tag_name": "v0.30",
            "body": self.MAIN_BODY,
            "assets": [
                {
                    "name": "documentation.zip",
                    "browser_download_url": (
                        "https://github.com/example/project/releases/"
                        "download/v0.30/documentation.zip"
                    ),
                },
                {
                    "name": "MiSTer_Physical-CD.zip",
                    "browser_download_url": (
                        "https://github.com/example/project/releases/"
                        "download/v0.30/MiSTer_Physical-CD.zip"
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
                side_effect=(b"documentation", b"bundle"),
            ):
                with patch.object(
                    self.generator,
                    "read_archive_members",
                    side_effect=(
                        [self.member("README.md")],
                        self.bundle_members(),
                    ),
                ):
                    archive = self.generator.release_archive(
                        "Anime0t4ku/Main_MiSTer_Physical_Disc"
                    )

        self.assertTrue(archive.url.endswith("/MiSTer_Physical-CD.zip"))

    def test_rejects_main_zip_that_differs_from_release_instructions(self) -> None:
        members = [self.member("MiSTer_Different"), self.mgl("_Console/PSX", "CD-PSX")]
        with self.assertRaisesRegex(RuntimeError, "but the ZIP contains"):
            self.build_main(members)

    def test_rejects_mgl_that_selects_a_missing_bundled_core(self) -> None:
        members = [
            self.member("MiSTer_Physical-CD"),
            self.mgl(f"{self.ROOT_FOLDER}/Cores/CDi", "CD-CDi"),
        ]
        with self.assertRaisesRegex(RuntimeError, "missing from the"):
            self.build_main(members)

    def test_rejects_bundled_core_that_no_mgl_launches(self) -> None:
        members = [
            self.member("MiSTer_Physical-CD"),
            self.mgl("_Console/PSX", "CD-PSX"),
            self.member(f"{self.ROOT_FOLDER}/Cores/CDi.rbf"),
        ]
        with self.assertRaisesRegex(RuntimeError, "no MGL launches"):
            self.build_main(members)

    def test_rejects_mgl_without_cd_setname(self) -> None:
        members = [
            self.member("MiSTer_Physical-CD"),
            self.mgl("_Console/PSX", "PSX"),
        ]
        with self.assertRaisesRegex(RuntimeError, r"CD-\* setname"):
            self.build_main(members)


class SolarusGeneratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.generator = load_generator("solarus")

    def member(self, path: str):
        return self.generator.ArchiveMember(
            archive_path=path,
            path=path,
            data=b"data",
        )

    def release_members(self, *extra: str):
        return [
            self.member(path)
            for path in (
                "Scripts/Solarus.sh",
                "_Other/Solarus_20260723.rbf",
                "docs/Solarus/README.md",
                "games/Solarus/libs/libsolarus.so.1",
                "games/Solarus/quest_manager.sh",
                "games/Solarus/quests/PUT-QUESTS-HERE.txt",
                "games/Solarus/solarus-run",
                "games/Solarus/solarus_daemon.sh",
                *extra,
            )
        ]

    def test_installs_every_published_file_in_path_order(self) -> None:
        members = self.release_members()
        selected = self.generator.selected_files(list(reversed(members)))

        self.assertEqual(
            [member.path for member in members],
            [destination for destination, _ in selected],
        )

    def test_rejects_files_outside_the_mister_folders(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "outside its MiSTer folders"):
            self.generator.selected_files(
                self.release_members("build/solarus-mister.tar.gz")
            )

    def test_rejects_a_release_without_exactly_one_dated_core(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "Solarus_YYYYMMDD.rbf"):
            self.generator.selected_files(
                self.release_members("_Other/Solarus_20260724.rbf")
            )

        undated = [
            member
            for member in self.release_members()
            if member.path != "_Other/Solarus_20260723.rbf"
        ]
        undated.append(self.member("_Other/Solarus.rbf"))
        with self.assertRaisesRegex(RuntimeError, "Solarus_YYYYMMDD.rbf"):
            self.generator.selected_files(undated)

    def test_rejects_a_release_missing_the_engine(self) -> None:
        members = [
            member
            for member in self.release_members()
            if member.path != "games/Solarus/solarus-run"
        ]
        with self.assertRaisesRegex(RuntimeError, "games/Solarus/solarus-run"):
            self.generator.selected_files(members)

    def test_asset_pattern_only_accepts_versioned_release_zips(self) -> None:
        pattern = self.generator.ASSET_PATTERN
        self.assertEqual(
            "v1.0.1", pattern.fullmatch("solarus-mister-v1.0.1.zip").group(1)
        )
        self.assertIsNone(pattern.fullmatch("solarus-mister-v1.0.1-debug.zip"))
        self.assertIsNone(pattern.fullmatch("solarus-mister-source.zip"))


if __name__ == "__main__":
    unittest.main()
