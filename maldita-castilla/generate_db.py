#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import io
import json
import re
import stat
import sys
import zipfile
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


FOLDER = "maldita-castilla"
UPSTREAM = "gmcnaught/maldita.castilla-mister"
ARCHIVE_ID = "release"
VERSION_PATTERN = re.compile(r"v\d+\.\d+\.\d+", re.IGNORECASE)
ASSET_PATTERN = re.compile(
    r"MalditaCastilla-MiSTer-(v\d+\.\d+\.\d+)\.zip",
    re.IGNORECASE,
)
CORE_PATTERN = re.compile(r"_Other/MalditaCastilla_\d{8}\.rbf")
MODULE_PATTERN = re.compile(r"games/gmloader/platform/mem_wc/mem_wc-[^/]+\.ko")
SHARED_OBJECT_PATTERN = re.compile(r".+\.so(?:\.\d+)*")
GLIBC_PATTERN = re.compile(rb"GLIBC_(\d+)\.(\d+)")

# Bound both the download and its expansion before reading ZIP members. These
# limits leave ample room beyond the current ~64 MB / ~92 MB release while
# turning an accidentally enormous or hostile latest-release asset into a
# clear generator failure instead of an unbounded CI allocation.
MIN_ARCHIVE_SIZE = 1_000_000
MAX_ARCHIVE_SIZE = 150_000_000
MAX_ARCHIVE_FILES = 256
MAX_UNCOMPRESSED_SIZE = 256_000_000
MAX_MEMBER_SIZE = 128_000_000

# Upstream v0.4.1 (2026-09-28) moved the port onto the shared mister-hybrid
# platform. MiSTer.ini's main= target is games/gmloader/platform/MiSTer_hybrid,
# which starts the engine launcher named in the hybrid.d/ registry entry next to
# it; games/gmloader/MiSTer_Maldita and games/Maldita Castilla/ are gone. v0.4.0
# shipped that binary and entry under linux/, a root folder the Downloader
# refuses for every database but distribution_mister, so it was never
# published here.

# The Downloader cannot edit MiSTer.ini, so the [Maldita Castilla] main= line
# comes from these, as for Solarus: running Scripts/MalditaCastilla.sh once adds
# main=games/gmloader/platform/MiSTer_hybrid (backing MiSTer.ini up first) and
# loads the core; the CoresMenu entry turns that line off and on. They are the
# only Scripts/ files installed.
MENU_SCRIPT = "Scripts/MalditaCastilla.sh"
CORES_MENU_SCRIPT = "Scripts/MalditaCastilla_CoresMenu.sh"
MENU_SCRIPTS = frozenset({MENU_SCRIPT, CORES_MENU_SCRIPT})
IGNORED = frozenset({"README.md".casefold()})
INSTALL_ROOTS = (
    "Scripts/",
    "_Other/",
    "games/gmloader/",
)
# The v0.3.x database installed a main= wrapper binary here, and its README had
# users point main= at it. Newer releases put the platform's stand-in script at
# the same path: MiSTer execs it as main=, it repoints [Maldita Castilla] main=
# at MiSTer_hybrid and then execs that, so an upgraded MiSTer.ini starts the
# game instead of stock MiSTer. Optional: releases before it lack the file.
LEGACY_MAIN = "games/gmloader/MiSTer_Maldita"
PUBLISHED_SAVE_FILES = frozenset(
    {
        "games/gmloader/saves/game.droid",
        "games/gmloader/saves/options.ini",
    }
)
PUBLISHED_APK_FOLDER_FILES = frozenset({"games/gmloader/APKs/README.txt"})
USER_OWNED = frozenset(
    {
        # The hook's registry entry names this as its opt-out switch: while the
        # file exists, loading the core does not start the engine.
        "games/gmloader/NOENGINE",
        # This opt-in developer file alters launch behaviour and must remain
        # under the user's control.
        "games/gmloader/bench.env",
    }
)

ENGINE_LAUNCHER = "games/gmloader/launch.sh"
PLATFORM_LAUNCHER = "games/gmloader/platform/launch_lib.sh"
MEMORY_MODULE_LOADER = "games/gmloader/platform/mem_wc_load.sh"
ENGINE = "games/gmloader/gmloader"
WRAPPER = "games/gmloader/platform/MiSTer_hybrid"
# The hook reads <its own folder>/hybrid.d/<CONF_STR core name>.conf.
REGISTRY = "games/gmloader/platform/hybrid.d/Maldita Castilla.conf"
# Upstream's Cores-browser entry; it only loads the dated core by prefix.
CORE_MGL = "_Other/Maldita Castilla.mgl"
# Linked into every platform v0.4+ hook build; a stock Main_MiSTer or a v0.3
# hook (which reads /media/fat/linux/hybrid.d) lacks it.
WRAPPER_MARKER = b"MiSTer_hybrid registry: <binary dir>/hybrid.d"
CONFIG = "games/gmloader/gmloader.json"
APK = "games/gmloader/mygame.apk"
GAME_DATA = "games/gmloader/saves/game.droid"
LICENCE = "games/gmloader/LICENSE.malditacastilla.txt"
CREDITS = "games/gmloader/maldita-castilla-readme.txt"

