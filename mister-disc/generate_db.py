#!/usr/bin/env python3

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".github"))

from db_helpers import (  # noqa: E402
    DirectFile,
    build_direct_database,
    generation_timestamp,
    generator_parser,
    git_file_revision,
    github_latest_release,
    github_raw_url,
    http_get_bytes,
    matching_release_asset,
    release_asset_url,
    write_bundle,
)


FOLDER = "mister-disc"
UPSTREAM = "theshaneobrien/mister-disc-drive-support"

PLAIN_ASSET = re.compile(r"MiSTer-disc")
RA_ASSET = re.compile(r"MiSTer-disc-RA")

MGL_FILES = (
    "3DO.mgl",
    "Mega CD.mgl",
    "Neo Geo CD.mgl",
    "Philips CD-i.mgl",
    "PlayStation.mgl",
    "Saturn.mgl",
    "TurboGrafx-CD.mgl",
)


def mgl_destination(name: str) -> str:
    return f"_Disc Cores/{name}"


def validate_main_binary(name: str, data: bytes) -> None:
    if not data.startswith(b"\x7fELF"):
        raise RuntimeError(f"{name} is not an ELF binary")
    if not 500_000 < len(data) < 8_000_000:
        raise RuntimeError(f"{name} has an implausible size: {len(data)}")


def validate_mgl(name: str, data: bytes) -> None:
    text = data.decode("utf-8")
    for needle in (
        "<mistergamedescription>",
        "<rbf>_Console/",
        'same_dir="1"',
        ">CD-",
    ):
        if needle not in text:
            raise RuntimeError(f"{name} is missing {needle!r}")


def main() -> int:
    args = generator_parser(FOLDER, "Generate the MiSTer Disc database").parse_args()
    release = github_latest_release(UPSTREAM)

    plain = matching_release_asset(release, PLAIN_ASSET)
    ra = matching_release_asset(release, RA_ASSET)
    plain_url = release_asset_url(plain)
    ra_url = release_asset_url(ra)
    plain_data = http_get_bytes(plain_url)
    ra_data = http_get_bytes(ra_url)
    validate_main_binary("MiSTer-disc", plain_data)
    validate_main_binary("MiSTer-disc-RA", ra_data)
    if plain_data == ra_data:
        raise RuntimeError("Plain and RA builds are identical: wrong release layout")

    direct_files = [
        DirectFile(path="MiSTer_Disc", url=plain_url, data=plain_data),
        DirectFile(path="MiSTer_Disc_RA", url=ra_url, data=ra_data),
    ]
    for name in MGL_FILES:
        path = Path(__file__).with_name("mgl") / name
        data = path.read_bytes()
        validate_mgl(name, data)
        direct_files.append(
            DirectFile(
                path=mgl_destination(name),
                url=github_raw_url(
                    args.repository,
                    git_file_revision(path),
                    f"{FOLDER}/mgl/{name}",
                ),
                data=data,
            )
        )

    database = build_direct_database(
        folder=FOLDER,
        repository=args.repository,
        timestamp=generation_timestamp(args.timestamp),
        filter_terms=(FOLDER,),
        direct_files=tuple(direct_files),
    )
    write_bundle(database, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
