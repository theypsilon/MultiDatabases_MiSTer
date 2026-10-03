#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".github"))

from db_helpers import (  # noqa: E402
    ArchiveMember,
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
    validate_arm_binary,
    write_bundle,
)


FOLDER = "donut-dodo"
UPSTREAM = "gmcnaught/donut.dodo-mister"
ARCHIVE_ID = "release"
NAME = "Donut Dodo MiSTer"
# Upstream tags are build dates, with a letter for a same-day rebuild
# (20260926b); the release ZIP carries the same version.
VERSION_PATTERN = re.compile(r"\d{8}[a-z]?")
ASSET_PATTERN = re.compile(r"DonutDodo-MiSTer-(\d{8}[a-z]?)\.zip")
CORE_PATTERN = re.compile(r"_Other/DonutDodo_\d{8}\.rbf")
MODULE_PATTERN = re.compile(r"games/DonutDodo/platform/mem_wc/mem_wc-[^/]+\.ko")
SHARED_OBJECT_PATTERN = re.compile(r".+\.so(?:\.\d+)*")
GLIBC_PATTERN = re.compile(rb"GLIBC_(\d+)\.(\d+)")
INSTALL_ROOTS = ("Scripts/", "_Other/", "games/DonutDodo/")

GAMEDIR = "games/DonutDodo"
ENGINE = f"{GAMEDIR}/frt_3.5.2"
ENGINE_LAUNCHER = f"{GAMEDIR}/launch.sh"
PLATFORM_LAUNCHER = f"{GAMEDIR}/platform/launch_lib.sh"
# Upstream launches through the shared mister-hybrid platform: MiSTer.ini
# [DonutDodo] main= points at this hook, which starts ENGINE_LAUNCHER from the
# hybrid.d/ registry entry next to it. Scripts/DonutDodo_CoresMenu.sh writes
# that main= line; Scripts/DonutDodo.sh starts the game without it.
WRAPPER = f"{GAMEDIR}/platform/MiSTer_hybrid"
REGISTRY = f"{GAMEDIR}/platform/hybrid.d/DonutDodo.conf"
CORE_MGL = "_Other/DonutDodo.mgl"
# Linked into every platform v0.4+ hook build; a stock Main_MiSTer or a v0.3
# hook (which reads /media/fat/linux/hybrid.d) lacks it.
WRAPPER_MARKER = b"MiSTer_hybrid registry: <binary dir>/hybrid.d"
SCRIPTS = ("Scripts/DonutDodo.sh", "Scripts/DonutDodo_CoresMenu.sh")

REQUIRED = frozenset(
    {
        *SCRIPTS,
        CORE_MGL,
        ENGINE,
        ENGINE_LAUNCHER,
        PLATFORM_LAUNCHER,
        WRAPPER,
        REGISTRY,
        f"{GAMEDIR}/libs/libSDL2-2.0.so.0",
        f"{GAMEDIR}/libs/libmisterglue.so",
        f"{GAMEDIR}/platform/mem_wc_load.sh",
    }
)

# The game is commercial and user-supplied: the release must never ship the
# pack or anything that would overwrite saves, settings or the hook's opt-out.
USER_OWNED_FILES = frozenset(
    {
        f"{GAMEDIR}/gamedata/DonutDodo.pck",
        # The hook's registry entry names this as its opt-out switch.
        f"{GAMEDIR}/NOENGINE",
    }
)
USER_OWNED_FOLDERS = (f"{GAMEDIR}/conf/",)

# Bound the download before reading ZIP members; the 20260928 release is
# ~12 MB compressed and ~25 MB expanded.
MIN_ARCHIVE_SIZE = 1_000_000
MAX_ARCHIVE_SIZE = 100_000_000


def release_asset(release: Mapping[str, Any]) -> tuple[dict[str, Any], str]:
    """Select the one dated bundle and tie its version to the release tag."""
    tag = str(release.get("tag_name") or "")
    if not VERSION_PATTERN.fullmatch(tag):
        raise RuntimeError(f"{NAME} release has an invalid tag: {tag}")

    matching = [
        asset
        for asset in release.get("assets") or []
        if isinstance(asset, dict)
        and ASSET_PATTERN.fullmatch(str(asset.get("name") or ""))
    ]
    if len(matching) != 1:
        raise RuntimeError(
            f"{NAME} release {tag} must publish exactly one "
            f"DonutDodo-MiSTer-<date>.zip, found {len(matching)}"
        )

    asset = matching_release_asset(dict(release), ASSET_PATTERN)
    version = ASSET_PATTERN.fullmatch(str(asset["name"])).group(1)
    if version != tag:
        raise RuntimeError(
            f"{NAME} release tag and bundle version differ: {tag} vs {version}"
        )
    url = release_asset_url(asset)
    if not url.startswith(
        f"https://github.com/{UPSTREAM}/releases/download/{tag}/"
    ):
        raise RuntimeError(
            f"{NAME} bundle URL does not belong to its release tag: {url}"
        )
    return asset, tag


