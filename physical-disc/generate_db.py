#!/usr/bin/env python3

from __future__ import annotations

import posixpath
import re
import sys
import xml.etree.ElementTree as ElementTree
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".github"))

from db_helpers import (  # noqa: E402
    ArchiveMember,
    SelectiveArchive,
    build_multi_selective_archive_database,
    generation_timestamp,
    generator_parser,
    github_latest_release,
    http_get_bytes,
    read_archive_members,
    release_asset_url,
    write_bundle,
)


FOLDER = "physical-disc"
UPSTREAM_OWNER = "Anime0t4ku"
MAIN_REPOSITORY = "Main_MiSTer_Physical_Disc"
ARCHIVE_ID = "physical-cd"


def zip_assets(
    release: dict[str, Any], repository: str
) -> tuple[dict[str, Any], ...]:
    assets = [
        asset
        for asset in release.get("assets") or []
        if isinstance(asset, dict)
        and str(asset.get("name") or "").lower().endswith(".zip")
    ]
    if not assets:
        tag = release.get("tag_name") or release.get("name") or "unknown"
        raise RuntimeError(
            f"{repository} release {tag} does not contain a ZIP asset"
        )
    return tuple(assets)


def main_setting_from_release_body(body: str) -> str:
    current_section = ""
    settings: list[str] = []

    for line in body.splitlines():
        stripped = line.strip()
        section = re.fullmatch(r"\[([^\]]+)\]", stripped)
        if section:
            current_section = section.group(1).strip()
            continue
        if current_section.casefold() != "cd-*":
            continue
        setting = re.fullmatch(r"main\s*=\s*(\S+)", stripped, re.IGNORECASE)
        if setting:
            settings.append(setting.group(1))

    unique_settings = set(settings)
    if len(unique_settings) != 1:
        raise RuntimeError(
            "Main release notes must contain exactly one "
            "[CD-*] main=<filename> setting"
        )
    return settings[0]


def _xml_elements(root: ElementTree.Element, name: str) -> list[ElementTree.Element]:
    return [
        element
        for element in root.iter()
        if element.tag.rsplit("}", 1)[-1].casefold() == name.casefold()
    ]


def launcher_rbf_target(repository_name: str, mgl: ArchiveMember) -> str:
    """Validate an MGL and return the RBF path (without extension) it launches."""
    try:
        root = ElementTree.fromstring(mgl.data.decode("utf-8-sig"))
    except (UnicodeDecodeError, ElementTree.ParseError) as exc:
        raise RuntimeError(
            f"{repository_name} contains an invalid MGL: {mgl.path}"
        ) from exc

    rbf_elements = _xml_elements(root, "rbf")
    if len(rbf_elements) != 1 or not (rbf_elements[0].text or "").strip():
        raise RuntimeError(
            f"{repository_name} MGL must contain exactly one RBF path: {mgl.path}"
        )

    setname_elements = _xml_elements(root, "setname")
    if (
        len(setname_elements) != 1
        or setname_elements[0].get("same_dir") != "1"
        or not (setname_elements[0].text or "").strip().upper().startswith("CD-")
    ):
        raise RuntimeError(
            f"{repository_name} MGL must use a CD-* setname with "
            f'same_dir="1": {mgl.path}'
        )

    return posixpath.normpath(
        (rbf_elements[0].text or "").strip().replace("\\", "/").strip("/")
    )


