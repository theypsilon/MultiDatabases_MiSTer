#!/usr/bin/env python3

from __future__ import annotations

import http.client
import json
import tempfile
import unittest
import urllib.error
from io import BytesIO, StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import call, patch

import db_helpers
from db_helpers import (
    ArchiveMember,
    apply_standard_tags,
    compatible_release_zip,
    database_id,
    database_url,
    expand_shell_variables,
    github_raw_url,
    http_get_bytes,
    read_scripts_app,
    release_tag,
    shell_variable,
    strip_spurious_reboot_flags,
    validate_arm_binary,
    validate_database,
    validate_payload_url,
    write_bundle,
)


def database(folder: str, timestamp: int, *, changed: bool = False) -> dict:
    folders = {"games/changed": {"tags": [0]}} if changed else {}
    return {
        "v": 1,
        "db_id": database_id(folder),
        "db_url": database_url("theypsilon/MultiDatabases_MiSTer", folder),
        "timestamp": timestamp,
        "files": {},
        "folders": folders,
        "tag_dictionary": {"changed": 0} if changed else {},
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


class RebootFlagTests(unittest.TestCase):
    def file(self, *, reboot: bool = True) -> dict:
        description = {
            "hash": "0123456789abcdef0123456789abcdef",
            "size": 1,
            "url": (
                "https://github.com/example/project/releases/download/v1/file"
            ),
            "tags": [0],
        }
        if reboot:
            description["reboot"] = True
        return description

    def database_with(self, files: dict) -> dict:
        value = database("example", 1)
        value["files"] = files
        value["tag_dictionary"] = {"example": 0}
        return value

    def test_strips_reboot_from_mister_prefixed_names(self) -> None:
        value = self.database_with(
            {
                "MiSTer_Physical-CD": self.file(),
                "sub/misterFOO.bin": self.file(),
                "cores/Some.rbf": self.file(),
            }
        )
        strip_spurious_reboot_flags(value)

        self.assertNotIn("reboot", value["files"]["MiSTer_Physical-CD"])
        self.assertNotIn("reboot", value["files"]["sub/misterFOO.bin"])
        self.assertTrue(value["files"]["cores/Some.rbf"]["reboot"])
        validate_database(value)

    def test_strips_reboot_inside_selective_archive_summaries(self) -> None:
        value = database("example", 1)
        value["tag_dictionary"] = {"example": 0}
        value["archives"] = {
            "release": {
                "format": "zip",
                "extract": "selective",
                "archive_file": {
                    "hash": "0123456789abcdef0123456789abcdef",
                    "size": 1,
                    "url": (
                        "https://github.com/example/project/releases/"
                        "download/v1/release.zip"
                    ),
                },
                "summary_inline": {
                    "files": {
                        "MiSTer_Physical-CD": {
                            "hash": "0123456789abcdef0123456789abcdef",
                            "size": 1,
                            "overwrite": True,
                            "reboot": True,
                            "arc_id": "release",
                            "arc_at": "MiSTer_Physical-CD",
                            "tags": [0],
                        }
                    },
                    "folders": {},
                },
            }
        }

        strip_spurious_reboot_flags(value)

        summary_file = value["archives"]["release"]["summary_inline"]["files"][
            "MiSTer_Physical-CD"
        ]
        self.assertNotIn("reboot", summary_file)
        validate_database(value)


class DatabaseUrlTests(unittest.TestCase):
    REPOSITORY = "theypsilon/MultiDatabases_MiSTer"
    BASE = "https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db"

    def test_serves_the_uncompressed_database_by_default(self) -> None:
        self.assertEqual(
            f"{self.BASE}/dreamster/db.json",
            database_url(self.REPOSITORY, "dreamster"),
        )

    def test_serves_the_zipped_database_when_the_entry_asks_for_it(self) -> None:
        self.assertEqual(
            f"{self.BASE}/misterfin/db.json.zip",
            database_url(self.REPOSITORY, "misterfin", compressed=True),
        )

    def test_the_drop_in_ini_follows_the_chosen_url(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "misterfin"
            value = database("misterfin", 100)
            value["db_url"] = database_url(
                self.REPOSITORY, "misterfin", compressed=True
            )
            write_bundle(value, output)

            ini = (output / "downloader_MultiDatabases_misterfin.ini").read_text(
                encoding="utf-8"
            )
        self.assertIn(f"db_url = {self.BASE}/misterfin/db.json.zip", ini)


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


class HttpGetBytesTests(unittest.TestCase):
    URL = "https://github.com/example/project/releases/download/v1/file.zip"

    def http_error(self, status: int) -> urllib.error.HTTPError:
        return urllib.error.HTTPError(
            self.URL,
            status,
            "test failure",
            {},
            None,
        )

    def test_retries_transient_http_and_connection_failures(self) -> None:
        effects = [
            self.http_error(503),
            http.client.RemoteDisconnected("connection dropped"),
            BytesIO(b"payload"),
        ]
        with patch.object(
            db_helpers.urllib.request, "urlopen", side_effect=effects
        ) as urlopen, patch.object(db_helpers.time, "sleep") as sleep, patch.object(
            db_helpers.sys, "stderr", new=StringIO()
        ):
            self.assertEqual(b"payload", http_get_bytes(self.URL))

        self.assertEqual(3, urlopen.call_count)
        self.assertEqual([call(1), call(2)], sleep.call_args_list)

    def test_stops_retrying_after_the_bounded_attempts(self) -> None:
        failures = [
            http.client.RemoteDisconnected("connection dropped") for _ in range(4)
        ]
        with patch.object(
            db_helpers.urllib.request, "urlopen", side_effect=failures
        ) as urlopen, patch.object(db_helpers.time, "sleep") as sleep, patch.object(
            db_helpers.sys, "stderr", new=StringIO()
        ):
            with self.assertRaisesRegex(
                RuntimeError, "Unable to download .*connection dropped"
            ):
                http_get_bytes(self.URL)

        self.assertEqual(4, urlopen.call_count)
        self.assertEqual([call(1), call(2), call(4)], sleep.call_args_list)

    def test_does_not_retry_a_permanent_http_error(self) -> None:
        with patch.object(
            db_helpers.urllib.request,
            "urlopen",
            side_effect=self.http_error(404),
        ) as urlopen, patch.object(db_helpers.time, "sleep") as sleep:
            with self.assertRaisesRegex(RuntimeError, "HTTP 404 while downloading"):
                http_get_bytes(self.URL)

        self.assertEqual(1, urlopen.call_count)
        sleep.assert_not_called()


class ScriptsAppTests(unittest.TestCase):
    APP_FOLDER = "Scripts/.config/ExampleApp"
    LAUNCHER = "Scripts/example.sh"
    BINARY = f"{APP_FOLDER}/example_app"
    # 32-bit little-endian EM_ARM header, then enough bytes to look like a build.
    ARM_BINARY = (
        b"\x7fELF\x01\x01\x01" + bytes(9) + b"\x02\x00\x28\x00" + bytes(600_000)
    )
    SCRIPT = (
        b'#!/bin/bash\n'
        b'VERSION="1.2.3"\n'
        b'BASE="/media/fat/Scripts/.config/ExampleApp"\n'
        b'BIN="$BASE/example_app"\n'
        b'exec "$BIN" "$@"\n'
    )

    def member(self, path: str, data: bytes = b"data") -> ArchiveMember:
        return ArchiveMember(archive_path=path, path=path, data=data)

    def members(self, *extra: ArchiveMember, launcher: bytes | None = None):
        return [
            self.member(self.LAUNCHER, launcher or self.SCRIPT),
            self.member(self.BINARY, self.ARM_BINARY),
            self.member(f"{self.APP_FOLDER}/example.json", b"{}"),
            *extra,
        ]

    def read(self, members, **kwargs):
        return read_scripts_app(members, name="Example", **kwargs)

    def test_reads_the_launcher_binary_and_every_published_file(self) -> None:
        members = self.members()
        app = self.read(list(reversed(members)))

        self.assertEqual(self.LAUNCHER, app.launcher.path)
        self.assertEqual(self.BINARY, app.binary.path)
        self.assertEqual(self.APP_FOLDER, app.folder)
        self.assertEqual(
            [f"{self.APP_FOLDER}/example.json", self.BINARY, self.LAUNCHER],
            [destination for destination, _ in app.files],
        )

    def test_follows_a_renamed_application_folder(self) -> None:
        # The launcher decides where the binary belongs, so a future release can
        # rename its folder without the entry pinning the old name.
        launcher = self.SCRIPT.replace(b"ExampleApp", b"Renamed")
        app = self.read(
            [
                self.member(self.LAUNCHER, launcher),
                self.member("Scripts/.config/Renamed/example_app", self.ARM_BINARY),
            ]
        )

        self.assertEqual("Scripts/.config/Renamed", app.folder)

    def test_rejects_files_outside_the_scripts_folder(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "outside Scripts/"):
            self.read(self.members(self.member("README.md")))

    def test_rejects_files_outside_the_application_folder(self) -> None:
        with self.assertRaisesRegex(RuntimeError, f"outside {self.APP_FOLDER}/"):
            self.read(self.members(self.member("Scripts/.config/other/notes.txt")))

    def test_rejects_a_binary_outside_a_config_subfolder(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "Scripts/.config/<app> folder"):
            self.read(
                [
                    self.member(self.LAUNCHER, self.SCRIPT),
                    self.member("Scripts/example_app", self.ARM_BINARY),
                ]
            )

    def test_rejects_a_launcher_that_runs_another_path(self) -> None:
        launcher = self.SCRIPT.replace(b"example_app", b"example_app_debug")
        with self.assertRaisesRegex(RuntimeError, "does not run /media/fat/"):
            self.read(self.members(launcher=launcher))

    def test_accepts_a_launcher_that_spells_out_the_binary_path(self) -> None:
        launcher = b'#!/bin/sh\nexec "/media/fat/' + self.BINARY.encode() + b'" "$@"\n'
        app = self.read(self.members(launcher=launcher))

        self.assertEqual(3, len(app.files))

    def test_requires_exactly_one_launcher_and_one_binary(self) -> None:
        with self.assertRaisesRegex(RuntimeError, r"exactly one Scripts/\*\.sh"):
            self.read(self.members(self.member("Scripts/extra.sh", b"#!")))
        with self.assertRaisesRegex(RuntimeError, r"exactly one Scripts/\*\.sh"):
            self.read([self.member(self.BINARY, self.ARM_BINARY)])
        with self.assertRaisesRegex(RuntimeError, "exactly one ARM binary"):
            self.read(
                self.members(self.member(f"{self.APP_FOLDER}/helper", self.ARM_BINARY))
            )

    def test_rejects_a_launcher_that_is_not_a_script(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "not a script"):
            self.read(self.members(launcher=b"echo hello\n"))

    def test_rejects_packaged_files_the_user_owns(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "belong to the user"):
            self.read(
                self.members(self.member(f"{self.APP_FOLDER}/config.json", b"{}")),
                user_owned=("config.json",),
            )

        # A trailing slash covers everything below that folder.
        with self.assertRaisesRegex(RuntimeError, "belong to the user"):
            self.read(
                self.members(
                    self.member(f"{self.APP_FOLDER}/Saves/game/state.bin", b"x")
                ),
                user_owned=("Saves/",),
            )

        # A sibling with the same prefix is not part of the subtree.
        self.read(
            self.members(self.member(f"{self.APP_FOLDER}/Saves.md", b"x")),
            user_owned=("Saves/",),
        )

    def test_binary_validation_requires_a_32_bit_arm_build(self) -> None:
        validate_arm_binary(self.BINARY, self.ARM_BINARY)

        with self.assertRaisesRegex(RuntimeError, "not an ELF"):
            validate_arm_binary(self.BINARY, b"MZ" + bytes(600_000))
        x86 = bytearray(self.ARM_BINARY)
        x86[18:20] = b"\x3e\x00"
        with self.assertRaisesRegex(RuntimeError, "little-endian ARM"):
            validate_arm_binary(self.BINARY, bytes(x86))
        with self.assertRaisesRegex(RuntimeError, "implausible size"):
            validate_arm_binary(self.BINARY, self.ARM_BINARY[:1000])

    def test_reads_shell_variables_and_expands_them(self) -> None:
        text = self.SCRIPT.decode()
        self.assertEqual("1.2.3", shell_variable(text, "VERSION"))
        self.assertEqual("unknown", shell_variable("#!/bin/sh\n", "VERSION"))
        self.assertIn(
            '"/media/fat/Scripts/.config/ExampleApp/example_app"',
            expand_shell_variables(text),
        )


class CompatibleReleaseZipTests(unittest.TestCase):
    def release(self, *names: str) -> dict:
        return {
            "tag_name": "v1.2.3",
            "assets": [
                {
                    "name": name,
                    "browser_download_url": (
                        f"https://github.com/example/project/releases/"
                        f"download/v1.2.3/{name}"
                    ),
                }
                for name in names
            ],
        }

    def accept(self, members):
        if members[0].path != "good":
            raise RuntimeError("unexpected layout")
        return "accepted"

    def pick(self, release: dict, layouts: tuple[str, ...]):
        with patch.object(
            db_helpers, "http_get_bytes", side_effect=[b"zip"] * len(layouts)
        ):
            with patch.object(
                db_helpers,
                "read_archive_members",
                side_effect=[
                    [ArchiveMember(archive_path=path, path=path, data=b"x")]
                    for path in layouts
                ],
            ):
                return compatible_release_zip(
                    release, accept=self.accept, context="example release"
                )

    def test_picks_the_asset_that_validates_whatever_it_is_called(self) -> None:
        url, data, accepted = self.pick(
            self.release("docs.zip", "renamed-in-this-release.zip"),
            ("bad", "good"),
        )

        self.assertTrue(url.endswith("/renamed-in-this-release.zip"))
        self.assertEqual(b"zip", data)
        self.assertEqual("accepted", accepted)

    def test_reports_why_every_asset_was_rejected(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "docs.zip: unexpected layout"):
            self.pick(self.release("docs.zip"), ("bad",))

    def test_rejects_an_ambiguous_release(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "multiple compatible"):
            self.pick(self.release("one.zip", "two.zip"), ("good", "good"))

    def test_requires_a_zip_asset(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "does not contain a ZIP"):
            compatible_release_zip(
                self.release("core.rbf"), accept=self.accept, context="example release"
            )

    def test_release_tag_falls_back_to_the_release_name(self) -> None:
        self.assertEqual("v1.2.3", release_tag({"tag_name": "v1.2.3"}))
        self.assertEqual("named", release_tag({"name": "named"}))
        self.assertEqual("unknown", release_tag({}))


class FakeOperatorTags:
    def __init__(self, metadata: dict, broken_mras_ignore: bool) -> None:
        self.aliases = metadata["aliases"]
        self.dictionary: dict[str, int] = {}
        self.used: set[int] = set()

    @staticmethod
    def clean(term: str) -> str:
        return term.lower().replace("-", "").replace("_", "").replace(" ", "")

    def init_aliases(self, aliases: list[list[str]]) -> None:
        for group in [*self.aliases, *aliases]:
            index = len(set(self.dictionary.values()))
            for term in group:
                self.dictionary[self.clean(term)] = index

    def _use_term(self, term: str) -> int:
        cleaned = self.clean(term)
        if cleaned not in self.dictionary:
            self.dictionary[cleaned] = len(set(self.dictionary.values()))
        index = self.dictionary[cleaned]
        self.used.add(index)
        return index

    def get_tags_for_file(self, path: Path) -> list[int]:
        return [self._use_term(path.parts[0])]

    def get_tags_for_folder(self, path: Path) -> list[int]:
        return [self._use_term(path.parts[0])]

    def get_dictionary(self) -> dict[str, int]:
        return {
            term: index
            for term, index in self.dictionary.items()
            if index in self.used
        }


class StandardTagTests(unittest.TestCase):
    def test_applies_operator_tags_and_standard_aliases_to_archive_entries(
        self,
    ) -> None:
        database_value = {
            "v": 1,
            "db_id": "MultiDatabases/example",
            "db_url": "https://example.com/db.json",
            "timestamp": 1,
            "files": {},
            "folders": {},
            "tag_dictionary": {},
            "archives": {
                "release": {
                    "format": "zip",
                    "extract": "selective",
                    "archive_file": {
                        "hash": "0123456789abcdef0123456789abcdef",
                        "size": 1,
                        "url": (
                            "https://github.com/example/project/releases/"
                            "download/v1/release.zip"
                        ),
                    },
                    "summary_inline": {
                        "files": {
                            "games/NES/game.nes": {
                                "hash": "0123456789abcdef0123456789abcdef",
                                "size": 1,
                                "overwrite": True,
                                "arc_id": "release",
                                "arc_at": "game.nes",
                            }
                        },
                        "folders": {
                            "games": {"arc_id": "release"},
                            "games/NES": {"arc_id": "release"},
                        },
                    },
                }
            },
        }
        operator = SimpleNamespace(
            Tags=FakeOperatorTags,
            initial_filter_aliases=[
                ["nes", "famicom"],
                ["console", "console-cores"],
            ],
        )

        apply_standard_tags(
            database_value,
            file_data={"games/NES/game.nes": b"x"},
            filter_terms=("example", "console", "nes"),
            operator_module=operator,
        )
        validate_database(database_value)

        dictionary = database_value["tag_dictionary"]
        self.assertEqual(dictionary["nes"], dictionary["famicom"])
        self.assertEqual(dictionary["console"], dictionary["consolecores"])
        file_tags = database_value["archives"]["release"]["summary_inline"][
            "files"
        ]["games/NES/game.nes"]["tags"]
        self.assertIn(dictionary["example"], file_tags)
        self.assertIn(dictionary["console"], file_tags)
        self.assertIn(dictionary["nes"], file_tags)
        folder_tags = database_value["archives"]["release"]["summary_inline"][
            "folders"
        ]["games/NES"]["tags"]
        self.assertIn(dictionary["example"], folder_tags)
        self.assertIn(dictionary["console"], folder_tags)
        self.assertIn(dictionary["nes"], folder_tags)

    def test_validation_rejects_an_unknown_tag_reference(self) -> None:
        value = database("example", 1, changed=True)
        value["folders"]["games/changed"]["tags"] = [99]
        with self.assertRaisesRegex(RuntimeError, "unknown tag index 99"):
            validate_database(value)

    def test_builds_an_archive_database_with_a_direct_file(self) -> None:
        operator = SimpleNamespace(
            Tags=FakeOperatorTags,
            initial_filter_aliases=[],
        )
        archive_member = db_helpers.ArchiveMember(
            archive_path="core.rbf",
            path="core.rbf",
            data=b"core",
        )
        direct_file = db_helpers.DirectFile(
            path="support/library.so",
            url=(
                "https://raw.githubusercontent.com/example/project/"
                "0123456789abcdef0123456789abcdef01234567/support/library.so"
            ),
            data=b"library",
        )

        with patch.object(db_helpers, "load_db_operator", return_value=operator):
            value = db_helpers.build_selective_archive_database(
                folder="example",
                repository="example/project",
                timestamp=1,
                archive_url=(
                    "https://github.com/example/project/releases/"
                    "download/v1/release.zip"
                ),
                archive_data=b"archive",
                selected_files=(("core.rbf", archive_member),),
                direct_files=(direct_file,),
                description="Installing example",
                filter_terms=("example",),
            )

        self.assertIn("support/library.so", value["files"])
        self.assertIn(
            "core.rbf",
            value["archives"]["release"]["summary_inline"]["files"],
        )
        self.assertIn("support", value["folders"])


if __name__ == "__main__":
    unittest.main()
