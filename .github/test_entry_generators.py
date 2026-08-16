#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import unittest
import zipfile
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

    def test_pins_the_zipped_database_url(self) -> None:
        source = (ROOT / "misterfin" / "generate_db.py").read_text(encoding="utf-8")
        self.assertIn("compressed_db_url=True", source)

    def test_asset_pattern_accepts_two_and_three_part_versions(self) -> None:
        pattern = self.generator.ASSET_PATTERN
        self.assertEqual("v0.9", pattern.fullmatch("misterfin-v0.9.zip").group(1))
        self.assertEqual(
            "v0.9.1", pattern.fullmatch("misterfin-v0.9.1.zip").group(1)
        )
        self.assertIsNone(pattern.fullmatch("misterfin-source.zip"))


class ScriptsAppEntryTests:
    """Shared checks for the entries that ship a Scripts launcher plus payload."""

    APP_FOLDER: str
    LAUNCHER: str
    BINARY: str
    EXTRA = ""
    # 32-bit little-endian EM_ARM header, then enough bytes to look like a build.
    ARM_BINARY = (
        b"\x7fELF\x01\x01\x01" + bytes(9) + b"\x02\x00\x28\x00" + bytes(600_000)
    )

    def launcher_script(self) -> bytes:
        app, binary = self.APP_FOLDER.rsplit("/", 1)[-1], self.BINARY.rsplit("/", 1)[-1]
        return (
            b"#!/bin/bash\n"
            b'VERSION="9.9.9"\n'
            b'BASE="/media/fat/Scripts/.config/' + app.encode() + b'"\n'
            b'exec "$BASE/' + binary.encode() + b'" "$@"\n'
        )

    def member(self, path: str, data: bytes = b"data"):
        return self.generator.ArchiveMember(archive_path=path, path=path, data=data)

    def release_members(self, *extra):
        published = [
            self.member(self.LAUNCHER, self.launcher_script()),
            self.member(self.BINARY, self.ARM_BINARY),
        ]
        if self.EXTRA:
            published.append(self.member(self.EXTRA, b"{}"))
        return [*published, *extra]

    def test_reads_the_published_release_layout(self) -> None:
        app = self.generator.read_app(self.release_members())

        self.assertEqual(self.APP_FOLDER, app.folder)
        self.assertEqual(
            sorted(member.path for member in self.release_members()),
            [destination for destination, _ in app.files],
        )