def main_archive(
    repository_name: str,
    release: dict[str, Any],
    archive_url: str,
    archive_data: bytes,
    members: list[ArchiveMember],
) -> SelectiveArchive:
    executables = [
        member
        for member in members
        if "/" not in member.path and member.path.startswith("MiSTer_")
    ]
    if len(executables) != 1:
        raise RuntimeError(
            f"{repository_name} ZIP must contain one root-level MiSTer executable"
        )
    executable = executables[0]
    configured_main = main_setting_from_release_body(
        str(release.get("body") or "")
    )
    if configured_main != executable.path:
        raise RuntimeError(
            f"{repository_name} release notes select {configured_main}, "
            f"but the ZIP contains {executable.path}"
        )

    mgls = [member for member in members if member.path.lower().endswith(".mgl")]
    rbfs = [member for member in members if member.path.lower().endswith(".rbf")]
    if not mgls:
        raise RuntimeError(
            f"{repository_name} ZIP must contain at least one MGL launcher"
        )

    launcher_members = (*mgls, *rbfs)
    roots = {
        member.path.split("/", 1)[0]
        for member in launcher_members
        if "/" in member.path
    }
    if len(roots) != 1 or any("/" not in member.path for member in launcher_members):
        raise RuntimeError(
            f"{repository_name} launchers and cores must share one custom root"
        )
    custom_root = next(iter(roots))
    if not custom_root.startswith("_"):
        raise RuntimeError(
            f"{repository_name} ZIP root is not a custom menu folder: {custom_root}"
        )

    cores_folder = f"{custom_root}/Cores"
    for mgl in mgls:
        if posixpath.dirname(mgl.path) != custom_root:
            raise RuntimeError(
                f"{repository_name} MGL must be directly inside {custom_root}: "
                f"{mgl.path}"
            )
    for rbf in rbfs:
        if posixpath.dirname(rbf.path) != cores_folder:
            raise RuntimeError(
                f"{repository_name} bundled core must be inside {cores_folder}: "
                f"{rbf.path}"
            )

    bundled_cores = {rbf.path.casefold(): rbf for rbf in rbfs}
    launched_cores: set[str] = set()
    for mgl in mgls:
        target = launcher_rbf_target(repository_name, mgl)
        bundled_key = f"{target}.rbf".casefold()
        if bundled_key in bundled_cores:
            launched_cores.add(bundled_key)
        elif target.casefold().startswith(f"{custom_root}/".casefold()):
            # Points inside the custom folder yet no such core ships in the ZIP.
            raise RuntimeError(
                f"{repository_name} MGL selects a bundled core missing from the "
                f"ZIP: {target}.rbf ({mgl.path})"
            )
        # Otherwise the MGL launches an official stable core supplied by the
        # standard MiSTer distribution; it is intentionally not bundled here.

    orphan_cores = sorted(
        bundled_cores[key].path for key in set(bundled_cores) - launched_cores
    )
    if orphan_cores:
        raise RuntimeError(
            f"{repository_name} bundles cores that no MGL launches: "
            + ", ".join(orphan_cores)
        )

    selected = (executable, *sorted(mgls + rbfs, key=lambda member: member.path))
    tag = str(release.get("tag_name") or release.get("name") or "unknown")
    return SelectiveArchive(
        archive_id=ARCHIVE_ID,
        url=archive_url,
        data=archive_data,
        selected_files=tuple((member.path, member) for member in selected),
        description=f"Installing {repository_name} {tag}",
        reboot_paths=(executable.path,),
    )


def release_archive(repository: str) -> SelectiveArchive:
    repository_name = repository.rsplit("/", 1)[-1]
    release = github_latest_release(repository)
    compatible: list[SelectiveArchive] = []
    rejected: list[str] = []

    for asset in zip_assets(release, repository):
        name = str(asset.get("name") or "unnamed ZIP")
        try:
            archive_url = release_asset_url(asset)
            archive_data = http_get_bytes(archive_url)
            members = read_archive_members(archive_data)
            archive = main_archive(
                repository_name,
                release,
                archive_url,
                archive_data,
                members,
            )
        except (RuntimeError, zipfile.BadZipFile) as exc:
            rejected.append(f"{name}: {exc}")
        else:
            compatible.append(archive)

    if len(compatible) == 1:
        return compatible[0]
    if len(compatible) > 1:
        raise RuntimeError(
            f"{repository} release contains multiple compatible ZIP assets"
        )
    raise RuntimeError(
        f"{repository} release has no compatible ZIP asset: "
        + "; ".join(rejected)
    )


def main() -> int:
    args = generator_parser(
        FOLDER, "Generate the physical-disc database"
    ).parse_args()
    repository = f"{UPSTREAM_OWNER}/{MAIN_REPOSITORY}"
    print(f"Physical-disc repository: {repository}", flush=True)
    archive = release_archive(repository)

    database = build_multi_selective_archive_database(
        folder=FOLDER,
        repository=args.repository,
        timestamp=generation_timestamp(args.timestamp),
        archives=(archive,),
        filter_terms=(FOLDER, "console"),
        tag_aliases=((FOLDER, "physical-cd"),),
    )
    write_bundle(database, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
