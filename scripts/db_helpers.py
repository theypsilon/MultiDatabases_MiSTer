#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import posixpath
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence


DB_NAMESPACE = "MultiDatabases_MiSTer"
DEFAULT_REPOSITORY = "theypsilon/MultiDatabases_MiSTer"
USER_AGENT = "MultiDatabases-MiSTer/1"

INVALID_EXACT_PATHS = {
    "mister",
    "menu.rbf",
    "mister.ini",
    "mister_alt.ini",
    "mister_alt_1.ini",
    "mister_alt_2.ini",
    "mister_alt_3.ini",
    "mister_new",
    "downloader.ini",
}
INVALID_ROOT_FOLDERS = {"linux", "saves", "savestates", "screenshots", "downloader"}
MD5_RE = re.compile(r"^[0-9a-f]{32}$")


@dataclass(frozen=True)
class ArchiveMember:
    archive_path: str
    path: str
    data: bytes


@dataclass(frozen=True)
class DirectFile:
    path: str
    url: str
    data: bytes
    reboot: bool = False
    tangles: tuple[str, ...] = ()


def generator_parser(folder: str, description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "dist" / folder,
        help=f"Output directory (default: dist/{folder})",
    )
    parser.add_argument(
        "--repository",
        default=os.getenv("TARGET_REPOSITORY")
        or os.getenv("GITHUB_REPOSITORY")
        or DEFAULT_REPOSITORY,
        help="GitHub owner/repository used in the generated database URL",
    )
    parser.add_argument(
        "--timestamp",
        type=int,
        default=None,
        help="Override the database generation timestamp (mainly for tests)",
    )
    return parser


def generation_timestamp(value: int | None) -> int:
    return int(time.time()) if value is None else value


def database_id(folder: str) -> str:
    return f"{DB_NAMESPACE}/{folder}"


def database_url(repository: str, folder: str) -> str:
    if repository.count("/") != 1:
        raise ValueError(f'Expected repository as "owner/name", got: {repository}')
    return (
        f"https://raw.githubusercontent.com/{repository}/db/"
        f"{folder}/db.json.zip"
    )


def http_get_bytes(url: str, *, accept: str = "application/octet-stream") -> bytes:
    headers = {
        "Accept": accept,
        "User-Agent": USER_AGENT,
    }
    if urllib.parse.urlparse(url).hostname == "api.github.com":
        token = os.getenv("GITHUB_TOKEN", "").strip()
        if token:
            headers["Authorization"] = f"Bearer {token}"
            headers["X-GitHub-Api-Version"] = "2022-11-28"

    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code} while downloading {url}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Unable to download {url}: {exc.reason}") from exc


def github_json(url: str) -> Any:
    return json.loads(
        http_get_bytes(url, accept="application/vnd.github+json").decode("utf-8")
    )


def github_latest_release(repository: str) -> dict[str, Any]:
    value = github_json(f"https://api.github.com/repos/{repository}/releases/latest")
    if not isinstance(value, dict):
        raise RuntimeError(f"Unexpected latest-release response for {repository}")
    return value


def github_releases(repository: str) -> list[dict[str, Any]]:
    value = github_json(
        f"https://api.github.com/repos/{repository}/releases?per_page=100"
    )
    if not isinstance(value, list):
        raise RuntimeError(f"Unexpected releases response for {repository}")
    return [release for release in value if isinstance(release, dict)]


def matching_release_asset(
    release: dict[str, Any],
    pattern: re.Pattern[str],
    *,
    highest_match: bool = False,
) -> dict[str, Any]:
    matches: list[tuple[str, dict[str, Any]]] = []
    for asset in release.get("assets") or []:
        if not isinstance(asset, dict):
            continue
        name = str(asset.get("name") or "")
        url = str(asset.get("browser_download_url") or "")
        match = pattern.fullmatch(name)
        if match and url.startswith("https://"):
            key = match.group(1) if highest_match and match.groups() else name
            matches.append((key, asset))

    if not matches:
        tag = release.get("tag_name") or release.get("name") or "unknown"
        raise RuntimeError(f"No matching release asset found in release {tag}")

    if highest_match:
        matches.sort(key=lambda item: item[0], reverse=True)
    return matches[0][1]


def first_zip_asset(release: dict[str, Any]) -> dict[str, Any]:
    for asset in release.get("assets") or []:
        if not isinstance(asset, dict):
            continue
        name = str(asset.get("name") or "")
        url = str(asset.get("browser_download_url") or "")
        if name.lower().endswith(".zip") and url.startswith("https://"):
            return asset
    tag = release.get("tag_name") or release.get("name") or "unknown"
    raise RuntimeError(f"No ZIP asset found in release {tag}")


