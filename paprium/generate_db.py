#!/usr/bin/env python3

from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ElementTree
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".github"))

from db_helpers import (  # noqa: E402
    MISTER_ROOT,
    ArchiveMember,
    DirectFile,
    SelectiveArchive,
    build_multi_selective_archive_database,
    generation_timestamp,
    generator_parser,
    git_file_revision,
    github_latest_release,
    github_raw_url,
    http_get_bytes,
    read_archive_members,
    release_asset_url,
    release_tag,
    write_bundle,
)


FOLDER = "paprium"
ARCHIVE_ID = "release"

# Reviewed upstream move (pull request #22, accepted by the repository owner on
# 2026-11-22): this entry tracked MisterPezz82/Paprium_MegaDrive_MiSTer and
# installed the newest MegaDrive_Paprium_YYYYMMDD.rbf asset of its latest
# release, up to V.08's MegaDrive_Paprium_20261013.rbf. On 2026-11-11 that
# repository published the release `final` -- "Retired: Paprium for MiSTer is
# now thekoalakoa's Paprium_MiSTer" -- carrying no assets at all and marked
# neither draft nor prerelease, and archived itself read-only. The generator
# failed closed there, as it should have: an archived repository can never
# publish another core, so skipping a release that carries nothing installable
# would not have kept this database current, it would have frozen it on a dead
# upstream in silence. The successor was named only in that notice and in the
# repository description, which are prose, so following it was a human's
# decision to make and this constant is that decision.
#
# What the review had in front of it, from structured metadata only:
# thekoalakoa/Paprium_MiSTer was created 2026-09-08, is not a fork, has no
# parent, and GitHub records no lineage to the retired repository -- its owner
# (id 118791477) is a different account from MisterPezz82 (id 295477100), which
# authored every release there, `final` included. The only tie is that the V.07
# and V.08 release names credit @thekoalakoa for the work, prose again. So the
# identification of the successor is a reviewed human judgement, not something
# this selection rule derived, and the same is true of the payload layout
# below: it was read from the release ZIP, never from upstream's notes.
UPSTREAM = "thekoalakoa/Paprium_MiSTer"

# Every release of the new project ships one versioned bundle under this name;
# 0.2.6 also attached an unrelated cpu-mate-brain_0.2.6.zip, so the bundle is
# selected by name and an ambiguous release fails instead of guessing. The
# retired project's dated-RBF ASSET_PATTERN is gone with it: the new core is
# undated, which also retires the paprium_megadrive_core tangle chain that kept
# successive dated files from deleting a working core.
ASSET_PATTERN = re.compile(r"Paprium_MiSTer_(\d+(?:\.\d+)*)\.zip")

# The reviewed layout of that bundle, as published in v0.3.0 and v0.3.1: the
# core, upstream's own launcher for it, and the Little-Man firmware blob the
# core loads before a game. Anything else in the ZIP, or any of these missing,
# is an upstream layout change that fails the generator for review.
UPSTREAM_CORE = "_Console/Paprium.rbf"
UPSTREAM_LAUNCHER = "_Console/Paprium.mgl"
UPSTREAM_FIRMWARE = "games/Paprium/little_man_firmware.bin"
UPSTREAM_CORE_RBF = "_Console/Paprium"
FIRMWARE_LOAD_PATH = f"{MISTER_ROOT}{UPSTREAM_FIRMWARE}"
FIRMWARE_LOAD_INDEX = "4"
EXPECTED = frozenset({UPSTREAM_CORE, UPSTREAM_LAUNCHER, UPSTREAM_FIRMWARE})

MINIMUM_CORE_SIZE = 1_000_000
MAXIMUM_CORE_SIZE = 16_000_000
MAXIMUM_FIRMWARE_SIZE = 4_000_000

# Reviewed naming decision (same review): this entry keeps installing the core
# into its own "_Custom Cores/Cores" folder, and keeps PapriumMD.mgl and the
# games/PapriumMD folder it has always published, so the menu entry, the ROM
# folder and the saves and core settings existing users already have stay
# exactly where they are. Only the core the launcher points at follows
# upstream's rename, which is the answer brickboy-dmg's review gave when its
# core was renamed. Upstream's own launcher is validated below but deliberately
# not installed: it would add a second menu entry that loads a ROM from
# games/Paprium/Paprium/Paprium.md, a path no user of this database has.
# Following upstream's Paprium naming instead would move those folders and
# orphan the saves, which is why it is not done here.
CORE_PATH = "_Custom Cores/Cores/Paprium.rbf"
GAMES_FOLDER = "games/PapriumMD"
# The firmware goes into this entry's own games folder rather than upstream's,
# because the shipped launcher's setname is what decides where the core's file
# browser opens, and that is where the firmware has to be for the core's own
# "load firmware" entry to find it next to the user's ROM.
FIRMWARE_PATH = f"{GAMES_FOLDER}/little_man_firmware.bin"
MGL_NAME = "PapriumMD.mgl"
MGL_PATH = f"_Custom Cores/{MGL_NAME}"
MGL_SETNAME = "PapriumMD"
MGL_RBF = "_Custom Cores/Cores/Paprium"


