#!/usr/bin/env python3

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".github"))

from db_helpers import (  # noqa: E402
    DirectFile,
    build_direct_database,
    generation_timestamp,
    generator_parser,
    github_commit_sha,
    github_json,
    github_raw_url,
    http_get_bytes,
    write_bundle,
)


FOLDER = "mms2-gb"
UPSTREAM = "Heber-co-uk/Gameboy_MiSTer_Cart"
RBF_PATTERN = re.compile(r"Gameboy_(\d{8})\.rbf", re.IGNORECASE)
SUPPORT_REVISION = "25c643e3c0a5cf5f654d2ab724272c04ff2b355f"
MGL_URL = github_raw_url(
    "Anime0t4ku/mister-companion",
    SUPPORT_REVISION,
    "assets/Load GB-GBC Cartridge.mgl",
)
CFG_URL = github_raw_url(
    "Anime0t4ku/mister-companion",
    SUPPORT_REVISION,
    "assets/MMS2_GB_Cart.CFG",
)


def latest_rbf(entries: Any) -> dict[str, Any]:
    if not isinstance(entries, list):
        raise RuntimeError("Unexpected MMS2 releases response")

    candidates: list[tuple[str, dict[str, Any]]] = []
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("type") != "file":
            continue
        name = str(entry.get("name") or "")
        match = RBF_PATTERN.fullmatch(name)
        if match:
            candidates.append((match.group(1), entry))

    if not candidates:
        raise RuntimeError(
            "Unable to find Gameboy_YYYYMMDD.rbf in the MMS2 releases directory"
        )

    return max(candidates, key=lambda item: item[0])[1]


def main() -> int:
    args = generator_parser(FOLDER, "Generate the MMS2 GB Core database").parse_args()
    upstream_revision = github_commit_sha(UPSTREAM, "master")
    releases_api = (
        f"https://api.github.com/repos/{UPSTREAM}/contents/releases"
        f"?ref={upstream_revision}"
    )
    entry = latest_rbf(github_json(releases_api))
    filename = str(entry["name"])
    rbf_url = github_raw_url(
        UPSTREAM,
        upstream_revision,
        f"releases/{filename}",
    )
    rbf_data = http_get_bytes(rbf_url)
    mgl_data = http_get_bytes(MGL_URL)
    cfg_data = http_get_bytes(CFG_URL)

    database = build_direct_database(
        folder=FOLDER,
        repository=args.repository,
        timestamp=generation_timestamp(args.timestamp),
        direct_files=(
            DirectFile(
                path=f"MMS2/{filename}",
                url=rbf_url,
                data=rbf_data,
                reboot=True,
                tangles=("mms2_gb_core",),
            ),
            DirectFile(
                path="Load GB-GBC Cartridge.mgl",
                url=MGL_URL,
                data=mgl_data,
            ),
            DirectFile(
                path="config/MMS2_GB_Cart.CFG",
                url=CFG_URL,
                data=cfg_data,
            ),
        ),
    )
    write_bundle(database, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
