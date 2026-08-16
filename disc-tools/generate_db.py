#!/usr/bin/env python3

from __future__ import annotations

import sys
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".github"))

from db_helpers import (  # noqa: E402
    ArchiveMember,
    SelectiveArchive,
    build_multi_selective_archive_database,
    compatible_release_zip,
    expand_shell_variables,
    generation_timestamp,
    generator_parser,
    github_latest_release,
    release_tag,
    shell_variable,
    validate_arm_binary,
    write_bundle,
)


FOLDER = "disc-tools"
NAME = "Disc Tools"
UPSTREAM = "Anime0t4ku/MiSTer-Disc-Tools"
ARCHIVE_ID = "release"
LAUNCHER = "Scripts/disctools.sh"
APP_FOLDER = "Scripts/.config/disctools"
MAIN_BINARY = f"{APP_FOLDER}/disctools"
HELPERS = (
    f"{APP_FOLDER}/bin/cdrdao",
    f"{APP_FOLDER}/bin/cue2toc",
    f"{APP_FOLDER}/bin/toc2cue",
    f"{APP_FOLDER}/bin/chdman",
    f"{APP_FOLDER}/bin/xorriso",
)
# These folders are application-owned working state. Empty directories in the
# release ZIP are harmless, but files inside them must never be installed by a
# database update because that could overwrite logs or in-progress temp data.
USER_OWNED_PREFIXES = (
    f"{APP_FOLDER}/logs/",
    f"{APP_FOLDER}/temp/",
)


def _is_arm_elf(member: ArchiveMember) -> bool:
    data = member.data
    return (
        data.startswith(b"\x7fELF")
        and len(data) >= 20
        and data[4:6] == b"\x01\x01"
        and data[18:20] == b"\x28\x00"
    )


def selected_files(
    members: Sequence[ArchiveMember],
) -> tuple[tuple[str, ArchiveMember], ...]:
    """Validate and install the complete Disc Tools release ZIP payload."""
    paths = {member.path: member for member in members}

    outside = sorted(
        member.path
        for member in members
        if member.path != LAUNCHER and not member.path.startswith(f"{APP_FOLDER}/")
    )
    if outside:
        raise RuntimeError(
            f"{NAME} ZIP installs outside {LAUNCHER} and {APP_FOLDER}/: "
            + ", ".join(outside)
        )

    packaged_runtime = sorted(
        member.path
        for member in members
        if member.path.startswith(USER_OWNED_PREFIXES)
    )
    if packaged_runtime:
        raise RuntimeError(
            f"{NAME} ZIP ships runtime log/temp files that belong to the app: "
            + ", ".join(packaged_runtime)
        )

    required = (LAUNCHER, MAIN_BINARY, *HELPERS)
    missing = sorted(set(required).difference(paths))
    if missing:
        raise RuntimeError(
            f"{NAME} ZIP is missing required files: " + ", ".join(missing)
        )

    launcher = paths[LAUNCHER]
    if not launcher.data.startswith(b"#!"):
        raise RuntimeError(f"{NAME} launcher is not a shell script: {LAUNCHER}")

    launcher_text = launcher.data.decode("utf-8", "replace")
    expected_binary = f"/media/fat/{MAIN_BINARY}"
    if expected_binary not in expand_shell_variables(launcher_text):
        raise RuntimeError(
            f"{NAME} launcher {LAUNCHER} does not run {expected_binary}"
        )

    validate_arm_binary(MAIN_BINARY, paths[MAIN_BINARY].data)
    for helper in HELPERS:
        if not _is_arm_elf(paths[helper]):
            raise RuntimeError(
                f"{NAME} helper {helper} is not a 32-bit little-endian ARM ELF"
            )

    version = shell_variable(launcher_text, "VERSION")
    print(f"{NAME} launcher declares version {version}", flush=True)

    return tuple(
        (member.path, member)
        for member in sorted(members, key=lambda member: member.path)
    )


def main() -> int:
    args = generator_parser(FOLDER, f"Generate the {NAME} database").parse_args()
    release = github_latest_release(UPSTREAM)
    tag = release_tag(release)
    url, data, files = compatible_release_zip(
        release,
        accept=selected_files,
        context=f"{UPSTREAM} release {tag}",
    )

    database = build_multi_selective_archive_database(
        folder=FOLDER,
        repository=args.repository,
        timestamp=generation_timestamp(args.timestamp),
        archives=(
            SelectiveArchive(
                archive_id=ARCHIVE_ID,
                url=url,
                data=data,
                selected_files=files,
                description=f"Installing {NAME} {tag}",
            ),
        ),
        filter_terms=(FOLDER, "utility"),
        tag_aliases=((FOLDER, "disctools"),),
    )
    write_bundle(database, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
