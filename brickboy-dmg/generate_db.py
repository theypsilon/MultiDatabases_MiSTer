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
    git_file_revision,
    github_latest_release,
    github_raw_url,
    http_get_bytes,
    release_asset_url,
    write_bundle,
)


FOLDER = "brickboy-dmg"

# Reviewed upstream move (pull request #12, 2026-10-03): this entry used to
# follow kandowontu/brickboy-dmg-fpgacore and installed its v0.2.0
# BrickBoy_DMG.rbf asset. That repository and the whole kandowontu account
# answer 404 with no redirect, which is a removal and not a rename, so the
# payload URL the published database pointed at died with them and this
# generator failed closed, as it should have. Review confirmed the author came
# back as kandowontu2 and that kandowontu2/BrickBoy_MiSTer is the same project
# continued: a non-fork repository, GPL-3.0 like the old one, described as the
# standalone BrickBoy DMG core for MiSTer, and the only BrickBoy repository in
# that account. GitHub records no lineage between the two and release 0.5.1
# ships different bytes than v0.2.0 did, so the identification is a reviewed
# human decision rather than something the selection rule derived. If this
# repository disappears in turn, that is another upstream review and not an
# edit to this constant.
UPSTREAM = "kandowontu2/BrickBoy_MiSTer"

# Do NOT repoint UPSTREAM at kathoc/brickboy-dmg-fpgacore. The removed
# repository was forked from it, it is still live, it carries the identical
# name and even reuses the v0.2.0 tag, but it is an Analogue Pocket openFPGA
# project that ships brickboy-dmg-pocket.zip and no MiSTer core.
RBF_PATTERN = re.compile(r"BrickBoy\.rbf", re.IGNORECASE)

# Upstream renamed the core binary BrickBoy_DMG.rbf -> BrickBoy.rbf, so the
# installed core follows it. It stays in this entry's own "_Custom Cores/Cores"
# folder, where it has always been installed and where the MGL below looks for
# it; upstream's own ZIP packs the same bytes under "_Other" and is not used.
CORE_FOLDER = "_Custom Cores/Cores"
CORE_NAME = "BrickBoy"
CORE_PATH = f"{CORE_FOLDER}/{CORE_NAME}.rbf"

# Reviewed naming decision (same review): the MGL keeps its BrickBoy_DMG
# filename and setname so that the menu entry and the save/config directory
# existing users already have stay exactly where they are, and only its <rbf>
# follows the renamed core. Renaming the MGL to match upstream would orphan
# those saves, which is why it is deliberately not done here.
MGL_NAME = "BrickBoy_DMG.mgl"
MGL_PATH = f"Custom Cores/{MGL_NAME}"
MGL_SETNAME = "BrickBoy_DMG"


def select_rbf_asset(release: dict[str, Any]) -> dict[str, Any]:
    matches = []
    for asset in release.get("assets") or []:
        if not isinstance(asset, dict):
            continue
        name = str(asset.get("name") or "")
        url = str(asset.get("browser_download_url") or "")
        if RBF_PATTERN.fullmatch(name) and url.startswith("https://"):
            matches.append(asset)

    if len(matches) != 1:
        tag = release.get("tag_name") or release.get("name") or "unknown"
        raise RuntimeError(
            f"BrickBoy release {tag} must contain exactly one "
            f"{CORE_NAME}.rbf asset; found {len(matches)}"
        )
    return matches[0]


def validate_mgl(mgl_data: bytes) -> None:
    """Keep the shipped MGL and the installed core from drifting apart."""
    text = mgl_data.decode("utf-8")
    expected_rbf = f"<rbf>{CORE_FOLDER}/{CORE_NAME}</rbf>"
    if expected_rbf not in text:
        raise RuntimeError(f"{MGL_NAME} must launch {CORE_PATH} through {expected_rbf}")
    if f'<setname same_dir="1">{MGL_SETNAME}</setname>' not in text:
        raise RuntimeError(
            f"{MGL_NAME} must keep its reviewed {MGL_SETNAME} setname"
        )


def main() -> int:
    args = generator_parser(
        FOLDER, "Generate the BrickBoy DMG database"
    ).parse_args()
    release = github_latest_release(UPSTREAM)
    asset = select_rbf_asset(release)
    rbf_url = release_asset_url(asset)
    rbf_data = http_get_bytes(rbf_url)

    mgl_path = Path(__file__).with_name(MGL_NAME)
    mgl_url = github_raw_url(
        args.repository,
        git_file_revision(mgl_path),
        f"{FOLDER}/{MGL_NAME}",
    )
    mgl_data = mgl_path.read_bytes()
    validate_mgl(mgl_data)

    database = build_direct_database(
        folder=FOLDER,
        repository=args.repository,
        timestamp=generation_timestamp(args.timestamp),
        filter_terms=(FOLDER, "console", "gb", "gbc"),
        tag_aliases=((FOLDER, "brickboy"),),
        direct_files=(
            DirectFile(
                path=CORE_PATH,
                url=rbf_url,
                data=rbf_data,
            ),
            DirectFile(
                path=MGL_PATH,
                url=mgl_url,
                data=mgl_data,
            ),
        ),
    )
    write_bundle(database, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