REQUIRED = frozenset(
    {
        MENU_SCRIPT,
        CORES_MENU_SCRIPT,
        ENGINE_LAUNCHER,
        PLATFORM_LAUNCHER,
        MEMORY_MODULE_LOADER,
        ENGINE,
        WRAPPER,
        REGISTRY,
        CONFIG,
        APK,
        GAME_DATA,
        "games/gmloader/saves/options.ini",
        LICENCE,
        CREDITS,
        "games/gmloader/APKs/README.txt",
        "games/gmloader/lib/armeabi-v7a/libstdc++.so",
        "games/gmloader/libGLES_sw.so",
        "games/gmloader/mesa/libEGL.so.1",
        "games/gmloader/mesa/libGLESv2.so.2",
        "games/gmloader/mesa/libdrm.so.2",
        "games/gmloader/mesa/libglapi.so.0",
        "games/gmloader/mesa/libtinfo.so.6",
        "games/gmloader/mesa/swrast_dri.so",
    }
)

# Maldita Castilla is CC BY-NC-ND 4.0. Pin the five reviewed, unmodified game
# files to the checksums recorded by upstream at release/gamedata/SOURCE.txt
# (PortMaster-New commit 9fcbf7e318ed1f5967457d79c2e84c0b4dcfc4b9).
# Engine/core updates continue automatically; changed game bytes stop for a
# fresh provenance and licence review instead of being silently redistributed.
GAME_FILE_SHA256 = {
    APK: "b40d646b6d25b34e07fcfe5b93b2a191eaf7b8962791808186dda2dd328ca075",
    GAME_DATA: "30821c816eb623af041a5407897f06df5dbfb36786efd0c955f5d26fd53aa579",
    "games/gmloader/saves/options.ini": (
        "735c10e22e63bcdba691a2c48862f774a0a61a45fbb52ef67bcb833e79a044c5"
    ),
    LICENCE: "f7f28b8c7a1af76b9874ca6d040e8b1eb6768fd1043106c9d315090ea96754e7",
    CREDITS: "899d543057cba14f393d33c7352fd5f8c3986b23b47a5b29b34c8467be2055f3",
}


def release_asset(release: Mapping[str, Any]) -> tuple[dict[str, Any], str]:
    """Select the one versioned bundle and tie its version to the release tag."""
    tag = str(release.get("tag_name") or "")
    if not VERSION_PATTERN.fullmatch(tag):
        raise RuntimeError(f"Maldita Castilla release has an invalid tag: {tag}")

    matching = [
        asset
        for asset in release.get("assets") or []
        if isinstance(asset, dict)
        and ASSET_PATTERN.fullmatch(str(asset.get("name") or ""))
        and str(asset.get("browser_download_url") or "").startswith("https://")
    ]
    if len(matching) != 1:
        raise RuntimeError(
            "Maldita Castilla release must publish exactly one versioned ZIP, "
            f"found {len(matching)}"
        )

    asset = matching_release_asset(dict(release), ASSET_PATTERN)
    match = ASSET_PATTERN.fullmatch(str(asset.get("name") or ""))
    if match is None or match.group(1).casefold() != tag.casefold():
        raise RuntimeError(
            "Maldita Castilla release tag and bundle version differ: "
            f"{tag} vs {asset.get('name') or 'unnamed asset'}"
        )
    url = release_asset_url(asset)
    expected_prefix = f"https://github.com/{UPSTREAM}/releases/download/{tag}/"
    if not url.startswith(expected_prefix):
        raise RuntimeError(
            "Maldita Castilla bundle URL does not belong to its release tag: "
            f"{url}"
        )
    return asset, tag


def validate_asset_metadata(asset: Mapping[str, Any]) -> int:
    size = asset.get("size")
    if not isinstance(size, int) or isinstance(size, bool):
        raise RuntimeError("Maldita Castilla release bundle has no integer size")
    if not MIN_ARCHIVE_SIZE <= size <= MAX_ARCHIVE_SIZE:
        raise RuntimeError(
            "Maldita Castilla release bundle has an implausible size: "
            f"{size}"
        )

    digest = asset.get("digest")
    if digest is not None and not re.fullmatch(r"sha256:[0-9a-f]{64}", str(digest)):
        raise RuntimeError(
            f"Maldita Castilla release bundle has an invalid digest: {digest}"
        )
    return size