def release_asset(release: Mapping[str, Any]) -> tuple[dict[str, Any], str]:
    """Select the one versioned bundle and tie it to its own release tag."""
    tag = release_tag(release)
    matching = [
        asset
        for asset in release.get("assets") or []
        if isinstance(asset, dict)
        and ASSET_PATTERN.fullmatch(str(asset.get("name") or ""))
        and str(asset.get("browser_download_url") or "").startswith("https://")
    ]
    if len(matching) != 1:
        found = ", ".join(
            sorted(str(asset.get("name")) for asset in release.get("assets") or [])
        )
        raise RuntimeError(
            f"Paprium release {tag} must publish exactly one "
            f"Paprium_MiSTer_<version>.zip, found: {found or 'no assets'}"
        )

    asset = matching[0]
    match = ASSET_PATTERN.fullmatch(str(asset.get("name")))
    assert match is not None
    url = release_asset_url(asset)
    expected_prefix = f"https://github.com/{UPSTREAM}/releases/download/{tag}/"
    if not url.startswith(expected_prefix):
        raise RuntimeError(
            f"Paprium bundle URL does not belong to release {tag}: {url}"
        )
    return asset, match.group(1)


def validate_upstream_launcher(member: ArchiveMember) -> None:
    """Read upstream's own launcher for the two facts this entry relies on.

    It is the structured statement of which member of the ZIP is the core and
    that the firmware blob is one of that core's load entries rather than a
    stray file. Upstream's notes and its retirement notice are prose and are
    not read anywhere.
    """
    try:
        root = ElementTree.fromstring(member.data.decode("utf-8"))
    except (UnicodeDecodeError, ElementTree.ParseError) as exc:
        raise RuntimeError(f"{member.path} is not a readable MGL") from exc
    if root.tag != "mistergamedescription":
        raise RuntimeError(f"{member.path} is not a MiSTer launcher")

    launched = [(element.text or "").strip() for element in root.findall("rbf")]
    if launched != [UPSTREAM_CORE_RBF]:
        raise RuntimeError(
            f"{member.path} must launch {UPSTREAM_CORE_RBF}, found: "
            + (", ".join(launched) or "no <rbf>")
        )

    indexes = [
        str(element.get("index"))
        for element in root.findall("file")
        if (element.get("path") or "") == FIRMWARE_LOAD_PATH
    ]
    if indexes != [FIRMWARE_LOAD_INDEX]:
        raise RuntimeError(
            f"{member.path} must load {UPSTREAM_FIRMWARE} through load entry "
            f"{FIRMWARE_LOAD_INDEX}, found: "
            + (", ".join(indexes) or "no entry for it")
        )


def selected_files(
    members: Sequence[ArchiveMember],
) -> tuple[tuple[str, ArchiveMember], ...]:
    """Validate the release layout and install only this entry's payload."""
    by_path = {member.path: member for member in members}

    unexpected = sorted(set(by_path).difference(EXPECTED))
    if unexpected:
        raise RuntimeError(
            "The Paprium ZIP ships files this entry does not expect: "
            + ", ".join(unexpected)
        )
    missing = sorted(EXPECTED.difference(by_path))
    if missing:
        raise RuntimeError(
            "The Paprium ZIP is missing required files: " + ", ".join(missing)
        )

    core = by_path[UPSTREAM_CORE]
    if not MINIMUM_CORE_SIZE <= len(core.data) <= MAXIMUM_CORE_SIZE:
        raise RuntimeError(
            f"{UPSTREAM_CORE} has an implausible RBF size: {len(core.data)}"
        )
    firmware = by_path[UPSTREAM_FIRMWARE]
    if not 0 < len(firmware.data) <= MAXIMUM_FIRMWARE_SIZE:
        raise RuntimeError(
            f"{UPSTREAM_FIRMWARE} has an implausible size: {len(firmware.data)}"
        )
    validate_upstream_launcher(by_path[UPSTREAM_LAUNCHER])

    return ((CORE_PATH, core), (FIRMWARE_PATH, firmware))


def validate_mgl(mgl_data: bytes) -> None:
    """Keep the shipped launcher and the installed core from drifting apart."""
    text = mgl_data.decode("utf-8")
    expected_rbf = f"<rbf>{MGL_RBF}</rbf>"
    if expected_rbf not in text:
        raise RuntimeError(f"{MGL_NAME} must launch {CORE_PATH} through {expected_rbf}")
    if f"<setname>{MGL_SETNAME}</setname>" not in text:
        raise RuntimeError(f"{MGL_NAME} must keep its reviewed {MGL_SETNAME} setname")


def main() -> int:
    args = generator_parser(FOLDER, "Generate the Paprium MegaDrive database").parse_args()
    release = github_latest_release(UPSTREAM)
    asset, version = release_asset(release)
    archive_url = release_asset_url(asset)
    archive_data = http_get_bytes(archive_url)
    selected = selected_files(read_archive_members(archive_data))

    mgl_path = Path(__file__).with_name(MGL_NAME)
    mgl_data = mgl_path.read_bytes()
    validate_mgl(mgl_data)
    mgl_url = github_raw_url(
        args.repository,
        git_file_revision(mgl_path),
        f"{FOLDER}/{MGL_NAME}",
    )

    database = build_multi_selective_archive_database(
        folder=FOLDER,
        repository=args.repository,
        timestamp=generation_timestamp(args.timestamp),
        archives=(
            SelectiveArchive(
                archive_id=ARCHIVE_ID,
                url=archive_url,
                data=archive_data,
                selected_files=selected,
                description=f"Installing Paprium for MiSTer {version}",
                reboot_paths=(CORE_PATH,),
            ),
        ),
        filter_terms=(FOLDER, "console", "megadrive"),
        tag_aliases=((FOLDER, "papriummd", "megadrive-paprium"),),
        direct_files=(
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
