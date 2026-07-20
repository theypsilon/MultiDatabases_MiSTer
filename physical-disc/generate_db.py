#!/usr/bin/env python3

from __future__ import annotations

import posixpath
import re
import sys
import urllib.parse
import xml.etree.ElementTree as ElementTree
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".github"))

from db_helpers import (  # noqa: E402
    ArchiveMember,
    SelectiveArchive,
    build_multi_selective_archive_database,
    generation_timestamp,
    generator_parser,
    github_json,
    github_latest_release,
    http_get_bytes,
    read_archive_members,
    release_asset_url,
    write_bundle,
)


FOLDER = "physical-disc"
UPSTREAM_OWNER = "Anime0t4ku"
REPOSITORY_SUFFIX = "_Physical_Disc"
MAIN_REPOSITORY = "Main_MiSTer_Physical_Disc"


def discover_repositories(
    owner: str = UPSTREAM_OWNER,
    *,
    fetch_json: Callable[[str], Any] | None = None,
) -> tuple[str, ...]:
    fetch = github_json if fetch_json is None else fetch_json
    matches: set[str] = set()

    for page in range(1, 101):
        encoded_owner = urllib.parse.quote(owner, safe="")
        response = fetch(
            f"https://api.github.com/users/{encoded_owner}/repos"
            f"?type=owner&sort=full_name&direction=asc&per_page=100&page={page}"
        )
        if not isinstance(response, list):
            raise RuntimeError(f"Unexpected repository response for {owner}")

        for repository in response:
            if not isinstance(repository, dict):
                continue
            name = str(repository.get("name") or "")
            full_name = str(repository.get("full_name") or "")
            if name.endswith(REPOSITORY_SUFFIX):
                expected_full_name = f"{owner}/{name}"
                if full_name != expected_full_name:
                    raise RuntimeError(
                        f"Unexpected owner for matching repository {full_name}"
                    )
                matches.add(full_name)

        if len(response) < 100:
            break
    else:
        raise RuntimeError(f"Repository pagination did not terminate for {owner}")

    if not matches:
        raise RuntimeError(
            f"No {owner} repositories end in {REPOSITORY_SUFFIX}"
        )
    required_main = f"{owner}/{MAIN_REPOSITORY}"
    if required_main not in matches:
        raise RuntimeError(
            f"Required physical-disc Main repository is missing: {required_main}"
        )
    return tuple(sorted(matches, key=str.casefold))


def unique_zip_asset(release: dict[str, Any], repository: str) -> dict[str, Any]:
    assets = [
        asset
        for asset in release.get("assets") or []
        if isinstance(asset, dict)
        and str(asset.get("name") or "").lower().endswith(".zip")
    ]
    if len(assets) != 1:
        tag = release.get("tag_name") or release.get("name") or "unknown"
        raise RuntimeError(
            f"{repository} release {tag} must contain exactly one ZIP asset; "
            f"found {len(assets)}"
        )
    return assets[0]


def archive_id_for(repository_name: str) -> str:
    if not repository_name.endswith(REPOSITORY_SUFFIX):
        raise RuntimeError(
            f"Repository does not end in {REPOSITORY_SUFFIX}: {repository_name}"
        )
    stem = repository_name[: -len(REPOSITORY_SUFFIX)]
    if stem.lower().endswith("_mister"):
        stem = stem[:-7]
    archive_id = re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-")
    if not archive_id:
        raise RuntimeError(f"Unable to derive archive ID from {repository_name}")
    return archive_id


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


def main_archive(
    repository_name: str,
    release: dict[str, Any],
    archive_url: str,
    archive_data: bytes,
    members: list[ArchiveMember],
) -> SelectiveArchive:
    if len(members) != 1 or "/" in members[0].path:
        raise RuntimeError(
            f"{repository_name} ZIP must contain one root-level MiSTer executable"
        )

    member = members[0]
    if not member.path.startswith("MiSTer_"):
        raise RuntimeError(
            f"{repository_name} ZIP file is not a named MiSTer executable: "
            f"{member.path}"
        )
    configured_main = main_setting_from_release_body(
        str(release.get("body") or "")
    )
    if configured_main != member.path:
        raise RuntimeError(
            f"{repository_name} release notes select {configured_main}, "
            f"but the ZIP contains {member.path}"
        )

    tag = str(release.get("tag_name") or release.get("name") or "unknown")
    return SelectiveArchive(
        archive_id=archive_id_for(repository_name),
        url=archive_url,
        data=archive_data,
        selected_files=((member.path, member),),
        description=f"Installing {repository_name} {tag}",
        reboot_paths=(member.path,),
    )