def release_asset_url(asset: dict[str, Any]) -> str:
    url = str(asset.get("browser_download_url") or "")
    if not url.startswith("https://"):
        raise RuntimeError(f"Invalid release asset URL: {url}")
    return url


def read_archive_members(archive_data: bytes) -> list[ArchiveMember]:
    members: list[ArchiveMember] = []
    seen_paths: set[str] = set()

    with zipfile.ZipFile(io.BytesIO(archive_data)) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue

            archive_path = info.filename.replace("\\", "/")
            if archive_path.startswith("/"):
                raise RuntimeError(f"Unsafe absolute path in ZIP: {info.filename}")

            normalized = posixpath.normpath(archive_path)
            if (
                normalized in {"", ".", ".."}
                or normalized.startswith("../")
                or "/../" in f"/{normalized}/"
            ):
                raise RuntimeError(f"Unsafe path in ZIP: {info.filename}")
            if normalized in seen_paths:
                raise RuntimeError(f"Duplicate path in ZIP: {normalized}")

            seen_paths.add(normalized)
            members.append(
                ArchiveMember(
                    archive_path=info.filename,
                    path=normalized,
                    data=archive.read(info),
                )
            )

    if not members:
        raise RuntimeError("The release ZIP is empty")
    return members


def build_selective_archive_database(
    *,
    folder: str,
    repository: str,
    timestamp: int,
    archive_url: str,
    archive_data: bytes,
    selected_files: Sequence[tuple[str, ArchiveMember]],
    description: str,
    extra_folders: Iterable[str] = (),
) -> dict[str, Any]:
    archive_id = "release"
    summary_files: dict[str, dict[str, Any]] = {}

    for destination, member in selected_files:
        destination = normalize_install_path(destination)
        if destination in summary_files:
            raise RuntimeError(f"Duplicate destination path: {destination}")
        summary_files[destination] = {
            "hash": md5(member.data),
            "size": len(member.data),
            "overwrite": True,
            "arc_id": archive_id,
            "arc_at": member.archive_path,
        }

    if not summary_files:
        raise RuntimeError(f"No installable files selected for {folder}")

    summary_folders = {
        path: {"arc_id": archive_id}
        for path in parent_folders(summary_files)
    }
    db_id = database_id(folder)
    db_url = database_url(repository, folder)
    database = {
        "v": 1,
        "db_id": db_id,
        "db_url": db_url,
        "timestamp": timestamp,
        "files": {},
        "folders": {path: {} for path in expanded_folders(extra_folders)},
        "tag_dictionary": {},
        "archives": {
            archive_id: {
                "format": "zip",
                "extract": "selective",
                "description": description,
                "archive_file": {
                    "hash": md5(archive_data),
                    "size": len(archive_data),
                    "url": archive_url,
                },
                "summary_inline": {
                    "files": dict(sorted(summary_files.items())),
                    "folders": dict(sorted(summary_folders.items())),
                },
            }
        },
    }
    validate_database(database)
    return database


def build_direct_database(
    *,
    folder: str,
    repository: str,
    timestamp: int,
    direct_files: Sequence[DirectFile],
    extra_folders: Iterable[str] = (),
) -> dict[str, Any]:
    files: dict[str, dict[str, Any]] = {}
    for item in direct_files:
        destination = normalize_install_path(item.path)
        if destination in files:
            raise RuntimeError(f"Duplicate destination path: {destination}")
        description: dict[str, Any] = {
            "hash": md5(item.data),
            "size": len(item.data),
            "url": item.url,
            "overwrite": True,
        }
        if item.reboot:
            description["reboot"] = True
        if item.tangles:
            description["tangle"] = list(item.tangles)
        files[destination] = description

    all_folders = set(parent_folders(files))
    all_folders.update(expanded_folders(extra_folders))
    db_id = database_id(folder)
    db_url = database_url(repository, folder)
    database = {
        "v": 1,
        "db_id": db_id,
        "db_url": db_url,
        "timestamp": timestamp,
        "files": dict(sorted(files.items())),
        "folders": {path: {} for path in sorted(all_folders)},
        "tag_dictionary": {},
    }
    validate_database(database)
    return database


