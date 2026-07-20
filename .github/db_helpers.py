#!/usr/bin/env python3

"""Shared database generation helpers."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
import os
import posixpath
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Iterable, Iterator, Mapping, Sequence


DB_NAMESPACE = "MultiDatabases"
DEFAULT_REPOSITORY = "theypsilon/MultiDatabases_MiSTer"
USER_AGENT = "MultiDatabases-MiSTer/1"
DB_OPERATOR_REPOSITORY = "MiSTer-devel/Distribution_MiSTer"
DB_OPERATOR_REVISION = "main"
DB_OPERATOR_REPOSITORY_PATH = ".github/db_operator.py"

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
GIT_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


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
        f"{folder}/db.json"
    )


def github_raw_url(repository: str, revision: str, path: str) -> str:
    if repository.count("/") != 1:
        raise ValueError(f'Expected repository as "owner/name", got: {repository}')
    if not GIT_COMMIT_RE.fullmatch(revision):
        raise ValueError(f"Expected a full Git commit SHA, got: {revision}")
    encoded_path = urllib.parse.quote(path.strip("/"), safe="/")
    return (
        f"https://raw.githubusercontent.com/{repository}/"
        f"{revision}/{encoded_path}"
    )


def git_file_revision(path: Path, *, repository_root: Path | None = None) -> str:
    root = (
        Path(__file__).resolve().parents[1]
        if repository_root is None
        else repository_root.resolve()
    )
    try:
        relative = path.resolve().relative_to(root).as_posix()
    except ValueError as exc:
        raise RuntimeError(f"Asset is outside the repository: {path}") from exc

    status = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain", "--", relative],
        check=True,
        capture_output=True,
        text=True,
    )
    if status.stdout.strip():
        raise RuntimeError(
            f"Asset must be committed before generating its URL: {relative}"
        )

    result = subprocess.run(
        ["git", "-C", str(root), "log", "-1", "--format=%H", "--", relative],
        check=True,
        capture_output=True,
        text=True,
    )
    revision = result.stdout.strip()
    if not GIT_COMMIT_RE.fullmatch(revision):
        raise RuntimeError(f"Unable to find a committed revision for {relative}")
    return revision


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


def github_commit_sha(repository: str, revision: str) -> str:
    encoded_revision = urllib.parse.quote(revision, safe="")
    value = github_json(
        f"https://api.github.com/repos/{repository}/commits/{encoded_revision}"
    )
    if not isinstance(value, dict):
        raise RuntimeError(f"Unexpected commit response for {repository}")
    sha = str(value.get("sha") or "")
    if not GIT_COMMIT_RE.fullmatch(sha):
        raise RuntimeError(
            f"Unable to resolve {repository} revision {revision} to a commit"
        )
    return sha


def prepare_db_operator() -> Path:
    configured_path = os.getenv("DB_OPERATOR_PATH", "").strip()
    if configured_path:
        path = Path(configured_path).resolve()
        if not path.is_file():
            raise RuntimeError(f"DB_OPERATOR_PATH does not exist: {path}")
        return path

    revision = github_commit_sha(DB_OPERATOR_REPOSITORY, DB_OPERATOR_REVISION)
    path = (
        Path(tempfile.gettempdir())
        / f"distribution_db_operator_{revision}.py"
    )
    if path.is_file():
        return path

    url = github_raw_url(
        DB_OPERATOR_REPOSITORY,
        revision,
        DB_OPERATOR_REPOSITORY_PATH,
    )
    source = http_get_bytes(url, accept="text/plain")
    if b"class Tags:" not in source or b"initial_filter_aliases" not in source:
        raise RuntimeError(f"Downloaded file is not a compatible db_operator: {url}")

    temporary_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary_path.write_bytes(source)
    temporary_path.replace(path)
    print(f"Using Distribution db_operator.py at {revision}", flush=True)
    return path


def load_db_operator(path: Path | None = None) -> ModuleType:
    operator_path = prepare_db_operator() if path is None else path.resolve()
    module_name = f"_multidatabases_db_operator_{operator_path.stem}"
    spec = importlib.util.spec_from_file_location(module_name, operator_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load db_operator: {operator_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise

    if not hasattr(module, "Tags") or not hasattr(
        module, "initial_filter_aliases"
    ):
        raise RuntimeError(f"Incompatible db_operator: {operator_path}")
    return module


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
    filter_terms: Sequence[str],
    tag_aliases: Sequence[Sequence[str]] = (),
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
    apply_standard_tags(
        database,
        file_data={
            normalize_install_path(destination): member.data
            for destination, member in selected_files
        },
        filter_terms=filter_terms,
        tag_aliases=tag_aliases,
    )
    validate_database(database)
    return database


def build_direct_database(
    *,
    folder: str,
    repository: str,
    timestamp: int,
    direct_files: Sequence[DirectFile],
    filter_terms: Sequence[str],
    tag_aliases: Sequence[Sequence[str]] = (),
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
    apply_standard_tags(
        database,
        file_data={
            normalize_install_path(item.path): item.data
            for item in direct_files
        },
        filter_terms=filter_terms,
        tag_aliases=tag_aliases,
    )
    validate_database(database)
    return database


def apply_standard_tags(
    database: dict[str, Any],
    *,
    file_data: Mapping[str, bytes],
    filter_terms: Sequence[str],
    tag_aliases: Sequence[Sequence[str]] = (),
    operator_module: ModuleType | None = None,
) -> None:
    if not filter_terms:
        raise RuntimeError(f"{database.get('db_id', 'Database')} needs filter terms")

    operator = load_db_operator() if operator_module is None else operator_module
    metadata = {
        "home": {},
        "aliases": [list(alias_group) for alias_group in tag_aliases],
    }
    tags = operator.Tags(metadata, True)
    tags.init_aliases(operator.initial_filter_aliases)

    file_descriptions: list[tuple[str, dict[str, Any]]] = list(
        sorted(database["files"].items())
    )
    folder_descriptions: list[tuple[str, dict[str, Any]]] = list(
        sorted(database["folders"].items())
    )
    for archive_id in sorted(database.get("archives", {})):
        summary = database["archives"][archive_id]["summary_inline"]
        file_descriptions.extend(sorted(summary["files"].items()))
        folder_descriptions.extend(sorted(summary["folders"].items()))

    described_paths = {path for path, _ in file_descriptions}
    missing_data = described_paths.difference(file_data)
    if missing_data:
        raise RuntimeError(
            "Missing source data for tagged files: "
            + ", ".join(sorted(missing_data))
        )

    with tempfile.TemporaryDirectory() as temporary_directory:
        source_root = Path(temporary_directory)
        for path in sorted(described_paths):
            target = source_root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            if _db_operator_reads_file(path):
                target.write_bytes(file_data[path])
            else:
                target.touch()

        with working_directory(source_root):
            for path, description in file_descriptions:
                file_tags = tags.get_tags_for_file(Path(path))
                for term in filter_terms:
                    tag = tags._use_term(term)
                    if tag not in file_tags:
                        file_tags.append(tag)
                description["tags"] = sorted(file_tags)

            for path, description in folder_descriptions:
                folder_tags = tags.get_tags_for_folder(Path(path))
                for term in filter_terms:
                    tag = tags._use_term(term)
                    if tag not in folder_tags:
                        folder_tags.append(tag)
                description["tags"] = sorted(folder_tags)

    database["tag_dictionary"] = dict(sorted(tags.get_dictionary().items()))


def _db_operator_reads_file(path: str) -> bool:
    install_path = Path(path)
    return (
        install_path.suffix.lower() in {".mgl", ".mra"}
        or install_path.parts[0].lstrip("_").lower() == "wallpapers"
    )


@contextmanager
def working_directory(path: Path) -> Iterator[None]:
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def databases_have_same_content(
    previous: dict[str, Any], candidate: dict[str, Any]
) -> bool:
    previous_content = dict(previous)
    candidate_content = dict(candidate)
    previous_content.pop("timestamp", None)
    candidate_content.pop("timestamp", None)
    return previous_content == candidate_content


def bundle_needs_update(database: dict[str, Any], output: Path) -> bool:
    db_id = str(database["db_id"])
    sanitized_id = re.sub(r"[^A-Za-z0-9._-]+", "_", db_id).strip("._-")
    if not sanitized_id:
        raise RuntimeError(f"Unable to create a drop-in name for {db_id}")

    expected_files = (
        output / "db.json",
        output / "db.json.zip",
        output / f"downloader_{sanitized_id}.ini",
        output / f"downloader_{sanitized_id}.zip",
    )
    if not all(path.is_file() for path in expected_files):
        return True

    try:
        previous = json.loads((output / "db.json").read_bytes())
        validate_database(previous)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, RuntimeError, TypeError):
        return True

    return not databases_have_same_content(previous, database)


def write_bundle(database: dict[str, Any], output: Path) -> bool:
    validate_database(database)
    db_id = str(database["db_id"])
    if not bundle_needs_update(database, output):
        print(f"No changes detected for {db_id}; preserving existing bundle", flush=True)
        return False

    encoded = (
        json.dumps(database, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")

    if output.exists():
        if output.is_dir():
            shutil.rmtree(output)
        else:
            output.unlink()
    output.mkdir(parents=True)
    (output / "db.json").write_bytes(encoded)

    with zipfile.ZipFile(
        output / "db.json.zip", "w", compression=zipfile.ZIP_DEFLATED
    ) as archive:
        archive.writestr("db.json", encoded)

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
    return True


def validate_database(database: dict[str, Any]) -> None:
    required = {
        "v",
        "db_id",
        "timestamp",
        "files",
        "folders",
        "tag_dictionary",
    }
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
    tag_dictionary = database["tag_dictionary"]
    if not isinstance(tag_dictionary, dict):
        raise RuntimeError("Database tag_dictionary must be an object")
    for term, index in tag_dictionary.items():
        if not isinstance(term, str) or not term:
            raise RuntimeError("Tag dictionary terms must be non-empty strings")
        if not isinstance(index, int) or isinstance(index, bool) or index < 0:
            raise RuntimeError(f"Tag dictionary index for {term} must be non-negative")
    valid_tag_indexes = set(tag_dictionary.values())

    for path, description in database["files"].items():
        validate_install_path(path)
        validate_file_description(
            description,
            require_url=True,
            valid_tag_indexes=valid_tag_indexes,
            require_tags=True,
        )
    for path, description in database["folders"].items():
        validate_install_path(path)
        validate_description_tags(
            description,
            valid_tag_indexes=valid_tag_indexes,
            context=path,
            require_tags=True,
        )

    for archive_id, archive in database.get("archives", {}).items():
        if archive.get("format") != "zip":
            raise RuntimeError(f"Archive {archive_id} must use ZIP")
        if archive.get("extract") not in {"all", "selective"}:
            raise RuntimeError(f"Archive {archive_id} has an invalid extraction mode")
        validate_file_description(
            archive.get("archive_file"),
            require_url=True,
            valid_tag_indexes=valid_tag_indexes,
        )
        summary = archive.get("summary_inline")
        if not isinstance(summary, dict):
            raise RuntimeError(f"Archive {archive_id} needs summary_inline")
        for path, description in summary.get("files", {}).items():
            validate_install_path(path)
            validate_file_description(
                description,
                require_url=False,
                valid_tag_indexes=valid_tag_indexes,
                require_tags=True,
            )
            if description.get("arc_id") != archive_id:
                raise RuntimeError(f"{path} has the wrong arc_id")
            if not isinstance(description.get("arc_at"), str):
                raise RuntimeError(f"{path} needs an arc_at")
        for path, description in summary.get("folders", {}).items():
            validate_install_path(path)
            validate_description_tags(
                description,
                valid_tag_indexes=valid_tag_indexes,
                context=path,
                require_tags=True,
            )
            if description.get("arc_id") != archive_id:
                raise RuntimeError(f"{path} has the wrong folder arc_id")


def validate_file_description(
    value: Any,
    *,
    require_url: bool,
    valid_tag_indexes: set[int],
    require_tags: bool = False,
) -> None:
    if not isinstance(value, dict):
        raise RuntimeError("File description must be an object")
    if not isinstance(value.get("hash"), str) or not MD5_RE.fullmatch(value["hash"]):
        raise RuntimeError("File description needs a lowercase MD5 hash")
    if not isinstance(value.get("size"), int) or value["size"] < 0:
        raise RuntimeError("File description needs a non-negative size")
    if require_url:
        url = value.get("url")
        if not isinstance(url, str):
            raise RuntimeError("File description needs an HTTPS URL")
        validate_payload_url(url)
    validate_description_tags(
        value,
        valid_tag_indexes=valid_tag_indexes,
        context="File description",
        require_tags=require_tags,
    )


def validate_description_tags(
    value: Any,
    *,
    valid_tag_indexes: set[int],
    context: str,
    require_tags: bool,
) -> None:
    if not isinstance(value, dict):
        raise RuntimeError(f"{context} description must be an object")
    tags = value.get("tags")
    if tags is None and not require_tags:
        return
    if not isinstance(tags, list) or (require_tags and not tags):
        raise RuntimeError(f"{context} needs a non-empty tags list")
    for tag in tags:
        if not isinstance(tag, int) or isinstance(tag, bool):
            raise RuntimeError(f"{context} tag references must be integer indexes")
        if tag not in valid_tag_indexes:
            raise RuntimeError(f"{context} references unknown tag index {tag}")


def validate_payload_url(url: str) -> None:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise RuntimeError(f"Payload URL must use HTTPS: {url}")
    if parsed.query or parsed.fragment:
        raise RuntimeError(f"Payload URL must not use a query or fragment: {url}")

    parts = [urllib.parse.unquote(part) for part in parsed.path.split("/") if part]
    if parsed.hostname == "raw.githubusercontent.com":
        if len(parts) < 4 or not GIT_COMMIT_RE.fullmatch(parts[2]):
            raise RuntimeError(
                f"Raw GitHub payload URL must use a full commit SHA: {url}"
            )
        return

    if parsed.hostname == "github.com":
        if (
            len(parts) < 6
            or parts[2:4] != ["releases", "download"]
            or parts[4].lower() == "latest"
        ):
            raise RuntimeError(
                f"GitHub payload URL must identify a concrete release: {url}"
            )
        return

    raise RuntimeError(
        f"Payload URL must use a concrete GitHub release or commit: {url}"
    )


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