def _xml_elements(root: ElementTree.Element, name: str) -> list[ElementTree.Element]:
    return [
        element
        for element in root.iter()
        if element.tag.rsplit("}", 1)[-1].casefold() == name.casefold()
    ]


def validate_core_launcher(
    repository_name: str,
    rbf: ArchiveMember,
    mgl: ArchiveMember,
) -> None:
    try:
        root = ElementTree.fromstring(mgl.data.decode("utf-8-sig"))
    except (UnicodeDecodeError, ElementTree.ParseError) as exc:
        raise RuntimeError(
            f"{repository_name} contains an invalid MGL: {mgl.path}"
        ) from exc

    rbf_elements = _xml_elements(root, "rbf")
    if len(rbf_elements) != 1 or not (rbf_elements[0].text or "").strip():
        raise RuntimeError(
            f"{repository_name} MGL must contain exactly one RBF path"
        )
    launcher_rbf = posixpath.normpath(
        (rbf_elements[0].text or "").strip().replace("\\", "/").strip("/")
    )
    expected_rbf = posixpath.splitext(rbf.path)[0]
    if launcher_rbf.casefold() != expected_rbf.casefold():
        raise RuntimeError(
            f"{repository_name} MGL selects {launcher_rbf}, "
            f"but the ZIP contains {expected_rbf}.rbf"
        )

    setname_elements = _xml_elements(root, "setname")
    if (
        len(setname_elements) != 1
        or setname_elements[0].get("same_dir") != "1"
        or not (setname_elements[0].text or "").strip().upper().startswith("CD-")
    ):
        raise RuntimeError(
            f"{repository_name} MGL must use a CD-* setname with same_dir=\"1\""
        )


def core_archive(
    repository_name: str,
    release: dict[str, Any],
    archive_url: str,
    archive_data: bytes,
    members: list[ArchiveMember],
) -> SelectiveArchive:
    rbfs = [member for member in members if member.path.lower().endswith(".rbf")]
    mgls = [member for member in members if member.path.lower().endswith(".mgl")]
    if len(rbfs) != 1 or len(mgls) != 1:
        raise RuntimeError(
            f"{repository_name} ZIP must contain exactly one RBF and one MGL"
        )

    rbf = rbfs[0]
    mgl = mgls[0]
    roots = {
        member.path.split("/", 1)[0]
        for member in members
        if "/" in member.path
    }
    if len(roots) != 1 or any("/" not in member.path for member in members):
        raise RuntimeError(
            f"{repository_name} ZIP files must share one custom root folder"
        )
    custom_root = next(iter(roots))
    if not custom_root.startswith("_"):
        raise RuntimeError(
            f"{repository_name} ZIP root is not a custom menu folder: {custom_root}"
        )
    if posixpath.dirname(rbf.path) != f"{custom_root}/Cores":
        raise RuntimeError(
            f"{repository_name} RBF must be inside {custom_root}/Cores"
        )
    if posixpath.dirname(mgl.path) != custom_root:
        raise RuntimeError(
            f"{repository_name} MGL must be directly inside {custom_root}"
        )

    validate_core_launcher(repository_name, rbf, mgl)
    tag = str(release.get("tag_name") or release.get("name") or "unknown")
    return SelectiveArchive(
        archive_id=archive_id_for(repository_name),
        url=archive_url,
        data=archive_data,
        selected_files=tuple((member.path, member) for member in members),
        description=f"Installing {repository_name} {tag}",
        reboot_paths=(rbf.path,),
    )


def release_archive(repository: str) -> SelectiveArchive:
    repository_name = repository.rsplit("/", 1)[-1]
    release = github_latest_release(repository)
    asset = unique_zip_asset(release, repository)
    archive_url = release_asset_url(asset)
    archive_data = http_get_bytes(archive_url)
    members = read_archive_members(archive_data)

    if repository_name == MAIN_REPOSITORY:
        return main_archive(
            repository_name,
            release,
            archive_url,
            archive_data,
            members,
        )
    return core_archive(
        repository_name,
        release,
        archive_url,
        archive_data,
        members,
    )


def main() -> int:
    args = generator_parser(
        FOLDER, "Generate the dynamically discovered physical-disc database"
    ).parse_args()
    repositories = discover_repositories()
    print(
        "Physical-disc repositories: " + ", ".join(repositories),
        flush=True,
    )
    archives = tuple(release_archive(repository) for repository in repositories)

    database = build_multi_selective_archive_database(
        folder=FOLDER,
        repository=args.repository,
        timestamp=generation_timestamp(args.timestamp),
        archives=archives,
        filter_terms=(FOLDER, "console"),
        tag_aliases=((FOLDER, "physical-cd"),),
    )
    write_bundle(database, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