def validate_archive_download(
    asset: Mapping[str, Any], archive_data: bytes
) -> None:
    size = asset.get("size")
    if not isinstance(size, int) or isinstance(size, bool):
        raise RuntimeError(f"{NAME} release bundle has no integer size")
    if not MIN_ARCHIVE_SIZE <= size <= MAX_ARCHIVE_SIZE:
        raise RuntimeError(f"{NAME} release bundle has an implausible size: {size}")
    if len(archive_data) != size:
        raise RuntimeError(
            f"{NAME} release bundle size differs from GitHub metadata: "
            f"expected {size}, downloaded {len(archive_data)}"
        )
    digest = asset.get("digest")
    if digest is not None and (
        hashlib.sha256(archive_data).hexdigest()
        != str(digest).removeprefix("sha256:")
    ):
        raise RuntimeError(
            f"{NAME} release bundle does not match its GitHub SHA-256 digest"
        )


def _text(member: ArchiveMember) -> str:
    try:
        return member.data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RuntimeError(f"{member.path} is not UTF-8") from exc


def _require_markers(
    member: ArchiveMember, text: str, markers: Sequence[str]
) -> None:
    missing = [marker for marker in markers if marker not in text]
    if missing:
        raise RuntimeError(
            f"{member.path} is missing required markers: " + ", ".join(missing)
        )


def _validate_script(member: ArchiveMember, *, markers: Sequence[str]) -> None:
    if not member.data.startswith(b"#!"):
        raise RuntimeError(f"{member.path} has no shebang")
    text = _text(member)
    _require_markers(member, f"{text}\n{expand_shell_variables(text)}", markers)


def _validate_arm_elf(path: str, data: bytes) -> None:
    if len(data) < 20 or not data.startswith(b"\x7fELF"):
        raise RuntimeError(f"{path} is not an ELF binary")
    if data[4:6] != b"\x01\x01" or data[18:20] != b"\x28\x00":
        raise RuntimeError(f"{path} is not a 32-bit little-endian ARM binary")


def _validate_glibc_ceiling(path: str, data: bytes) -> None:
    versions = {
        (int(major), int(minor)) for major, minor in GLIBC_PATTERN.findall(data)
    }
    if not versions:
        raise RuntimeError(f"{path} has no GLIBC symbol versions")
    newest = max(versions)
    if newest > (2, 29):
        raise RuntimeError(
            f"{path} requires GLIBC_{newest[0]}.{newest[1]}, above MiSTer's "
            "GLIBC_2.29 compatibility ceiling"
        )


def _validate_registry(member: ArchiveMember) -> None:
    """The hook's entry must start the bundled launcher and nothing else."""
    launchers = [
        line.split("=", 1)[1].strip()
        for line in _text(member).splitlines()
        if line.strip().startswith("launcher=")
    ]
    if launchers != [f"/media/fat/{ENGINE_LAUNCHER}"]:
        raise RuntimeError(
            f"{REGISTRY} does not start /media/fat/{ENGINE_LAUNCHER}: "
            + (", ".join(launchers) or "no launcher=")
        )


def _validate_mgl(member: ArchiveMember) -> None:
    text = _text(member)
    if "<rbf>_Other/DonutDodo</rbf>" not in text or "<file" in text:
        raise RuntimeError(f"{CORE_MGL} must only load the _Other/DonutDodo_* core")


