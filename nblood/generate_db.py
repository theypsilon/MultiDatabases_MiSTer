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

# The upstream Downloader database is the structured publication interface for
# this preview: its base_files_url pins the matching wrapper, RBF, and engine to
# one source commit. Only these paths are intentionally mirrored. In particular,
# README_DATA.md and any future unrelated upstream paths remain excluded.
SOURCE_DESTINATIONS = (
    ("Mister_NBlood", "Mister_NBlood"),
    ("_Computer/NBlood.rbf", "_Other/NBlood.rbf"),
    ("games/NBlood/NBlood", "games/NBlood/NBlood"),
)

ARM_PATHS = frozenset({"Mister_NBlood", "games/NBlood/NBlood"})
PAYLOAD_SIZE_LIMITS = {
    "Mister_NBlood": (500_000, 64_000_000),
    "_Computer/NBlood.rbf": (1_000_000, 16_000_000),
    "games/NBlood/NBlood": (500_000, 64_000_000),
}
MAX_DATABASE_ARCHIVE_SIZE = 2_000_000
MAX_DATABASE_SIZE = 2_000_000
RAW_PAYLOAD_PATTERN = re.compile(
    r"https://raw\.githubusercontent\.com/meathax/blood/"
    r"(?P<revision>[0-9a-f]{40})/(?P<path>.+)"
)


class PublishedFile(NamedTuple):
    source_path: str
    destination: str
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
    source_path: str,
    description: Mapping[str, Any],
) -> tuple[str, str]:
    """Resolve a file URL exactly as Downloader does, then require a commit pin."""
    if "url" in description:
        url = description["url"]
    else:
        base_url = database.get("base_files_url")
        if not isinstance(base_url, str) or not base_url:
            raise RuntimeError(
                f"NBlood upstream file {source_path} has no download URL"
            )
        url = base_url + urllib.parse.quote(source_path)

    if not isinstance(url, str):
        raise RuntimeError(f"NBlood upstream file {source_path} has an invalid URL")
    validate_payload_url(url)

    match = RAW_PAYLOAD_PATTERN.fullmatch(url)
    if match is None or urllib.parse.unquote(match.group("path")) != source_path:
        raise RuntimeError(
            f"NBlood upstream file {source_path} must use its immutable "
            f"{UPSTREAM} raw path: {url}"
        )
    return url, match.group("revision")


def select_published_files(database: Mapping[str, Any]) -> tuple[PublishedFile, ...]:
    """Select the fixed three-file NBlood payload and remap its RBF to _Other."""
    files = database.get("files")
    if not isinstance(files, dict):
        raise RuntimeError("NBlood upstream database files must be an object")

    selected: list[PublishedFile] = []
    for source_path, destination in SOURCE_DESTINATIONS:
        description = files.get(source_path)
        if not isinstance(description, dict):
            raise RuntimeError(
                f"NBlood upstream database is missing required file {source_path}"
            )

        digest = description.get("hash")
        if not isinstance(digest, str) or MD5_RE.fullmatch(digest) is None:
            raise RuntimeError(
                f"NBlood upstream file {source_path} needs a lowercase MD5 hash"
            )
        size = description.get("size")
        if not isinstance(size, int) or isinstance(size, bool):
            raise RuntimeError(
                f"NBlood upstream file {source_path} needs an integer size"
            )
        minimum, maximum = PAYLOAD_SIZE_LIMITS[source_path]
        if not minimum <= size <= maximum:
            raise RuntimeError(
                f"NBlood upstream file {source_path} has an implausible size: {size}"
            )

        url, revision = payload_url(database, source_path, description)
        selected.append(
            PublishedFile(
                source_path=source_path,
                destination=destination,
                url=url,
                revision=revision,
                size=size,
                digest=digest,
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
            f"NBlood upstream file {item.source_path} has the wrong size: "
            f"expected {item.size}, downloaded {len(data)}"
        )
    if md5(data) != item.digest:
        raise RuntimeError(
            f"NBlood upstream file {item.source_path} does not match its MD5 hash"
        )

    if item.source_path in ARM_PATHS:
        validate_arm_binary(item.destination, data)
    elif item.source_path == "_Computer/NBlood.rbf":
        minimum, maximum = PAYLOAD_SIZE_LIMITS[item.source_path]
        if not minimum <= len(data) <= maximum:
            raise RuntimeError(
                f"NBlood.rbf has an implausible size: {len(data)}"
            )


def main() -> int:
    args = generator_parser(FOLDER, "Generate the NBlood database").parse_args()
    upstream_database = read_upstream_database(
        http_get_bytes(UPSTREAM_DATABASE_URL)
    )

    direct_files: list[DirectFile] = []
    for item in select_published_files(upstream_database):
        data = http_get_bytes(item.url)
        validate_published_file(item, data)
        direct_files.append(
            DirectFile(path=item.destination, url=item.url, data=data)
        )

    database = build_direct_database(
        folder=FOLDER,
        repository=args.repository,
        timestamp=generation_timestamp(args.timestamp),
        direct_files=direct_files,
        filter_terms=(FOLDER, "other"),
        tag_aliases=((FOLDER, "blood"),),
        # This fixed three-file database is expected to remain below 10 KB.
        compressed_db_url=False,
    )
    write_bundle(database, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