def write_bundle(database: dict[str, Any], output: Path) -> None:
    validate_database(database)
    output.mkdir(parents=True, exist_ok=True)

    encoded = (
        json.dumps(database, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")
    (output / "db.json").write_bytes(encoded)

    with zipfile.ZipFile(
        output / "db.json.zip", "w", compression=zipfile.ZIP_DEFLATED
    ) as archive:
        archive.writestr("db.json", encoded)

    db_id = str(database["db_id"])
    db_url = str(database["db_url"])
    sanitized_id = re.sub(r"[^A-Za-z0-9._-]+", "_", db_id).strip("._-")
    if not sanitized_id:
        raise RuntimeError(f"Unable to create a drop-in name for {db_id}")

    ini_name = f"downloader_{sanitized_id}.ini"
    ini_contents = f"[{db_id}]\ndb_url = {db_url}\n".encode("utf-8")
    (output / ini_name).write_bytes(ini_contents)

    with zipfile.ZipFile(
        output / f"downloader_{sanitized_id}.zip",
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:
        archive.writestr(ini_name, ini_contents)

    print(f"Generated {db_id} in {output}", flush=True)


def validate_database(database: dict[str, Any]) -> None:
    required = {"v", "db_id", "timestamp", "files", "folders"}
    missing = required.difference(database)
    if missing:
        raise RuntimeError(f"Database is missing fields: {sorted(missing)}")
    if database["v"] != 1:
        raise RuntimeError("Database version must be 1")
    if not isinstance(database["db_id"], str) or not database["db_id"]:
        raise RuntimeError("Database ID must be a non-empty string")
    if not isinstance(database["timestamp"], int):
        raise RuntimeError("Database timestamp must be an integer")
    if not isinstance(database["files"], dict):
        raise RuntimeError("Database files must be an object")
    if not isinstance(database["folders"], dict):
        raise RuntimeError("Database folders must be an object")

    for path, description in database["files"].items():
        validate_install_path(path)
        validate_file_description(description, require_url=True)
    for path in database["folders"]:
        validate_install_path(path)

    for archive_id, archive in database.get("archives", {}).items():
        if archive.get("format") != "zip":
            raise RuntimeError(f"Archive {archive_id} must use ZIP")
        if archive.get("extract") not in {"all", "selective"}:
            raise RuntimeError(f"Archive {archive_id} has an invalid extraction mode")
        validate_file_description(archive.get("archive_file"), require_url=True)
        summary = archive.get("summary_inline")
        if not isinstance(summary, dict):
            raise RuntimeError(f"Archive {archive_id} needs summary_inline")
        for path, description in summary.get("files", {}).items():
            validate_install_path(path)
            validate_file_description(description, require_url=False)
            if description.get("arc_id") != archive_id:
                raise RuntimeError(f"{path} has the wrong arc_id")
            if not isinstance(description.get("arc_at"), str):
                raise RuntimeError(f"{path} needs an arc_at")
        for path, description in summary.get("folders", {}).items():
            validate_install_path(path)
            if description.get("arc_id") != archive_id:
                raise RuntimeError(f"{path} has the wrong folder arc_id")


def validate_file_description(value: Any, *, require_url: bool) -> None:
    if not isinstance(value, dict):
        raise RuntimeError("File description must be an object")
    if not isinstance(value.get("hash"), str) or not MD5_RE.fullmatch(value["hash"]):
        raise RuntimeError("File description needs a lowercase MD5 hash")
    if not isinstance(value.get("size"), int) or value["size"] < 0:
        raise RuntimeError("File description needs a non-negative size")
    if require_url:
        url = value.get("url")
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            raise RuntimeError("File description needs an HTTP(S) URL")


def normalize_install_path(path: str) -> str:
    normalized = path.replace("\\", "/").strip("/")
    validate_install_path(normalized)
    return normalized


def validate_install_path(path: str) -> None:
    if not isinstance(path, str) or not path:
        raise RuntimeError("Install paths must be non-empty strings")
    if path.startswith(("/", ".", "\\")):
        raise RuntimeError(f"Install path must be relative: {path}")
    normalized = path.replace("\\", "/")
    parts = normalized.lower().split("/")
    if "" in parts or ".." in parts:
        raise RuntimeError(f"Invalid install path: {path}")
    if normalized.lower() in INVALID_EXACT_PATHS:
        raise RuntimeError(f"Restricted install path: {path}")
    if parts[0] in INVALID_ROOT_FOLDERS:
        raise RuntimeError(f"Restricted root folder: {path}")


def parent_folders(paths: Iterable[str]) -> list[str]:
    result: set[str] = set()
    for path in paths:
        parent = posixpath.dirname(path)
        while parent:
            result.add(parent)
            parent = posixpath.dirname(parent)
    return sorted(result)


def expanded_folders(paths: Iterable[str]) -> list[str]:
    normalized = [normalize_install_path(path) for path in paths]
    result = set(normalized)
    result.update(parent_folders(normalized))
    return sorted(result)


def md5(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()