def selected_files(
    members: Sequence[ArchiveMember],
) -> tuple[tuple[str, ArchiveMember], ...]:
    """Validate the release layout and install every file it publishes."""
    by_path: dict[str, ArchiveMember] = {}
    case_paths: dict[str, str] = {}
    for member in members:
        case_key = member.path.casefold()
        if case_key in case_paths:
            raise RuntimeError(
                f"Case-colliding files in {NAME} ZIP: "
                f"{case_paths[case_key]} and {member.path}"
            )
        case_paths[case_key] = member.path
        by_path[member.path] = member

    unexpected = sorted(
        path for path in by_path if not path.startswith(INSTALL_ROOTS)
    )
    if unexpected:
        raise RuntimeError(
            f"{NAME} ZIP installs outside its MiSTer folders: "
            + ", ".join(unexpected)
        )

    user_owned = sorted(
        path
        for path in by_path
        if path.casefold() in {owned.casefold() for owned in USER_OWNED_FILES}
        or path.casefold().startswith(
            tuple(folder.casefold() for folder in USER_OWNED_FOLDERS)
        )
    )
    if user_owned:
        raise RuntimeError(
            f"{NAME} ZIP would overwrite user-supplied game data, saves or "
            "settings: " + ", ".join(user_owned)
        )

    cores = sorted(path for path in by_path if CORE_PATTERN.fullmatch(path))
    if len(cores) != 1:
        raise RuntimeError(
            f"{NAME} ZIP must ship exactly one _Other/DonutDodo_YYYYMMDD.rbf "
            "core, found: " + (", ".join(cores) or "none")
        )
    other_core_files = sorted(
        path
        for path in by_path
        if path.startswith("_Other/") and path not in (cores[0], CORE_MGL)
    )
    if other_core_files:
        raise RuntimeError(
            f"{NAME} ZIP has unexpected files under _Other/: "
            + ", ".join(other_core_files)
        )
    other_scripts = sorted(
        path
        for path in by_path
        if path.startswith("Scripts/") and path not in SCRIPTS
    )
    if other_scripts:
        raise RuntimeError(
            f"{NAME} ZIP has unexpected files under Scripts/: "
            + ", ".join(other_scripts)
        )

    missing = sorted(REQUIRED.difference(by_path))
    if missing:
        raise RuntimeError(
            f"{NAME} ZIP is missing required files: " + ", ".join(missing)
        )
    modules = [path for path in by_path if MODULE_PATTERN.fullmatch(path)]
    if not modules:
        raise RuntimeError(f"{NAME} ZIP has no mem_wc-<kernel>.ko module")

    core_size = len(by_path[cores[0]].data)
    if not 1_000_000 <= core_size <= 16_000_000:
        raise RuntimeError(f"{cores[0]} has an implausible RBF size: {core_size}")

    _validate_script(
        by_path[ENGINE_LAUNCHER],
        markers=(
            f"/media/fat/{GAMEDIR}",
            '"./frt_3.5.2"',
            '"--main-pack" "gamedata/DonutDodo.pck"',
            "platform/launch_lib.sh",
        ),
    )
    _require_markers(
        by_path[PLATFORM_LAUNCHER], _text(by_path[PLATFORM_LAUNCHER]), ("mh_main()",)
    )
    for path in SCRIPTS:
        _validate_script(by_path[path], markers=(f"/media/fat/{WRAPPER}",))

    for path in (ENGINE, WRAPPER):
        validate_arm_binary(path, by_path[path].data)
        _validate_glibc_ceiling(path, by_path[path].data)
    if WRAPPER_MARKER not in by_path[WRAPPER].data:
        raise RuntimeError(f"{WRAPPER} is not the mister-hybrid main= hook build")
    _validate_registry(by_path[REGISTRY])
    _validate_mgl(by_path[CORE_MGL])
    for path, member in by_path.items():
        if SHARED_OBJECT_PATTERN.fullmatch(path) or path in modules:
            _validate_arm_elf(path, member.data)

    return tuple((path, by_path[path]) for path in sorted(by_path))


def main() -> int:
    args = generator_parser(FOLDER, f"Generate the {NAME} database").parse_args()
    release = github_latest_release(UPSTREAM)
    asset, version = release_asset(release)
    archive_url = release_asset_url(asset)
    archive_data = http_get_bytes(archive_url)
    validate_archive_download(asset, archive_data)
    selected = selected_files(read_archive_members(archive_data))

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
                description=f"Installing {NAME} {version}",
                # An already-loaded kernel module stays resident after its file
                # changes, so a matching module update takes effect on reboot.
                reboot_paths=tuple(
                    path for path, _ in selected if MODULE_PATTERN.fullmatch(path)
                ),
            ),
        ),
        filter_terms=(FOLDER, "other"),
        tag_aliases=((FOLDER, "donutdodo", "dodo"),),
    )
    write_bundle(database, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
