#!/usr/bin/env python3

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".github"))

from db_helpers import (  # noqa: E402
    DirectFile,
    build_direct_database,
    generation_timestamp,
    generator_parser,
    git_file_revision,
    github_releases,
    github_raw_url,
    http_get_bytes,
    release_asset_url,
    release_tag,
    write_bundle,
)


FOLDER = "megavgmdrive"
UPSTREAM = "dai-VGM/MegaVGMDrive"
STABLE_TAG = re.compile(r"v(\d+(?:\.\d+)*)")
CORE_ASSET = re.compile(r".*MiSTer.*\.rbf", re.IGNORECASE)
ANY_CORE_ASSET = re.compile(r".*\.rbf", re.IGNORECASE)
MINIMUM_CORE_SIZE = 1_000_000

# Upstream ships beta snapshots as ordinary releases, under descriptive tags
# instead of a version. Snapshots are not published, but one that carries a
# core is a tagging change that has to be reviewed, so it stops the build
# until it is recorded here or superseded by a stable release.
REVIEWED_SNAPSHOTS: tuple[str, ...] = ()


def release_date(release: Mapping[str, Any]) -> str:
    """ISO 8601 publication date, comparable as a string."""
    return str(release.get("published_at") or release.get("created_at") or "")


def stable_version(release: Mapping[str, Any]) -> tuple[int, ...] | None:
    """Version of a `vX.Y` tag, or None for a snapshot tag."""
    match = STABLE_TAG.fullmatch(release_tag(release))
    if match is None:
        return None
    return tuple(int(part) for part in match.group(1).split("."))


def core_assets(release: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Every `.rbf` asset a release ships, whatever it is named."""
    return [
        asset
        for asset in release.get("assets") or []
        if isinstance(asset, dict)
        and ANY_CORE_ASSET.fullmatch(str(asset.get("name") or ""))
        and str(asset.get("browser_download_url") or "").startswith("https://")
    ]


def core_asset(release: Mapping[str, Any]) -> dict[str, Any]:
    """The single MiSTer core shipped by a release.

    A release that ships `.rbf` assets none of which is the MiSTer core, or
    more than one of them, is an upstream layout change rather than something
    to guess at, so it fails instead of installing the wrong bitstream.
    """
    shipped = core_assets(release)
    matches = [
        asset for asset in shipped if CORE_ASSET.fullmatch(str(asset.get("name") or ""))
    ]
    if len(matches) != 1:
        found = ", ".join(sorted(str(asset.get("name")) for asset in shipped)) or "none"
        raise RuntimeError(
            f"{UPSTREAM} release {release_tag(release)} does not ship exactly one "
            f"MiSTer core .rbf asset, found: {found}"
        )
    return matches[0]


def select_core_release(
    releases: Sequence[Mapping[str, Any]],
) -> tuple[Mapping[str, Any], dict[str, Any]]:
    """Pick the highest stable release, and never quietly keep an older core.

    Snapshots are skipped because upstream publishes betas as ordinary
    releases, but every way of ending up on a stale core - the newest stable
    release dropping or renaming its core, or a snapshot carrying one - fails
    the build instead, so the database is either current or visibly broken.
    """
    published = [
        release
        for release in releases
        if not release.get("draft") and not release.get("prerelease")
    ]

    stable: list[tuple[tuple[int, ...], Mapping[str, Any]]] = []
    for release in published:
        version = stable_version(release)
        if version is not None:
            stable.append((version, release))
    if not stable:
        raise RuntimeError(f"No stable {UPSTREAM} release found")

    _, selected = max(stable, key=lambda candidate: candidate[0])
    asset = core_asset(selected)

    unreviewed = sorted(
        release_tag(release)
        for release in published
        if stable_version(release) is None
        and release_date(release) > release_date(selected)
        and core_assets(release)
        and release_tag(release) not in REVIEWED_SNAPSHOTS
    )
    if unreviewed:
        raise RuntimeError(
            f"{UPSTREAM} snapshot releases newer than {release_tag(selected)} ship a "
            f"core .rbf: {', '.join(unreviewed)}. Review them, then either follow the "
            "new stable release or record them in REVIEWED_SNAPSHOTS."
        )

    return selected, asset


def main() -> int:
    args = generator_parser(FOLDER, "Generate the MegaVGMDrive database").parse_args()
    release, asset = select_core_release(github_releases(UPSTREAM))
    rbf_url = release_asset_url(asset)
    rbf_data = http_get_bytes(rbf_url)
    if len(rbf_data) < MINIMUM_CORE_SIZE:
        raise RuntimeError(
            f"{asset.get('name')} is too small ({len(rbf_data)} bytes) to be "
            "a MegaVGMDrive core"
        )
    print(f"MegaVGMDrive core from release {release_tag(release)}")

    mgl_path = Path(__file__).with_name("MegaVGMDrive.mgl")
    mgl_url = github_raw_url(
        args.repository,
        git_file_revision(mgl_path),
        "megavgmdrive/MegaVGMDrive.mgl",
    )
    mgl_data = mgl_path.read_bytes()

    database = build_direct_database(
        folder=FOLDER,
        repository=args.repository,
        timestamp=generation_timestamp(args.timestamp),
        filter_terms=(FOLDER, "console", "megadrive"),
        tag_aliases=((FOLDER, "vgm-md-mister"),),
        direct_files=(
            DirectFile(
                path="_Custom Cores/Cores/MegaVGMdrive_MiSTer.rbf",
                url=rbf_url,
                data=rbf_data,
                reboot=True,
            ),
            DirectFile(
                path="_Custom Cores/MegaVGMDrive.mgl",
                url=mgl_url,
                data=mgl_data,
            ),
        ),
        extra_folders=("games/MegaVGMDrive",),
    )
    write_bundle(database, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
