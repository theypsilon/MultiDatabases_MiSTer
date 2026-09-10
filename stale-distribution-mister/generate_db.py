#!/usr/bin/env python3

from __future__ import annotations

import json
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".github"))

from db_helpers import (  # noqa: E402
    databases_have_same_content,
    generator_parser,
    github_raw_url,
    http_get_bytes,
    md5,
    read_archive_members,
)


FOLDER = "stale-distribution-mister"
DATABASE_ID = "distribution_mister"
# A moving URL, used for discovery only: the document it serves is republished
# as is, and the payload URLs inside it are upstream's own pinned ones.
UPSTREAM_DATABASE_URL = (
    "https://raw.githubusercontent.com/MiSTer-devel/Distribution_MiSTer/main/db.json.zip"
)

# The Linux release this database stays on. Distribution keeps only its newest
# Linux in the all_releases tag, so the SD-Installer repository, pinned to the
# commit that published this release, is the immutable source. The hash and
# size were computed from that exact URL when the pin was reviewed.
LINUX_REPOSITORY = "MiSTer-devel/SD-Installer-Win64_MiSTer"
LINUX_RELEASE = "release_20250402"
LINUX_COMMIT = "b8531c7848526d9a8227841923cc4a493cb6e631"
LINUX_URL = github_raw_url(LINUX_REPOSITORY, LINUX_COMMIT, f"{LINUX_RELEASE}.7z")
LINUX_DESCRIPTION: Mapping[str, Any] = {
    "hash": "8dc3acae7d758a80a363fbd7ad31d95d",
    "size": 93_727_644,
    "url": LINUX_URL,
    # Downloader compares this with /MiSTer.version; Distribution derives it
    # from the release date the same way.
    "version": LINUX_RELEASE[-6:],
}
# OPEN DECISION (2026-09-10, awaiting human review): upstream commented out
# apply_linux_update in MiSTer-devel/Distribution_MiSTer@6916c7e6, so its
# published document now carries no linux section at all and
# read_upstream_database fails closed instead of guessing. Whether this entry
# may keep injecting the pin above into a document that ships no linux section
# is a human call, so nothing was relaxed here and the build stays red until it
# is made. If the exception is accepted, record it as a reviewed constant, e.g.
#     UPSTREAM_LINUX_SECTION_OPTIONAL = True
# consulted only for a section that is missing, never for one whose shape
# changed.
SEVEN_ZIP_SIGNATURE = b"7z\xbc\xaf'\x1c"

MAX_DATABASE_ARCHIVE_SIZE = 4_000_000
MAX_DATABASE_SIZE = 16_000_000


def read_upstream_database(archive_data: bytes) -> dict[str, Any]:
    """Read the one db.json document from the official db.json.zip."""
    if len(archive_data) > MAX_DATABASE_ARCHIVE_SIZE:
        raise RuntimeError(
            "Distribution database archive is implausibly large: "
            f"{len(archive_data)} bytes"
        )
    members = read_archive_members(archive_data)
    if len(members) != 1 or members[0].path != "db.json":
        names = ", ".join(sorted(member.path for member in members)) or "none"
        raise RuntimeError(
            f"Distribution database ZIP must contain only db.json, found: {names}"
        )
    if len(members[0].data) > MAX_DATABASE_SIZE:
        raise RuntimeError(
            f"Distribution db.json is implausibly large: {len(members[0].data)} bytes"
        )
    try:
        database = json.loads(members[0].data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Distribution db.json is not valid UTF-8 JSON") from exc
    if not isinstance(database, dict):
        raise RuntimeError("Distribution db.json must contain an object")
    if database.get("db_id") != DATABASE_ID:
        raise RuntimeError(
            "Unexpected Distribution database ID: "
            f"{database.get('db_id') or 'missing'}"
        )
    if not isinstance(database.get("linux"), dict):
        raise RuntimeError(
            "Distribution database no longer carries a linux section to pin"
        )
    return database


def pin_linux(upstream: Mapping[str, Any]) -> dict[str, Any]:
    """The official document with only its linux section replaced."""
    database = dict(upstream)
    database["linux"] = dict(LINUX_DESCRIPTION)
    return database


def validate_linux_payload(data: bytes) -> None:
    """Check a downloaded copy of the pinned Linux release against its pin."""
    if not data.startswith(SEVEN_ZIP_SIGNATURE):
        raise RuntimeError("Pinned Linux release is not a 7z archive")
    if len(data) != LINUX_DESCRIPTION["size"]:
        raise RuntimeError(
            f"Pinned Linux release has the wrong size: {len(data)}, "
            f"expected {LINUX_DESCRIPTION['size']}"
        )
    if md5(data) != LINUX_DESCRIPTION["hash"]:
        raise RuntimeError("Pinned Linux release does not match its MD5 hash")


def write_bundle(database: dict[str, Any], output: Path) -> bool:
    """Publish db.json and db.json.zip, preserving an unchanged bundle.

    The shared write_bundle is not used: it validates the document against the
    layout of this repository's own databases, which the official distribution
    does not follow, and it ships a drop-in INI, which Downloader refuses for
    the distribution_mister section.
    """
    json_path = output / "db.json"
    try:
        previous = json.loads(json_path.read_bytes())
        unchanged = (output / "db.json.zip").is_file() and databases_have_same_content(
            previous, database
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        unchanged = False
    if unchanged:
        print(f"No changes detected for {DATABASE_ID}; preserving existing bundle", flush=True)
        return False

    encoded = (
        json.dumps(database, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")
    if output.exists():
        shutil.rmtree(output) if output.is_dir() else output.unlink()
    output.mkdir(parents=True)
    json_path.write_bytes(encoded)
    with zipfile.ZipFile(
        output / "db.json.zip", "w", compression=zipfile.ZIP_DEFLATED
    ) as archive:
        archive.writestr("db.json", encoded)
    print(f"Generated {DATABASE_ID} in {output}", flush=True)
    return True


def main() -> int:
    parser = generator_parser(
        FOLDER, "Generate the stale Distribution MiSTer database"
    )
    parser.add_argument(
        "--verify-linux-payload",
        action="store_true",
        help="Download the pinned Linux release and verify its hash and size",
    )
    args = parser.parse_args()

    if args.verify_linux_payload:
        validate_linux_payload(http_get_bytes(LINUX_URL))

    upstream = read_upstream_database(http_get_bytes(UPSTREAM_DATABASE_URL))
    write_bundle(pin_linux(upstream), args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