def validate_archive_download(
    asset: Mapping[str, Any], archive_data: bytes
) -> None:
    expected_size = validate_asset_metadata(asset)
    if len(archive_data) != expected_size:
        raise RuntimeError(
            "Maldita Castilla release bundle size differs from GitHub metadata: "
            f"expected {expected_size}, downloaded {len(archive_data)}"
        )

    digest = asset.get("digest")
    if digest is not None:
        actual = hashlib.sha256(archive_data).hexdigest()
        if actual != str(digest).removeprefix("sha256:"):
            raise RuntimeError(
                "Maldita Castilla release bundle does not match its GitHub "
                "SHA-256 digest"
            )

    try:
        with zipfile.ZipFile(io.BytesIO(archive_data)) as archive:
            files = [info for info in archive.infolist() if not info.is_dir()]
    except zipfile.BadZipFile as exc:
        raise RuntimeError("Maldita Castilla release bundle is not a ZIP") from exc

    if not files:
        raise RuntimeError("Maldita Castilla release bundle is empty")
    if len(files) > MAX_ARCHIVE_FILES:
        raise RuntimeError(
            "Maldita Castilla release bundle contains too many files: "
            f"{len(files)}"
        )

    total_size = sum(info.file_size for info in files)
    if total_size > MAX_UNCOMPRESSED_SIZE:
        raise RuntimeError(
            "Maldita Castilla release bundle expands past the safety limit: "
            f"{total_size}"
        )

    for info in files:
        if info.flag_bits & 0x1:
            raise RuntimeError(
                f"Encrypted file in Maldita Castilla release bundle: {info.filename}"
            )
        if info.file_size > MAX_MEMBER_SIZE:
            raise RuntimeError(
                "Oversized file in Maldita Castilla release bundle: "
                f"{info.filename} ({info.file_size})"
            )
        mode = info.external_attr >> 16
        if stat.S_ISLNK(mode):
            raise RuntimeError(
                f"Symbolic link in Maldita Castilla release bundle: {info.filename}"
            )


def _member_map(members: Sequence[ArchiveMember]) -> dict[str, ArchiveMember]:
    by_path: dict[str, ArchiveMember] = {}
    case_paths: dict[str, str] = {}
    for member in members:
        if member.path in by_path:
            raise RuntimeError(
                f"Duplicate file in Maldita Castilla ZIP: {member.path}"
            )
        case_key = member.path.casefold()
        if case_key in case_paths:
            raise RuntimeError(
                "Case-colliding files in Maldita Castilla ZIP: "
                f"{case_paths[case_key]} and {member.path}"
            )
        by_path[member.path] = member
        case_paths[case_key] = member.path
    return by_path


def _validate_script(
    member: ArchiveMember, *, markers: Sequence[str]
) -> None:
    if not member.data.startswith(b"#!"):
        raise RuntimeError(f"Maldita Castilla script has no shebang: {member.path}")
    try:
        text = member.data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RuntimeError(
            f"Maldita Castilla script is not UTF-8: {member.path}"
        ) from exc
    searchable = f"{text}\n{expand_shell_variables(text)}"
    missing = [marker for marker in markers if marker not in searchable]
    if missing:
        raise RuntimeError(
            f"Maldita Castilla script {member.path} is missing required paths: "
            + ", ".join(missing)
        )


def _validate_library(
    member: ArchiveMember, *, markers: Sequence[str]
) -> None:
    """A shell library the launcher sources: no shebang, same path markers."""
    try:
        text = member.data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RuntimeError(
            f"Maldita Castilla script is not UTF-8: {member.path}"
        ) from exc
    missing = [marker for marker in markers if marker not in text]
    if missing:
        raise RuntimeError(
            f"Maldita Castilla script {member.path} is missing required paths: "
            + ", ".join(missing)
        )


def _validate_arm_elf(path: str, data: bytes) -> None:
    if len(data) < 20 or not data.startswith(b"\x7fELF"):
        raise RuntimeError(f"{path} is not an ELF binary")
    if data[4:6] != b"\x01\x01" or data[18:20] != b"\x28\x00":
        raise RuntimeError(f"{path} is not a 32-bit little-endian ARM binary")


