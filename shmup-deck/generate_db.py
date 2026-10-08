#!/usr/bin/env python3

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".github"))

from db_helpers import (  # noqa: E402
    MISTER_ROOT,
    SHELL_ASSIGNMENT,
    ArchiveMember,
    DirectFile,
    SelectiveArchive,
    build_multi_selective_archive_database,
    expand_shell_variables,
    generation_timestamp,
    generator_parser,
    github_latest_release,
    http_get_bytes,
    matching_release_asset,
    read_archive_members,
    release_asset_url,
    release_tag,
    write_bundle,
)


FOLDER = "shmup-deck"
NAME = "Shmup Deck"

# Upstream changed hands and this constant deliberately has not followed it
# yet (proposed on pull request #16, still awaiting review on 2026-10-08).
# The repository this entry has always tracked, searchsolved/shmup-deck,
# was transferred to a newly created organization, shmupfan/shmup-deck, on
# 2026-10-02, and from release v1.12.5 the launcher sets
# REPO="shmupfan/shmup-deck" to match. That trips both the shared repository
# identity check in discovery and validate_launcher below, so the generator
# fails closed and the database stays parked on v1.12.4. The owner is all that
# is left to decide: with UPSTREAM repointed, v1.12.12 passes every other
# check and publishes the same twenty paths as the parked v1.12.4.
#
# Repointing this value is a human decision, not one this generator may make:
# REPO is the repository the launcher refetches and overwrites itself from on
# every run, so it decides whose code the Scripts menu executes and whose code
# user-startup.sh runs at every boot. GitHub metadata shows continuity -- the
# same repository id 1370342380 and creation date, and every commit and
# release through v1.12.12 still authored by searchsolved -- but an
# organization can grant push access to accounts a personal account cannot,
# and shmupfan publishes no member list, so who may ship that launcher is no
# longer publicly auditable. Accepting the move is a review of the project's
# distribution identity; until it happens, a loud failure is the correct
# outcome and this entry keeps serving the last reviewed release.
#
# A transfer used to leave no trace in discovery: the API 301-redirects the
# old path to the same repository, so github_latest_release below followed it
# in silence and the bundle published on 2026-10-02 already carries shmupfan
# payload URLs for v1.12.4, four days before this launcher check was the only
# thing that noticed. Discovery now refuses a repository that answers under
# another name, so the move fails here for what it is.
#
# Failing closed keeps the new owner out of this database, not off the MiSTer.
# The v1.12.4 launcher the parked bundle still installs reads its own REPO to
# fetch releases/latest, which GitHub redirects to shmupfan; it then writes
# the newest shmup_deck.sh beside itself, re-execs it, and unpacks the newest
# ZIP over the app folder. Anyone who has opened the Scripts entry since
# v1.12.5 is therefore already running shmupfan's code, and a downloader run
# only puts v1.12.4 back until the launcher runs again. So the gate buys a
# review of what this repository publishes; it does not buy users time, which
# is an argument for deciding the owner rather than leaving it parked.
UPSTREAM = "searchsolved/shmup-deck"
ARCHIVE_ID = "release"

# Every release ships exactly these two assets, under these names: the
# launcher itself looks the ZIP up by this exact name, so the names are part of
# upstream's interface rather than a guess.
LAUNCHER_ASSET = re.compile(r"shmup_deck\.sh")
ARCHIVE_ASSET = re.compile(r"shmup_deck\.zip")
RELEASE_TAG = re.compile(r"v(\d+\.\d+\.\d+)")

LAUNCHER = "Scripts/shmup_deck.sh"
APP_FOLDER = "Scripts/.config/shmup_deck"
SERVICE = "shmup_deck.py"
APP_DATA = "app/"
# The ZIP wraps everything in one folder, which the launcher strips when it
# installs the same ZIP by hand.
ARCHIVE_PREFIX = "shmup_deck/"
REQUIRED = (
    SERVICE,
    "app/index.html",
    "app/games.json",
    "app/art.json",
    "app/cores.json",
)
# What Shmup Deck writes beside itself: the launcher records the installed
# release in VERSION, and the service keeps the downloaded flyer art, the MRA
# index, the play statistics and the shared favourites there. A release that
# started packing any of them would overwrite user data on every downloader
# run.
USER_OWNED = (
    "VERSION",
    "art/",
    "favourites.json",
    "mra_index.json",
    "mra_index_seen.json",
    "plays.json",
)
SERVICE_VERSION = re.compile(r'^VERSION = "([^"\n]*)"$', re.MULTILINE)

# Reviewed boot registration. The launcher appends one line to the update-safe
# user-startup.sh, ending in this marker, and its `uninstall` argument deletes
# every line carrying the marker again. The entry README documents that exact
# procedure, so a launcher that moved the boot entry or changed the marker
# has to be reviewed instead of published.
STARTUP = "/media/fat/linux/user-startup.sh"
MARK = "# shmup_deck"
SERVICE_PATH = f"{MISTER_ROOT}{APP_FOLDER}/{SERVICE}"
BOOT_ENTRY = re.compile(rf">>\s*\"?{re.escape(STARTUP)}\"?")
BOOT_REMOVAL = re.compile(
    rf"sed -i \"?/{re.escape(MARK)}/d\"? \"?{re.escape(STARTUP)}\"?"
)


def release_version(release: dict) -> str:
    """The `X.Y.Z` of a `vX.Y.Z` release tag."""
    tag = release_tag(release)
    match = RELEASE_TAG.fullmatch(tag)
    if match is None:
        raise RuntimeError(f"{NAME} release tag is not vX.Y.Z: {tag}")
    return match.group(1)


