#!/usr/bin/env python3

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from db_helpers import (
    apply_standard_tags,
    database_id,
    database_url,
    github_raw_url,
    strip_spurious_reboot_flags,
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


if __name__ == "__main__":
    unittest.main()