def _validate_glibc_ceiling(path: str, data: bytes) -> None:
    versions = {
        (int(major), int(minor))
        for major, minor in GLIBC_PATTERN.findall(data)
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
    try:
        text = member.data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RuntimeError(f"{REGISTRY} is not UTF-8") from exc
    launchers = [
        line.split("=", 1)[1].strip()
        for line in text.splitlines()
        if line.strip().startswith("launcher=")
    ]
    if launchers != [f"/media/fat/{ENGINE_LAUNCHER}"]:
        raise RuntimeError(
            f"{REGISTRY} does not start /media/fat/{ENGINE_LAUNCHER}: "
            + (", ".join(launchers) or "no launcher=")
        )


def _validate_mgl(member: ArchiveMember) -> None:
    text = member.data.decode("utf-8", "replace")
    if "<rbf>_Other/MalditaCastilla</rbf>" not in text or "<file" in text:
        raise RuntimeError(
            f"{CORE_MGL} must only load the _Other/MalditaCastilla_* core"
        )


def _validate_config(member: ArchiveMember) -> None:
    try:
        config = json.loads(member.data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"{CONFIG} is not valid UTF-8 JSON") from exc
    required = {
        "save_dir": "saves",
        "apk_path": "mygame.apk",
        "blitter": 2,
        "force_platform": "os_android",
    }
    if not isinstance(config, dict) or any(
        config.get(key) != value for key, value in required.items()
    ):
        raise RuntimeError(
            f"{CONFIG} no longer points at the bundled game and FPGA blitter"
        )


def _validate_apk(member: ArchiveMember) -> None:
    try:
        with zipfile.ZipFile(io.BytesIO(member.data)) as archive:
            names = set(archive.namelist())
    except zipfile.BadZipFile as exc:
        raise RuntimeError(f"{APK} is not a valid APK/ZIP") from exc
    required = {
        "lib/armeabi-v7a/libopenal.so",
        "lib/armeabi-v7a/libyoyo.so",
    }
    missing = sorted(required.difference(names))
    if missing:
        raise RuntimeError(
            f"{APK} is missing its GameMaker ARM runner: " + ", ".join(missing)
        )


def _validate_game_files(by_path: Mapping[str, ArchiveMember]) -> None:
    for path, expected in GAME_FILE_SHA256.items():
        actual = hashlib.sha256(by_path[path].data).hexdigest()
        if actual != expected:
            raise RuntimeError(
                f"{path} changed from the reviewed, unmodified game payload"
            )

    licence = by_path[LICENCE].data.decode("utf-8", "replace")
    if "Attribution-NonCommercial-NoDerivatives 4.0 International" not in licence:
        raise RuntimeError(
            f"{LICENCE} does not contain the reviewed CC BY-NC-ND 4.0 licence"
        )
    if "Locomalito" not in by_path[CREDITS].data.decode("utf-8", "replace"):
        raise RuntimeError(f"{CREDITS} is missing the game's attribution")
    _validate_apk(by_path[APK])


def selected_files(
    members: Sequence[ArchiveMember],
) -> tuple[tuple[str, ArchiveMember], ...]:
    """Validate the release contract and install only its MiSTer payload."""
    by_path = _member_map(members)
    installable = {
        path: member
        for path, member in by_path.items()
        if path.casefold() not in IGNORED
    }

    unexpected = sorted(
        path
        for path in installable
        if not path.startswith(INSTALL_ROOTS)
        or (path.startswith("Scripts/") and path not in MENU_SCRIPTS)
    )
    if unexpected:
        raise RuntimeError(
            "Maldita Castilla ZIP installs outside its MiSTer folders: "
            + ", ".join(unexpected)
        )

    unsafe = sorted(
        path
        for path in installable
        if path.casefold() in {owned.casefold() for owned in USER_OWNED}
    )
    if unsafe:
        raise RuntimeError(
            "Maldita Castilla ZIP contains user-owned or daemon-controlled "
            "files: " + ", ".join(unsafe)
        )

    save_files = {
        path for path in installable if path.casefold().startswith(
            "games/gmloader/saves/".casefold()
        )
    }
    unexpected_saves = sorted(save_files.difference(PUBLISHED_SAVE_FILES))
    if unexpected_saves:
        raise RuntimeError(
            "Maldita Castilla ZIP would overwrite user save data: "
            + ", ".join(unexpected_saves)
        )

    apk_folder_files = {
        path for path in installable if path.casefold().startswith(
            "games/gmloader/apks/".casefold()
        )
    }
    unexpected_apks = sorted(
        apk_folder_files.difference(PUBLISHED_APK_FOLDER_FILES)
    )
    if unexpected_apks:
        raise RuntimeError(
            "Maldita Castilla ZIP would overwrite user-supplied APKs: "
            + ", ".join(unexpected_apks)
        )

    cores = sorted(path for path in installable if CORE_PATTERN.fullmatch(path))
    other_core_files = sorted(
        path
        for path in installable
        if path.startswith("_Other/") and path not in cores and path != CORE_MGL
    )
    if other_core_files:
        raise RuntimeError(
            "Maldita Castilla ZIP has unexpected files under _Other/: "
            + ", ".join(other_core_files)
        )
    if len(cores) != 1:
        raise RuntimeError(
            "Maldita Castilla ZIP must ship exactly one "
            "_Other/MalditaCastilla_YYYYMMDD.rbf core, found: "
            + (", ".join(cores) or "none")
        )

    missing = sorted(REQUIRED.difference(installable))
    if missing:
        raise RuntimeError(
            "Maldita Castilla ZIP is missing required files: " + ", ".join(missing)
        )

    modules = sorted(
        path for path in installable if MODULE_PATTERN.fullmatch(path)
    )
    if not modules:
        raise RuntimeError(
            "Maldita Castilla ZIP has no mem_wc-<kernel>.ko performance module"
        )

    core = installable[cores[0]]
    if not 1_000_000 <= len(core.data) <= 16_000_000:
        raise RuntimeError(
            f"{core.path} has an implausible RBF size: {len(core.data)}"
        )

    _validate_script(
        installable[ENGINE_LAUNCHER],
        markers=(
            "/media/fat/games/gmloader",
            '"./gmloader" "-c" "gmloader.json"',
            "platform/launch_lib.sh",
        ),
    )
    _validate_script(
        installable[MENU_SCRIPT],
        markers=(
            "/media/fat/games/gmloader/platform/MiSTer_hybrid",
            "/media/fat/_Other/MalditaCastilla_",
        ),
    )
    _validate_script(
        installable[CORES_MENU_SCRIPT],
        markers=(
            "/media/fat/games/gmloader/platform/MiSTer_hybrid",
            "/media/fat/MiSTer.ini",
        ),
    )
    if LEGACY_MAIN in installable:
        # It must hand over to the hook, or fall back to stock MiSTer: nothing
        # respawns MiSTer if the process MiSTer exec'd as main= just exits.
        _validate_script(
            installable[LEGACY_MAIN],
            markers=(
                "/media/fat/games/gmloader/platform/MiSTer_hybrid",
                'exec "$HOOK" "$@"',
                "/media/fat/MiSTer",
            ),
        )
    _validate_library(installable[PLATFORM_LAUNCHER], markers=("mh_main()",))
    _validate_library(
        installable[MEMORY_MODULE_LOADER], markers=("mem_wc-", "uname -r")
    )

    for path in (ENGINE, WRAPPER):
        validate_arm_binary(path, installable[path].data)
        _validate_glibc_ceiling(path, installable[path].data)
    if WRAPPER_MARKER not in installable[WRAPPER].data:
        raise RuntimeError(f"{WRAPPER} is not the mister-hybrid main= hook build")
    _validate_registry(installable[REGISTRY])
    if CORE_MGL in installable:
        _validate_mgl(installable[CORE_MGL])

    for path, member in installable.items():
        if SHARED_OBJECT_PATTERN.fullmatch(path) or path in modules:
            _validate_arm_elf(path, member.data)

    if (
        installable["games/gmloader/libGLES_sw.so"].data
        != installable["games/gmloader/mesa/libGLESv2.so.2"].data
    ):
        raise RuntimeError(
            "games/gmloader/libGLES_sw.so is not the bundled Mesa libGLESv2"
        )

    _validate_config(installable[CONFIG])
    _validate_game_files(installable)

    return tuple(
        (path, installable[path]) for path in sorted(installable)
    )


def main() -> int:
    args = generator_parser(
        FOLDER, "Generate the Maldita Castilla MiSTer database"
    ).parse_args()
    release = github_latest_release(UPSTREAM)
    asset, version = release_asset(release)
    validate_asset_metadata(asset)
    archive_url = release_asset_url(asset)
    archive_data = http_get_bytes(archive_url)
    validate_archive_download(asset, archive_data)
    selected = selected_files(read_archive_members(archive_data))
    modules = tuple(
        path for path, _ in selected if MODULE_PATTERN.fullmatch(path)
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
                description=f"Installing Maldita Castilla MiSTer {version}",
                # An already-loaded kernel module stays resident after its file
                # changes, so a matching module update takes effect on reboot.
                reboot_paths=modules,
            ),
        ),
        filter_terms=(FOLDER, "other"),
        tag_aliases=((FOLDER, "malditacastilla", "maldita", "castilla"),),
    )
    write_bundle(database, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