def service_version(data: bytes) -> str:
    """The version the service reports, from its VERSION constant."""
    match = SERVICE_VERSION.search(data.decode("utf-8", "replace"))
    if match is None:
        raise RuntimeError(f"{NAME} {SERVICE} declares no VERSION constant")
    return match.group(1)


def app_path(member: ArchiveMember) -> str:
    """Path of a ZIP member inside the app folder, the way the launcher
    installs it."""
    path = member.path
    if path.startswith(ARCHIVE_PREFIX):
        path = path[len(ARCHIVE_PREFIX) :]
    if not path:
        raise RuntimeError(f"{NAME} ZIP has an empty path: {member.archive_path}")
    return path


def is_user_owned(path: str) -> bool:
    return any(
        path.startswith(owned) if owned.endswith("/") else path == owned
        for owned in USER_OWNED
    )


def selected_files(
    members: Sequence[ArchiveMember], *, version: str
) -> tuple[tuple[str, ArchiveMember], ...]:
    """Validate the release ZIP layout and map it under the app folder."""
    paths = {app_path(member): member for member in members}
    if len(paths) != len(members):
        raise RuntimeError(f"{NAME} ZIP maps two members to the same file")

    packaged = sorted(path for path in paths if is_user_owned(path))
    if packaged:
        raise RuntimeError(
            f"{NAME} ZIP ships files that belong to the user, which an update "
            "would overwrite: " + ", ".join(packaged)
        )

    outside = sorted(
        path for path in paths if path != SERVICE and not path.startswith(APP_DATA)
    )
    if outside:
        raise RuntimeError(
            f"{NAME} ZIP ships files outside {SERVICE} and {APP_DATA}: "
            + ", ".join(outside)
        )

    missing = sorted(set(REQUIRED).difference(paths))
    if missing:
        raise RuntimeError(
            f"{NAME} ZIP is missing required files: " + ", ".join(missing)
        )

    binaries = sorted(
        path for path, member in paths.items() if member.data.startswith(b"\x7fELF")
    )
    if binaries:
        raise RuntimeError(
            f"{NAME} is a pure Python service, but its ZIP ships binaries: "
            + ", ".join(binaries)
        )

    declared = service_version(paths[SERVICE].data)
    if declared != version:
        raise RuntimeError(
            f"{NAME} {SERVICE} declares version {declared}, "
            f"but the release is tagged v{version}"
        )

    return tuple(
        (f"{APP_FOLDER}/{path}", paths[path]) for path in sorted(paths)
    )


def shell_assignments(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for match in SHELL_ASSIGNMENT.finditer(text):
        values[match.group(1)] = next(
            group for group in match.groups()[1:] if group is not None
        )
    return values


def validate_launcher(data: bytes) -> None:
    """Require the launcher to run, register and unregister the service the
    reviewed way: from the app folder this database installs, through one
    marked line in user-startup.sh."""
    if not data.startswith(b"#!"):
        raise RuntimeError(f"{NAME} launcher is not a script")
    text = data.decode("utf-8", "replace")
    values = shell_assignments(text)

    expected = {
        "REPO": UPSTREAM,
        "HOME_DIR": f"{MISTER_ROOT}{APP_FOLDER}",
        "STARTUP": STARTUP,
        "MARK": MARK,
    }
    for name, value in expected.items():
        if values.get(name) != value:
            raise RuntimeError(
                f"{NAME} launcher must set {name}={value!r}, "
                f"found {values.get(name)!r}"
            )

    expanded = expand_shell_variables(text)
    if SERVICE_PATH not in expanded:
        raise RuntimeError(f"{NAME} launcher does not run {SERVICE_PATH}")
    if BOOT_ENTRY.search(expanded) is None:
        raise RuntimeError(f"{NAME} launcher does not register itself in {STARTUP}")
    if '"uninstall"' not in text or BOOT_REMOVAL.search(expanded) is None:
        raise RuntimeError(
            f"{NAME} launcher does not remove its {MARK!r} line from {STARTUP} "
            "on uninstall"
        )


def main() -> int:
    args = generator_parser(FOLDER, f"Generate the {NAME} database").parse_args()
    release = github_latest_release(UPSTREAM)
    version = release_version(release)

    launcher_url = release_asset_url(matching_release_asset(release, LAUNCHER_ASSET))
    launcher_data = http_get_bytes(launcher_url)
    validate_launcher(launcher_data)

    archive_url = release_asset_url(matching_release_asset(release, ARCHIVE_ASSET))
    archive_data = http_get_bytes(archive_url)
    files = selected_files(read_archive_members(archive_data), version=version)
    print(f"{NAME} release v{version}: {len(files)} app files", flush=True)

    database = build_multi_selective_archive_database(
        folder=FOLDER,
        repository=args.repository,
        timestamp=generation_timestamp(args.timestamp),
        archives=(
            SelectiveArchive(
                archive_id=ARCHIVE_ID,
                url=archive_url,
                data=archive_data,
                selected_files=files,
                description=f"Installing {NAME} v{version}",
                # The service is started at boot from user-startup.sh, so a
                # new version only takes over on the next boot.
                reboot_paths=(f"{APP_FOLDER}/{SERVICE}",),
            ),
        ),
        direct_files=(
            DirectFile(path=LAUNCHER, url=launcher_url, data=launcher_data),
        ),
        filter_terms=(FOLDER, "utility"),
    )
    write_bundle(database, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
