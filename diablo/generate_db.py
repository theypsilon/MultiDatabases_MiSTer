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
    validate_install_path,
    validate_payload_url,
    write_bundle,
)


FOLDER = "diablo"
UPSTREAM = "meathax/dbdiablo"
UPSTREAM_DATABASE_ID = "meathax/dbdiablo"
UPSTREAM_DATABASE_URL = (
    "https://raw.githubusercontent.com/meathax/dbdiablo/db/db.json.zip"
)

# The upstream Downloader database is the structured publication interface for
# this port: its base_files_url pins every file to one source commit. This
# entry forwards a reviewed slice of it, at the upstream paths. Nothing outside
# this scope is ever forwarded, however upstream describes it, so a file that
# upstream adds elsewhere (its Main_MiSTer frontend at the root, scripts, other
# cores) can never reach the published database by mistake.
FORWARDED_FILES = frozenset({"_Other/Diablo.rbf", "_Other/Hellfire.rbf"})
FORWARDED_FOLDERS = ("_Other/Diablo", "games/Diablo")

# The contents of the forwarded folders are upstream's business and are not
# inspected file by file: only the two named cores must exist, so that their
# disappearance or renaming fails the generator instead of silently publishing
# a database without them.
REQUIRED_FILES = FORWARDED_FILES

# Retail Diablo and Hellfire archives. Upstream lists them under games/Diablo
# with archive.org download URLs; they are commercial game data that users
# must supply themselves, so they are never forwarded, whatever URL upstream
# gives them. Every other forwarded file must be served from upstream's own
# pinned commit; any other external source fails the generator for review.
RETAIL_GAME_DATA = frozenset(
    {
        "games/Diablo/DIABDAT.MPQ",
        "games/Diablo/hellfire.mpq",
        "games/Diablo/hfmonk.mpq",
        "games/Diablo/hfmusic.mpq",
        "games/Diablo/hfvoice.mpq",
    }
)

MAX_DATABASE_ARCHIVE_SIZE = 2_000_000
MAX_DATABASE_SIZE = 4_000_000
RAW_PAYLOAD_PATTERN = re.compile(
    r"https://raw\.githubusercontent\.com/meathax/dbdiablo/"
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
            "Diablo upstream database archive is implausibly large: "
            f"{len(archive_data)} bytes"
        )

    members = read_archive_members(archive_data)
    if len(members) != 1 or members[0].path != "db.json":
        names = ", ".join(sorted(member.path for member in members)) or "none"
        raise RuntimeError(
            "Diablo upstream database ZIP must contain only db.json, found: "
            f"{names}"
        )
    if len(members[0].data) > MAX_DATABASE_SIZE:
        raise RuntimeError(
            "Diablo upstream db.json is implausibly large: "
            f"{len(members[0].data)} bytes"
        )

    try:
        database = json.loads(members[0].data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Diablo upstream db.json is not valid UTF-8 JSON") from exc

    if not isinstance(database, dict):
        raise RuntimeError("Diablo upstream db.json must contain an object")
    if database.get("v") != 1:
        raise RuntimeError("Diablo upstream database must use format version 1")
    if database.get("db_id") != UPSTREAM_DATABASE_ID:
        raise RuntimeError(
            "Unexpected Diablo upstream database ID: "
            f"{database.get('db_id') or 'missing'}"
        )
    if database.get("db_url") != UPSTREAM_DATABASE_URL:
        raise RuntimeError(
            "Unexpected Diablo upstream database URL: "
            f"{database.get('db_url') or 'missing'}"
        )
    timestamp = database.get("timestamp")
    if not isinstance(timestamp, int) or isinstance(timestamp, bool):
        raise RuntimeError("Diablo upstream database needs an integer timestamp")
    if not isinstance(database.get("files"), dict):
        raise RuntimeError("Diablo upstream database files must be an object")
    return database


def forwarded_folder(path: str) -> str | None:
    """Return the reviewed folder that contains path, if any."""
    for folder in FORWARDED_FOLDERS:
        if path.startswith(folder + "/"):
            return folder
    return None


def is_forwarded(path: str) -> bool:
    """Whether an upstream path lies inside the reviewed forwarding scope."""
    if path in RETAIL_GAME_DATA:
        return False
    return path in FORWARDED_FILES or forwarded_folder(path) is not None


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
            raise RuntimeError(f"Diablo upstream file {path} has no download URL")
        url = base_url + urllib.parse.quote(path)

    if not isinstance(url, str):
        raise RuntimeError(f"Diablo upstream file {path} has an invalid URL")
    validate_payload_url(url)

    match = RAW_PAYLOAD_PATTERN.fullmatch(url)
    if match is None or urllib.parse.unquote(match.group("path")) != path:
        raise RuntimeError(
            f"Diablo upstream file {path} must use its immutable "
            f"{UPSTREAM} raw path: {url}"
        )
    return url, match.group("revision")


def select_published_files(database: Mapping[str, Any]) -> tuple[PublishedFile, ...]:
    """Select the forwarded slice of the upstream database."""
    files = database.get("files")
    if not isinstance(files, dict):
        raise RuntimeError("Diablo upstream database files must be an object")

    selected: list[PublishedFile] = []
    skipped: list[str] = []
    for path in sorted(files, key=str):
        if not isinstance(path, str):
            raise RuntimeError(f"Diablo upstream database has a non-string path: {path!r}")
        if not is_forwarded(path):
            skipped.append(path)
            continue
        # A path such as _Other/Diablo/../MiSTer passes the prefix check, so
        # traversal and restricted roots are rejected here before anything
        # inside the scope is trusted.
        validate_install_path(path)

        description = files[path]
        if not isinstance(description, dict):
            raise RuntimeError(f"Diablo upstream file {path} must be an object")
        digest = description.get("hash")
        if not isinstance(digest, str) or MD5_RE.fullmatch(digest) is None:
            raise RuntimeError(
                f"Diablo upstream file {path} needs a lowercase MD5 hash"
            )
        size = description.get("size")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise RuntimeError(
                f"Diablo upstream file {path} needs a non-negative integer size"
            )

        url, revision = payload_url(database, path, description)
        selected.append(
            PublishedFile(
                path=path, url=url, revision=revision, size=size, digest=digest
            )
        )

    published = {item.path for item in selected}
    missing = sorted(REQUIRED_FILES.difference(published))
    if missing:
        raise RuntimeError(
            "Diablo upstream database is missing required files: "
            + ", ".join(missing)
        )

    revisions = {item.revision for item in selected}
    if len(revisions) != 1:
        raise RuntimeError(
            "Diablo upstream files must all come from one commit, found: "
            + ", ".join(sorted(revisions))
        )
    if skipped:
        print(
            "Not forwarding upstream paths outside the reviewed scope: "
            + ", ".join(skipped),
            file=sys.stderr,
        )
    return tuple(selected)


def validate_published_file(item: PublishedFile, data: bytes) -> None:
    if len(data) != item.size:
        raise RuntimeError(
            f"Diablo upstream file {item.path} has the wrong size: "
            f"expected {item.size}, downloaded {len(data)}"
        )
    if md5(data) != item.digest:
        raise RuntimeError(
            f"Diablo upstream file {item.path} does not match its MD5 hash"
        )


def main() -> int:
    args = generator_parser(FOLDER, "Generate the Diablo database").parse_args()
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
        tag_aliases=((FOLDER, "hellfire"),),
        # The forwarded asset tree holds hundreds of files, so the database is
        # far above 10 KB and was published compressed. This must never change.
        compressed_db_url=True,
    )
    write_bundle(database, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