class MisterHiFiGeneratorTests(ScriptsAppEntryTests, unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.generator = load_generator("mister-hifi")

    APP_FOLDER = "Scripts/.config/MiSTerHiFi"
    LAUNCHER = "Scripts/misterhifi.sh"
    BINARY = f"{APP_FOLDER}/mister_hifi"
    EXTRA = f"{APP_FOLDER}/smb.example.json"

    def test_rejects_packaged_settings_and_credentials(self) -> None:
        # Installing them would overwrite the settings MiSTer Hi-Fi writes on
        # first launch and the user's own SMB share credentials.
        self.assertEqual(("config.json", "smb.json"), self.generator.USER_OWNED)
        for name in self.generator.USER_OWNED:
            with self.subTest(name=name):
                with self.assertRaisesRegex(RuntimeError, "belong to the user"):
                    self.generator.read_app(
                        self.release_members(
                            self.member(f"{self.APP_FOLDER}/{name}", b"{}")
                        )
                    )

    def test_keeps_the_example_share_configuration(self) -> None:
        # smb.example.json is the template the user copies; only the real
        # smb.json is off limits.
        app = self.generator.read_app(self.release_members())

        self.assertIn(self.EXTRA, [destination for destination, _ in app.files])


class CollectionLauncherGeneratorTests(ScriptsAppEntryTests, unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.generator = load_generator("collection-launcher")

    APP_FOLDER = "Scripts/.config/CollectionLauncher"
    LAUNCHER = "Scripts/CollectionLauncher.sh"
    BINARY = f"{APP_FOLDER}/collection_launcher"

    def test_rejects_packaged_collections_and_runtime_files(self) -> None:
        # Collections holds the user's own collections and tmp the launcher's
        # log; a release packing either would overwrite them on every run.
        self.assertEqual(("Collections/", "tmp/"), self.generator.USER_OWNED)
        for path in ("Collections/MyGames/collection.json", "tmp/CollectionLauncher.log"):
            with self.subTest(path=path):
                with self.assertRaisesRegex(RuntimeError, "belong to the user"):
                    self.generator.read_app(
                        self.release_members(
                            self.member(f"{self.APP_FOLDER}/{path}", b"x")
                        )
                    )

    def test_creates_the_collections_folder_beside_the_binary(self) -> None:
        # The ZIP only carries it as an empty folder, so the database has to
        # declare it - and it follows the folder the release actually uses.
        app = self.generator.read_app(self.release_members())
        self.assertEqual(
            (f"{self.APP_FOLDER}/Collections",), self.generator.extra_folders(app)
        )

        renamed = self.generator.ScriptsApp(
            launcher=self.member(self.LAUNCHER),
            binary=self.member(self.BINARY),
            folder="Scripts/.config/Renamed",
            files=(),
        )
        self.assertEqual(
            ("Scripts/.config/Renamed/Collections",),
            self.generator.extra_folders(renamed),
        )

class DiscToolsGeneratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.generator = load_generator("disc-tools")

    ARM_BINARY = (
        b"\x7fELF\x01\x01\x01" + bytes(9) + b"\x02\x00\x28\x00" + bytes(600_000)
    )
    ARM_HELPER = b"\x7fELF\x01\x01\x01" + bytes(9) + b"\x02\x00\x28\x00" + bytes(64)

    def member(self, path: str, data: bytes = b"data"):
        return self.generator.ArchiveMember(archive_path=path, path=path, data=data)

    def release_members(self, *extra):
        launcher = (
            b"#!/bin/bash\n"
            b'VERSION="1.0.0"\n'
            b'BASE="/media/fat/Scripts/.config/disctools"\n'
            b'BIN="$BASE/disctools"\n'
            b'exec "$BIN" "$@"\n'
        )
        return [
            self.member(self.generator.LAUNCHER, launcher),
            self.member(self.generator.MAIN_BINARY, self.ARM_BINARY),
            *[
                self.member(path, self.ARM_HELPER)
                for path in self.generator.HELPERS
            ],
            self.member(f"{self.generator.APP_FOLDER}/licenses/GPL-2.0.txt", b"GPL"),
            *extra,
        ]

    def test_installs_the_complete_release_zip_payload(self) -> None:
        members = self.release_members()
        selected = self.generator.selected_files(list(reversed(members)))
        self.assertEqual(
            sorted(member.path for member in members),
            [destination for destination, _ in selected],
        )

    def test_rejects_files_outside_the_packaged_mister_layout(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "installs outside"):
            self.generator.selected_files(
                self.release_members(self.member("README.md", b"source tree"))
            )

    def test_rejects_files_inside_runtime_log_or_temp_directories(self) -> None:
        for path in (
            f"{self.generator.APP_FOLDER}/logs/disctools.log",
            f"{self.generator.APP_FOLDER}/temp/work.bin",
        ):
            with self.subTest(path=path):
                with self.assertRaisesRegex(RuntimeError, "runtime log/temp"):
                    self.generator.selected_files(
                        self.release_members(self.member(path, b"runtime"))
                    )

    def test_requires_every_bundled_helper(self) -> None:
        missing = self.generator.HELPERS[0]
        members = [m for m in self.release_members() if m.path != missing]
        with self.assertRaisesRegex(RuntimeError, "missing required files"):
            self.generator.selected_files(members)

    def test_rejects_non_arm_helper_binaries(self) -> None:
        helper = self.generator.HELPERS[-1]
        members = [
            self.member(m.path, b"not-arm" if m.path == helper else m.data)
            for m in self.release_members()
        ]
        with self.assertRaisesRegex(RuntimeError, "not a 32-bit little-endian ARM ELF"):
            self.generator.selected_files(members)


class PhysicalDiscGeneratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.generator = load_generator("physical-disc")

    ROOT_FOLDER = "_Physical Disc Cores"

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
            self.mgl("_Console/PSX", "A0CD-PSX"),
            self.mgl("_Console/MegaCD", "A0CD-MegaCD"),
            self.mgl(f"{self.ROOT_FOLDER}/Cores/CDi", "A0CD-CDi"),
            self.member(f"{self.ROOT_FOLDER}/Cores/CDi.rbf"),
        ]

    def build_main(self, members):
        return self.generator.main_archive(
            "Main_MiSTer_Physical_Disc",
            "v0.30",
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
        self.assertIn(f"{self.ROOT_FOLDER}/A0CD-PSX.mgl", destinations)

    def test_selects_compatible_zip_without_parsing_release_notes(self) -> None:
        release = {
            "tag_name": "v0.30",
            # Human-facing prose must not influence artifact selection.
            "body": "[A0CD-*]\nmain=MiSTer_Untrusted-Release-Note\n",
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

    def test_rejects_an_unreviewed_main_executable_rename(self) -> None:
        members = [
            self.member("MiSTer_Different"),
            self.mgl("_Console/PSX", "A0CD-PSX"),
        ]
        with self.assertRaisesRegex(RuntimeError, "expected MiSTer_Physical-CD"):
            self.build_main(members)

    def test_rejects_mgl_that_selects_a_missing_bundled_core(self) -> None:
        members = [
            self.member("MiSTer_Physical-CD"),
            self.mgl(f"{self.ROOT_FOLDER}/Cores/CDi", "A0CD-CDi"),
        ]
        with self.assertRaisesRegex(RuntimeError, "missing from the"):
            self.build_main(members)

    def test_rejects_bundled_core_that_no_mgl_launches(self) -> None:
        members = [
            self.member("MiSTer_Physical-CD"),
            self.mgl("_Console/PSX", "A0CD-PSX"),
            self.member(f"{self.ROOT_FOLDER}/Cores/CDi.rbf"),
        ]
        with self.assertRaisesRegex(RuntimeError, "no MGL launches"):
            self.build_main(members)

    def test_rejects_mgl_without_a0cd_setname(self) -> None:
        members = [
            self.member("MiSTer_Physical-CD"),
            self.mgl("_Console/PSX", "PSX"),
        ]
        with self.assertRaisesRegex(RuntimeError, r"A0CD-\* setname"):
            self.build_main(members)

    def test_rejects_mgl_using_the_retired_cd_setname(self) -> None:
        # The old CD-* namespace also matched the stock CD-i core setname, so
        # upstream moved the launchers to A0CD-* and MiSTer.ini follows.
        members = [
            self.member("MiSTer_Physical-CD"),
            self.mgl("_Console/PSX", "CD-PSX"),
        ]
        with self.assertRaisesRegex(RuntimeError, r"A0CD-\* setname"):
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

    def test_drops_the_release_provenance_file(self) -> None:
        expected = self.release_members()
        selected = self.generator.selected_files(
            self.release_members("BUILD-INFO.txt")
        )

        self.assertEqual(
            [member.path for member in expected],
            [destination for destination, _ in selected],
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


class MalditaCastillaGeneratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.generator = load_generator("maldita-castilla")

    ARM_ELF = (
        b"\x7fELF\x01\x01\x01" + bytes(9) + b"\x02\x00\x28\x00" + bytes(32)
    )
    ARM_BINARY = ARM_ELF + bytes(600_000) + b"GLIBC_2.29\0"

    def member(self, path: str, data: bytes = b"data"):
        return self.generator.ArchiveMember(
            archive_path=path,
            path=path,
            data=data,
        )

    def apk(self) -> bytes:
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as archive:
            archive.writestr("lib/armeabi-v7a/libopenal.so", b"openal")
            archive.writestr("lib/armeabi-v7a/libyoyo.so", b"runner")
        return output.getvalue()

    def release_members(self, *extra):
        generator = self.generator
        gles = self.ARM_ELF + b"gles"
        contents = {
            "README.md": b"release instructions",
            "_Other/MalditaCastilla_20260808.rbf": bytes(1_000_000),
            generator.LAUNCHER: (
                b"#!/bin/bash\n"
                b'CORENAME="Maldita Castilla"\n'
                b'HANDLER="/media/fat/games/$CORENAME/launch.sh"\n'
                b'RBF_GLOB="/media/fat/_Other/MalditaCastilla_*.rbf"\n'
            ),
            generator.CORES_MENU_SETUP: (
                b"#!/bin/bash\n"
                b'WRAPPER_DEFAULT="/media/fat/games/gmloader/MiSTer_Maldita"\n'
                b'INI_DEFAULT="/media/fat/MiSTer.ini"\n'
            ),
            generator.ENGINE_LAUNCHER: (
                b"#!/bin/bash\n"
                b'GAMEDIR="/media/fat/games/gmloader"\n'
                b"exec ./gmloader -c gmloader.json\n"
            ),
            generator.MEMORY_MODULE_LOADER: (
                b"#!/bin/bash\n"
                b'KERNEL="$(uname -r)"\n'
                b'MODULE="mem_wc-$KERNEL.ko"\n'
            ),
            "games/Maldita Castilla/mem_wc-5.15.1-MiSTer.ko": self.ARM_ELF,
            generator.ENGINE: self.ARM_BINARY,
            generator.WRAPPER: (
                self.ARM_BINARY
                + f"/media/fat/{generator.ENGINE_LAUNCHER}".encode()
            ),
            generator.CONFIG: json.dumps(
                {
                    "save_dir": "saves",
                    "apk_path": "mygame.apk",
                    "blitter": 2,
                    "force_platform": "os_android",
                }
            ).encode(),
            generator.APK: self.apk(),
            generator.GAME_DATA: b"original game data",
            "games/gmloader/saves/options.ini": b"[Maldita Castilla]\n",
            generator.LICENCE: (
                b"Attribution-NonCommercial-NoDerivatives 4.0 International\n"
            ),
            generator.CREDITS: b"Maldita Castilla by Locomalito\n",
            "games/gmloader/APKs/README.txt": b"user APK folder",
            "games/gmloader/lib/armeabi-v7a/libstdc++.so": self.ARM_ELF,
            "games/gmloader/libGLES_sw.so": gles,
            "games/gmloader/mesa/libEGL.so.1": self.ARM_ELF,
            "games/gmloader/mesa/libGLESv2.so.2": gles,
            "games/gmloader/mesa/libdrm.so.2": self.ARM_ELF,
            "games/gmloader/mesa/libglapi.so.0": self.ARM_ELF,
            "games/gmloader/mesa/libtinfo.so.6": self.ARM_ELF,
            "games/gmloader/mesa/swrast_dri.so": self.ARM_ELF,
        }
        return [self.member(path, data) for path, data in contents.items()] + list(
            extra
        )

    def fixture_hashes(self, members) -> dict[str, str]:
        by_path = {member.path: member for member in members}
        return {
            path: hashlib.sha256(by_path[path].data).hexdigest()
            for path in self.generator.GAME_FILE_SHA256
            if path in by_path
        }

    def select(self, members):
        with patch.object(
            self.generator,
            "GAME_FILE_SHA256",
            self.fixture_hashes(members),
        ):
            return self.generator.selected_files(members)

    def replace(self, members, path: str, data: bytes):
        return [
            self.member(path, data) if member.path == path else member
            for member in members
        ]

    def test_installs_the_runtime_but_not_the_generic_root_readme(self) -> None:
        members = self.release_members()
        selected = self.select(list(reversed(members)))

        expected = sorted(
            member.path for member in members if member.path != "README.md"
        )
        self.assertEqual(expected, [path for path, _ in selected])
        self.assertEqual(23, len(selected))

    def test_rejects_files_outside_the_mister_install_roots(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "outside its MiSTer folders"):
            self.select(
                self.release_members(self.member("build/debug-symbols.tar.gz"))
            )

    def test_rejects_unnamespaced_scripts_that_could_collide(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "unnamespaced Scripts entry"):
            self.select(
                self.release_members(
                    self.member("Scripts/update_all.sh", b"#!/bin/bash\n")
                )
            )

    def test_rejects_user_owned_and_daemon_controlled_files(self) -> None:
        unsafe = (
            "games/Maldita Castilla/_handler.sh",
            "games/Maldita Castilla/takeover.env",
            "games/gmloader/bench.env",
            "games/gmloader/saves/slot1.sav",
            "games/gmloader/APKs/MyGame.apk",
        )
        for path in unsafe:
            with self.subTest(path=path):
                with self.assertRaisesRegex(RuntimeError, "user|daemon"):
                    self.select(self.release_members(self.member(path)))

    def test_rejects_case_collisions_that_are_ambiguous_on_fat(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "Case-colliding"):
            self.select(
                self.release_members(
                    self.member("scripts/malditacastilla.sh", b"#!/bin/bash\n")
                )
            )

    def test_rejects_a_second_or_undated_core(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "exactly one"):
            self.select(
                self.release_members(
                    self.member(
                        "_Other/MalditaCastilla_20260809.rbf", bytes(1_000_000)
                    )
                )
            )

        renamed = [
            self.member("_Other/MalditaCastilla.rbf", member.data)
            if member.path == "_Other/MalditaCastilla_20260808.rbf"
            else member
            for member in self.release_members()
        ]
        with self.assertRaisesRegex(RuntimeError, "unexpected files under _Other"):
            self.select(renamed)

    def test_rejects_a_missing_engine(self) -> None:
        members = [
            member
            for member in self.release_members()
            if member.path != self.generator.ENGINE
        ]
        with self.assertRaisesRegex(RuntimeError, self.generator.ENGINE):
            self.select(members)

    def test_rejects_an_incompatible_arm_engine(self) -> None:
        members = self.replace(
            self.release_members(), self.generator.ENGINE, b"MZ" + bytes(600_000)
        )
        with self.assertRaisesRegex(RuntimeError, "not an ELF"):
            self.select(members)

    def test_rejects_a_wrapper_without_the_launch_hook(self) -> None:
        members = self.replace(
            self.release_members(), self.generator.WRAPPER, self.ARM_BINARY
        )
        with self.assertRaisesRegex(RuntimeError, "main= wrapper"):
            self.select(members)

    def test_rejects_changed_game_bytes_until_they_are_reviewed(self) -> None:
        members = self.release_members()
        expected = self.fixture_hashes(members)
        changed = self.replace(members, self.generator.GAME_DATA, b"changed")

        with patch.object(self.generator, "GAME_FILE_SHA256", expected):
            with self.assertRaisesRegex(RuntimeError, "reviewed, unmodified"):
                self.generator.selected_files(changed)

    def test_release_bundle_version_must_match_the_release_tag(self) -> None:
        release = {
            "tag_name": "v1.2.3",
            "assets": [
                {
                    "name": "MalditaCastilla-MiSTer-v1.2.3.zip",
                    "browser_download_url": (
                        "https://github.com/gmcnaught/maldita.castilla-mister/"
                        "releases/"
                        "download/v1.2.3/MalditaCastilla-MiSTer-v1.2.3.zip"
                    ),
                }
            ],
        }
        asset, version = self.generator.release_asset(release)
        self.assertEqual("v1.2.3", version)
        self.assertEqual(release["assets"][0], asset)

        release["tag_name"] = "v1.2.4"
        with self.assertRaisesRegex(RuntimeError, "version differ"):
            self.generator.release_asset(release)

        release["tag_name"] = "v1.2.3"
        release["assets"].append(dict(release["assets"][0]))
        with self.assertRaisesRegex(RuntimeError, "exactly one"):
            self.generator.release_asset(release)

    def test_download_validation_checks_digest_and_expansion_limits(self) -> None:
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as archive:
            archive.writestr("file.bin", b"four")
        data = output.getvalue()
        asset = {
            "size": len(data),
            "digest": f"sha256:{hashlib.sha256(data).hexdigest()}",
        }

        with patch.object(self.generator, "MIN_ARCHIVE_SIZE", 0):
            self.generator.validate_archive_download(asset, data)
            with self.assertRaisesRegex(RuntimeError, "SHA-256"):
                self.generator.validate_archive_download(
                    {**asset, "digest": f"sha256:{'0' * 64}"}, data
                )
            with patch.object(self.generator, "MAX_MEMBER_SIZE", 3):
                with self.assertRaisesRegex(RuntimeError, "Oversized file"):
                    self.generator.validate_archive_download(asset, data)

    def test_keeps_the_database_url_uncompressed(self) -> None:
        source = (ROOT / "maldita-castilla" / "generate_db.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("compressed_db_url=True", source)


class MisterDiscGeneratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.generator = load_generator("mister-disc")

    def test_mgl_destinations_land_in_disc_cores(self) -> None:
        self.assertEqual(
            "_Disc_Cores/PlayStation.mgl",
            self.generator.mgl_destination("PlayStation.mgl"),
        )
        destinations = [
            self.generator.mgl_destination(name)
            for name in self.generator.MGL_FILES
        ]
        self.assertEqual(7, len(destinations))
        self.assertEqual(len(destinations), len(set(destinations)))
        for destination in destinations:
            self.assertTrue(destination.startswith("_Disc_Cores/"))
            self.assertTrue(destination.endswith(".mgl"))

    def test_asset_patterns_do_not_cross_match(self) -> None:
        self.assertIsNotNone(self.generator.PLAIN_ASSET.fullmatch("MiSTer-disc"))
        self.assertIsNone(self.generator.PLAIN_ASSET.fullmatch("MiSTer-disc-RA"))
        self.assertIsNotNone(self.generator.RA_ASSET.fullmatch("MiSTer-disc-RA"))
        self.assertIsNone(self.generator.RA_ASSET.fullmatch("MiSTer-disc"))

    def test_shipped_mgls_pass_validation(self) -> None:
        mgl_dir = ROOT / "mister-disc" / "mgl"
        for name in self.generator.MGL_FILES:
            data = (mgl_dir / name).read_bytes()
            self.generator.validate_mgl(name, data)

    def test_mgl_validation_rejects_missing_same_dir(self) -> None:
        bad = (
            b"<mistergamedescription>\n"
            b"    <rbf>_Console/PSX</rbf>\n"
            b"    <setname>CD-PSX</setname>\n"
            b"</mistergamedescription>\n"
        )
        with self.assertRaises(RuntimeError):
            self.generator.validate_mgl("PlayStation.mgl", bad)

    def test_binary_validation_requires_elf(self) -> None:
        with self.assertRaises(RuntimeError):
            self.generator.validate_main_binary("MiSTer-disc", b"MZ" + b"\0" * 600000)
        self.generator.validate_main_binary(
            "MiSTer-disc", b"\x7fELF" + b"\0" * 600000
        )

    def test_translate_payload_ships_and_validates(self) -> None:
        payload_dir = ROOT / "mister-disc" / "payload"
        self.assertEqual(4, len(self.generator.TRANSLATE_FILES))
        for rel in self.generator.TRANSLATE_FILES:
            data = (payload_dir / rel).read_bytes()
            self.generator.validate_script(rel, data)

    def test_translate_payload_excludes_user_owned_files(self) -> None:
        joined = " ".join(self.generator.TRANSLATE_FILES)
        self.assertNotIn("translate.ini", joined)
        self.assertNotIn("hotkey.cfg", joined)


if __name__ == "__main__":
    unittest.main()
