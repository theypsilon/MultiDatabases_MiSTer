#!/usr/bin/env python3

from __future__ import annotations

import json
import re
import sys
import urllib.parse
from pathlib import Path
from typing import Any, Mapping, NamedTuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".github"))

from db_helpers import (  # noqa: E402
    MD5_RE,
    DirectFile,
    build_direct_database,
    generation_timestamp,
    generator_parser,
    http_get_bytes,
    md5,
    read_archive_members,
    validate_arm_binary,
    validate_payload_url,
    write_bundle,
)


FOLDER = "nblood"
UPSTREAM = "meathax/blood"
UPSTREAM_DATABASE_ID = "meathax/blood"
UPSTREAM_DATABASE_URL = (
    "https://raw.githubusercontent.com/meathax/blood/db/db.json.zip"
)

ARM_BINARY = "arm"
FPGA_CORE = "rbf"


class MirroredFile(NamedTuple):
    kind: str
    size_limits: tuple[int, int]


# The upstream Downloader database is the structured publication interface for
# this port: its base_files_url pins every file to one source commit. This
# reviewed table names every upstream path that is installed, at its upstream
# location, and how its payload is validated. Upstream publishes the RBF under
# _Other since its commit 6783ec31, so the port stays out of the computer
# cores menu without a remap here.
MIRRORED_FILES: Mapping[str, MirroredFile] = {
    "Mister_NBlood": MirroredFile(ARM_BINARY, (500_000, 64_000_000)),
    "_Other/NBlood.rbf": MirroredFile(FPGA_CORE, (1_000_000, 16_000_000)),
    "games/NBlood/NBlood": MirroredFile(ARM_BINARY, (500_000, 64_000_000)),
}

# Upstream paths that are deliberately not installed. README_DATA.md is
# upstream's human-facing note on the game data; this entry's README carries
# the reviewed instructions instead. Any other upstream path fails the
# generator until it has been reviewed into one of these two tables, so a
# payload that upstream adds, renames, or moves is never silently left out of
# the published database.
IGNORED_SOURCE_PATHS = frozenset({"games/NBlood/README_DATA.md"})

MAX_DATABASE_ARCHIVE_SIZE = 2_000_000
MAX_DATABASE_SIZE = 2_000_000
RAW_PAYLOAD_PATTERN = re.compile(
    r"https://raw\.githubusercontent\.com/meathax/blood/"
    r"(?P<revision>[0-9a-f]{40})/(?P<path>.+)"
)


class PublishedFile(NamedTuple):
    path: str
    url: str
    revision: str
    size: int
    digest: str


def read_upstream_database(archive_data: bytes) -> dict[str, Any]:
    """Read the one db.json document from upstream's drop-in ZIP."""
    if len(archive_data) > MAX_DATABASE_ARCHIVE_SIZE:
        raise RuntimeError(
            "NBlood upstream database archive is implausibly large: "
            f"{len(archive_data)} bytes"
        )

    members = read_archive_members(archive_data)
    if len(members) != 1 or members[0].path != "db.json":
        names = ", ".join(sorted(member.path for member in members)) or "none"
        raise RuntimeError(
            "NBlood upstream database ZIP must contain only db.json, found: "
            f"{names}"
        )
    if len(members[0].data) > MAX_DATABASE_SIZE:
        raise RuntimeError(
            "NBlood upstream db.json is implausibly large: "
            f"{len(members[0].data)} bytes"
        )

    try:
        database = json.loads(members[0].data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("NBlood upstream db.json is not valid UTF-8 JSON") from exc

    if not isinstance(database, dict):
        raise RuntimeError("NBlood upstream db.json must contain an object")
    if database.get("v") != 1:
        raise RuntimeError("NBlood upstream database must use format version 1")
    if database.get("db_id") != UPSTREAM_DATABASE_ID:
        raise RuntimeError(
            "Unexpected NBlood upstream database ID: "
            f"{database.get('db_id') or 'missing'}"
        )
    if database.get("db_url") != UPSTREAM_DATABASE_URL:
        raise RuntimeError(
            "Unexpected NBlood upstream database URL: "
            f"{database.get('db_url') or 'missing'}"
        )
    timestamp = database.get("timestamp")
    if not isinstance(timestamp, int) or isinstance(timestamp, bool):
        raise RuntimeError("NBlood upstream database needs an integer timestamp")
    if not isinstance(database.get("files"), dict):
        raise RuntimeError("NBlood upstream database files must be an object")
    return database


def payload_url(
    database: Mapping[str, Any],
    path: str,
    description: Mapping[str, Any],
) -> tuple[str, str]:
    """Resolve a file URL exactly as Downloader does, then require a commit pin."""
    if "url" in description:
        url = description["url"]
    else:
        base_url = database.get("base_files_url")
        if not isinstance(base_url, str) or not base_url:
            raise RuntimeError(f"NBlood upstream file {path} has no download URL")
        url = base_url + urllib.parse.quote(path)

    if not isinstance(url, str):
        raise RuntimeError(f"NBlood upstream file {path} has an invalid URL")
    validate_payload_url(url)

    match = RAW_PAYLOAD_PATTERN.fullmatch(url)
    if match is None or urllib.parse.unquote(match.group("path")) != path:
        raise RuntimeError(
            f"NBlood upstream file {path} must use its immutable "
            f"{UPSTREAM} raw path: {url}"
        )
    return url, match.group("revision")


def select_published_files(database: Mapping[str, Any]) -> tuple[PublishedFile, ...]:
    """Select the reviewed NBlood payload from the upstream database."""
    files = database.get("files")
    if not isinstance(files, dict):
        raise RuntimeError("NBlood upstream database files must be an object")

    unreviewed = sorted(
        str(path)
        for path in files
        if path not in MIRRORED_FILES and path not in IGNORED_SOURCE_PATHS
    )
    if unreviewed:
        raise RuntimeError(
            "NBlood upstream database publishes unreviewed files: "
            + ", ".join(unreviewed)
            + ". Review each one into MIRRORED_FILES or IGNORED_SOURCE_PATHS."
        )

    selected: list[PublishedFile] = []
    for path, mirrored in MIRRORED_FILES.items():
        description = files.get(path)
        if not isinstance(description, dict):
            raise RuntimeError(
                f"NBlood upstream database is missing required file {path}"
            )

        digest = description.get("hash")
        if not isinstance(digest, str) or MD5_RE.fullmatch(digest) is None:
            raise RuntimeError(
                f"NBlood upstream file {path} needs a lowercase MD5 hash"
            )
        size = description.get("size")
        if not isinstance(size, int) or isinstance(size, bool):
            raise RuntimeError(f"NBlood upstream file {path} needs an integer size")
        minimum, maximum = mirrored.size_limits
        if not minimum <= size <= maximum:
            raise RuntimeError(
                f"NBlood upstream file {path} has an implausible size: {size}"
            )

        url, revision = payload_url(database, path, description)
        selected.append(
            PublishedFile(
                path=path, url=url, revision=revision, size=size, digest=digest
            )
        )

    revisions = {item.revision for item in selected}
    if len(revisions) != 1:
        raise RuntimeError(
            "NBlood upstream wrapper, RBF, and engine must come from one commit"
        )
    return tuple(selected)


def validate_published_file(item: PublishedFile, data: bytes) -> None:
    if len(data) != item.size:
        raise RuntimeError(
            f"NBlood upstream file {item.path} has the wrong size: "
            f"expected {item.size}, downloaded {len(data)}"
        )
    if md5(data) != item.digest:
        raise RuntimeError(
            f"NBlood upstream file {item.path} does not match its MD5 hash"
        )

    if MIRRORED_FILES[item.path].kind == ARM_BINARY:
        validate_arm_binary(item.path, data)


def main() -> int:
    args = generator_parser(FOLDER, "Generate the NBlood database").parse_args()
    upstream_database = read_upstream_database(
        http_get_bytes(UPSTREAM_DATABASE_URL)
    )

    direct_files: list[DirectFile] = []
    for item in select_published_files(upstream_database):
        data = http_get_bytes(item.url)
        validate_published_file(item, data)
        direct_files.append(DirectFile(path=item.path, url=item.url, data=data))

    database = build_direct_database(
        folder=FOLDER,
        repository=args.repository,
        timestamp=generation_timestamp(args.timestamp),
        direct_files=direct_files,
        filter_terms=(FOLDER, "other"),
        tag_aliases=((FOLDER, "blood"),),
        # This reviewed three-file list keeps the database well below 10 KB,
        # and the uncompressed db_url it was published with must never change.
        compressed_db_url=False,
    )
    write_bundle(database, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
