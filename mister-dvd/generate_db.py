#!/usr/bin/env python3

"""Generate MiSTer DVD and stage its installer-produced runtime files."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import urllib.parse
import uuid
from pathlib import Path
from typing import Any, Mapping, NamedTuple, Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".github"))

from db_helpers import (  # noqa: E402
    ArchiveMember,
    DirectFile,
    build_selective_archive_database,
    generation_timestamp,
    generator_parser,
    github_commit_sha,
    github_latest_release,
    github_raw_url,
    http_get_bytes,
    normalize_install_path,
    read_archive_members,
    release_asset_url,
    write_bundle,
)


FOLDER = "mister-dvd"
UPSTREAM = "owenb321/MiSTer_DVD"
PAYLOAD_BRANCH = "db-assets"
ASSET_PATTERN = re.compile(r"MiSTer_DVD_(v\d+\.\d+\.\d+)\.zip", re.IGNORECASE)
# OPEN QUESTION (upstream v0.4.0, 2026-09-05): upstream stopped attaching
# install_dvdcss.sh as a standalone release asset, so unique_release_asset()
# finds none and the database stays on v0.3.0 — the gate working as designed.
# The ZIP still carries Scripts/install_dvdcss.sh, byte-identical to v0.3.0's,
# so the installer itself is unchanged and still reachable. Whether to keep
# requiring the loose asset or to take the installer from the ZIP member is a
# human decision, because sourcing it from the ZIP retires the standalone-copy
# cross-check below and changes the installer URL recorded in source.json.
INSTALLER_PATTERN = re.compile(r"install_dvdcss\.sh", re.IGNORECASE)
CORE_PATTERN = re.compile(r"DVD_\d{8}\.rbf", re.IGNORECASE)
# Every member of the release ZIP is enumerated here, so a file upstream adds
# stops the generator until a human gives it a disposition.
# OPEN QUESTION (upstream v0.4.0, 2026-09-05): Scripts/dvd_report.py is new and
# has no disposition, so selected_files() fails. The installed MiSTer_DVDcss
# binary loads it from the fixed path /media/fat/Scripts/dvd_report.py and
# reports "Support bundle needs dvd_report.py" without it, so withholding it
# ships a Main with a feature that cannot work. Installing it also makes it
# required. Either way a human records the value; the build stays red until then.
EXPECTED_FILES = {
    "MiSTer_DVDcss",
    "Scripts/install_dvdcss.sh",
}
INSTALLABLE_FILES = {"MiSTer_DVDcss"}
# Scripts/set_dvd_region.sh, added by upstream v0.3.0, is withheld by review
# (pull request #3, 2026-09-01): it sets a USB DVD drive's RPC region through
# the DVD_AUTH ioctl, a change drives allow only about five times and never
# back to none, and playback does not need it. Withholding it also keeps the
# entry free of any Scripts menu step, as its README promises.
IGNORED_FILES = {"DVD_INSTALL.txt", "Scripts/set_dvd_region.sh"}
INSTALLER_PATH = "Scripts/install_dvdcss.sh"
PREPARED_DIRECTORY_ENV = "MISTER_DVD_PREPARED_DIR"
PAYLOAD_REVISION_ENV = "MISTER_DVD_PAYLOAD_REVISION"
SANDBOX_IMAGE = (
    "python:3.12-slim-bookworm@"
    "sha256:4427763a1ba36f5aa8f656a03e5d00f3b8d61f5dd950c73df6c14f8c7640f8ab"
)
SANDBOX_TIMEOUT_SECONDS = 600

# The slim Python image has every utility used by the current installer except a
# downloader. Supplying this small compatibility command avoids building a
# mutable apt-based image. It implements the wget and curl forms used by the
# installer and records successful fetches for source provenance.
FETCH_COMMAND = r'''#!/usr/bin/env python3
import hashlib
import json
import os
import sys
import urllib.parse
import urllib.request


def fail(message):
    print(f"sandbox fetch: {message}", file=sys.stderr)
    raise SystemExit(2)


program = os.path.basename(sys.argv[0])
arguments = sys.argv[1:]
destination = None
urls = []
index = 0
while index < len(arguments):
    argument = arguments[index]
    if argument in {"-O", "--output-document", "-o", "--output"}:
        index += 1
        if index >= len(arguments):
            fail(f"{argument} needs a path")
        destination = arguments[index]
    elif argument.startswith("--output-document="):
        destination = argument.split("=", 1)[1]
    elif argument.startswith("--output="):
        destination = argument.split("=", 1)[1]
    elif argument in {"-q", "--quiet", "-f", "--fail", "-s", "--silent", "-S", "--show-error", "-L", "--location", "-fsSL"}:
        pass
    elif argument == "--":
        urls.extend(arguments[index + 1 :])
        break
    elif argument.startswith("-"):
        fail(f"unsupported {program} option: {argument}")
    else:
        urls.append(argument)
    index += 1

if destination is None or len(urls) != 1:
    fail(f"expected one URL and an output path, got: {arguments!r}")
url = urls[0]
parsed = urllib.parse.urlparse(url)
if parsed.scheme not in {"http", "https"} or not parsed.hostname:
    fail(f"unsupported URL: {url}")

try:
    request = urllib.request.Request(url, headers={"User-Agent": "MiSTer-DVD-sandbox/1"})
    with urllib.request.urlopen(request, timeout=90) as response:
        data = response.read(256 * 1024 * 1024 + 1)
        resolved_url = response.geturl()
    if len(data) > 256 * 1024 * 1024:
        fail(f"download is larger than 256 MiB: {url}")
    with open(destination, "wb") as output:
        output.write(data)
    record = {
        "requested_url": url,
        "resolved_url": resolved_url,
        "sha256": hashlib.sha256(data).hexdigest(),
        "size": len(data),
    }
    encoded = (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode()
    descriptor = os.open(
        os.environ["MISTER_DVD_FETCH_LOG"],
        os.O_WRONLY | os.O_CREAT | os.O_APPEND,
        0o600,
    )
    try:
        os.write(descriptor, encoded)
    finally:
        os.close(descriptor)
except SystemExit:
    raise
except Exception as error:
    print(f"sandbox fetch: {url}: {error}", file=sys.stderr)
    raise SystemExit(1)
'''


class CapturedFile(NamedTuple):
    install_path: str
    data: bytes


class PreparedFile(NamedTuple):
    install_path: str
    asset_path: str
    data: bytes


class PreparedPayload(NamedTuple):
    archive_url: str
    archive_data: bytes
    selected_files: tuple[tuple[str, ArchiveMember], ...]
    installer_url: str
    installer_data: bytes
    asset_root: str
    files: tuple[PreparedFile, ...]
    source_data: bytes
    version: str


def unique_release_asset(
    release: Mapping[str, Any], pattern: re.Pattern[str], description: str
) -> dict[str, Any]:
    matches = []
    for asset in release.get("assets") or []:
        if not isinstance(asset, dict):
            continue
        name = str(asset.get("name") or "")
        url = str(asset.get("browser_download_url") or "")
        if pattern.fullmatch(name) and url.startswith("https://"):
            matches.append(asset)
    if len(matches) != 1:
        tag = release.get("tag_name") or release.get("name") or "unknown"
        raise RuntimeError(
            f"MiSTer DVD release {tag} must contain exactly one {description}; "
            f"found {len(matches)}"
        )
    return matches[0]


def selected_files(
    members: Sequence[ArchiveMember],
) -> tuple[tuple[str, ArchiveMember], ...]:
    selected = []
    core_paths = []
    unexpected = []

    for member in members:
        if CORE_PATTERN.fullmatch(member.path.removeprefix("_Other/")):
            if not member.path.startswith("_Other/"):
                unexpected.append(member.path)
                continue
            core_paths.append(member.path)
            selected.append((member.path, member))
        elif member.path in EXPECTED_FILES:
            if member.path in INSTALLABLE_FILES:
                selected.append((member.path, member))
        elif member.path in IGNORED_FILES:
            continue
        else:
            unexpected.append(member.path)

    if unexpected:
        raise RuntimeError(
            "MiSTer DVD ZIP contains unexpected files: "
            + ", ".join(sorted(unexpected))
        )
    if len(core_paths) != 1:
        raise RuntimeError(
            "MiSTer DVD ZIP must contain exactly one _Other/DVD_YYYYMMDD.rbf"
        )

    names = {member.path for member in members}
    missing = EXPECTED_FILES - names
    if missing:
        raise RuntimeError(
            "MiSTer DVD ZIP is missing required files: "
            + ", ".join(sorted(missing))
        )
    return tuple(sorted(selected, key=lambda item: item[0]))


def capture_installed_files(media_fat: Path) -> tuple[CapturedFile, ...]:
    captured = []
    for directory, directory_names, file_names in os.walk(
        media_fat, followlinks=False
    ):
        current = Path(directory)
        directory_names.sort()
        file_names.sort()
        for name in directory_names:
            path = current / name
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
                relative = path.relative_to(media_fat).as_posix()
                raise RuntimeError(
                    f"Sandbox installer created an unsupported directory: {relative}"
                )
        for name in file_names:
            path = current / name
            relative = path.relative_to(media_fat).as_posix()
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
                raise RuntimeError(
                    f"Sandbox installer created an unsupported file: {relative}"
                )
            if relative == INSTALLER_PATH:
                continue
            captured.append(
                CapturedFile(
                    install_path=normalize_install_path(relative),
                    data=path.read_bytes(),
                )
            )
    if not captured:
        raise RuntimeError("MiSTer DVD installer did not install any files")
    return tuple(sorted(captured, key=lambda item: item.install_path))


def read_fetch_log(audit_directory: Path) -> tuple[dict[str, Any], ...]:
    log_path = audit_directory / "fetches.jsonl"
    if not log_path.exists():
        return ()
    records = []
    try:
        lines = log_path.read_text("utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise RuntimeError("Unable to read sandbox download log") from exc
    for line in lines:
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Sandbox download log is invalid") from exc
        if not isinstance(record, dict) or set(record) != {
            "requested_url",
            "resolved_url",
            "sha256",
            "size",
        }:
            raise RuntimeError("Sandbox download record has unexpected fields")
        for key in ("requested_url", "resolved_url"):
            parsed = urllib.parse.urlparse(str(record[key]))
            if parsed.scheme not in {"http", "https"} or not parsed.hostname:
                raise RuntimeError(f"Sandbox recorded an invalid URL: {record[key]}")
        if not re.fullmatch(r"[0-9a-f]{64}", str(record["sha256"])):
            raise RuntimeError("Sandbox download record has an invalid hash")
        if not isinstance(record["size"], int) or record["size"] < 0:
            raise RuntimeError("Sandbox download record has an invalid size")
        records.append(record)
    return tuple(records)


def run_installer(
    installer_data: bytes,
) -> tuple[tuple[CapturedFile, ...], tuple[dict[str, Any], ...]]:
    with tempfile.TemporaryDirectory(prefix="mister-dvd-sandbox-") as temporary:
        sandbox = Path(temporary)
        media_fat = sandbox / "media" / "fat"
        installer = media_fat / INSTALLER_PATH
        installer.parent.mkdir(parents=True)
        installer.write_bytes(installer_data)
        installer.chmod(0o755)

        fetch_command = sandbox / "fetch"
        fetch_command.write_text(FETCH_COMMAND, encoding="utf-8")
        fetch_command.chmod(0o755)
        audit_directory = sandbox / "audit"
        audit_directory.mkdir()

        container_name = f"mister-dvd-{uuid.uuid4().hex}"
        user = f"{os.getuid()}:{os.getgid()}"
        command = [
            "docker",
            "run",
            "--rm",
            "--name",
            container_name,
            "--platform",
            "linux/amd64",
            "--user",
            user,
            "--read-only",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges",
            "--pids-limit=64",
            "--memory=256m",
            "--cpus=1",
            "--tmpfs",
            "/tmp:rw,nosuid,nodev,noexec,size=64m",
            "--workdir",
            "/media/fat/Scripts",
            "--env",
            "PYTHONDONTWRITEBYTECODE=1",
            "--env",
            "MISTER_DVD_FETCH_LOG=/sandbox/audit/fetches.jsonl",
            "--mount",
            f"type=bind,src={media_fat.resolve()},dst=/media/fat",
            "--mount",
            f"type=bind,src={audit_directory.resolve()},dst=/sandbox/audit",
            "--mount",
            (
                f"type=bind,src={fetch_command.resolve()},"
                "dst=/usr/local/bin/wget,readonly"
            ),
            "--mount",
            (
                f"type=bind,src={fetch_command.resolve()},"
                "dst=/usr/local/bin/curl,readonly"
            ),
            SANDBOX_IMAGE,
            "/bin/bash",
            f"/media/fat/{INSTALLER_PATH}",
        ]
        try:
            subprocess.run(
                command,
                cwd=ROOT,
                check=True,
                timeout=SANDBOX_TIMEOUT_SECONDS,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                "Docker is required to run the MiSTer DVD installer sandbox"
            ) from exc
        except subprocess.TimeoutExpired as exc:
            subprocess.run(
                ["docker", "rm", "--force", container_name],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            raise RuntimeError("MiSTer DVD installer sandbox timed out") from exc
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(
                f"MiSTer DVD installer sandbox failed with exit code {exc.returncode}"
            ) from exc

        return capture_installed_files(media_fat), read_fetch_log(audit_directory)


def source_metadata(
    installer_url: str,
    installer_data: bytes,
    downloads: Sequence[Mapping[str, Any]],
) -> bytes:
    return (
        json.dumps(
            {
                "downloads": list(downloads),
                "installer": installer_url,
                "installer_sha256": hashlib.sha256(installer_data).hexdigest(),
                "sandbox_image": SANDBOX_IMAGE,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def runtime_digest(files: Sequence[CapturedFile], source_data: bytes) -> str:
    digest = hashlib.sha256()
    for item in sorted(files, key=lambda candidate: candidate.install_path):
        for value in (item.install_path.encode("utf-8"), item.data):
            digest.update(len(value).to_bytes(8, "big"))
            digest.update(value)
    digest.update(len(source_data).to_bytes(8, "big"))
    digest.update(source_data)
    return digest.hexdigest()


def prepare_payload() -> PreparedPayload:
    release = github_latest_release(UPSTREAM)
    archive_asset = unique_release_asset(release, ASSET_PATTERN, "versioned ZIP")
    installer_asset = unique_release_asset(
        release, INSTALLER_PATTERN, "install_dvdcss.sh asset"
    )
    archive_url = release_asset_url(archive_asset)
    installer_url = release_asset_url(installer_asset)
    archive_data = http_get_bytes(archive_url)
    installer_data = http_get_bytes(installer_url, accept="text/plain")
    members = read_archive_members(archive_data)
    selected = selected_files(members)

    bundled_installers = [
        member.data for member in members if member.path == INSTALLER_PATH
    ]
    if bundled_installers != [installer_data]:
        raise RuntimeError(
            "The standalone libdvdcss installer differs from the release ZIP copy"
        )

    captured, downloads = run_installer(installer_data)
    metadata = source_metadata(installer_url, installer_data, downloads)
    asset_root = f"{FOLDER}/runtime/{runtime_digest(captured, metadata)}"
    files = tuple(
        PreparedFile(
            install_path=item.install_path,
            asset_path=f"{asset_root}/{item.install_path}",
            data=item.data,
        )
        for item in captured
    )
    version_match = ASSET_PATTERN.fullmatch(str(archive_asset["name"]))
    if version_match is None:
        raise AssertionError("validated MiSTer DVD asset no longer matches")

    return PreparedPayload(
        archive_url=archive_url,
        archive_data=archive_data,
        selected_files=selected,
        installer_url=installer_url,
        installer_data=installer_data,
        asset_root=asset_root,
        files=files,
        source_data=metadata,
        version=version_match.group(1),
    )


def write_prepared_payload(payload: PreparedPayload, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=False)
    asset_directory = output / "files" / payload.asset_root
    metadata_directory = asset_directory / ".metadata"
    metadata_directory.mkdir(parents=True)

    manifest_files = []
    for item in payload.files:
        target = output / "files" / item.asset_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(item.data)
        manifest_files.append(
            {
                "asset_path": item.asset_path,
                "install_path": item.install_path,
            }
        )

    (metadata_directory / "source.json").write_bytes(payload.source_data)
    (output / "release.zip").write_bytes(payload.archive_data)
    (output / "install_dvdcss.sh").write_bytes(payload.installer_data)
    manifest_files.sort(key=lambda item: item["install_path"])
    manifest = {
        "archive_url": payload.archive_url,
        "asset_root": payload.asset_root,
        "files": manifest_files,
        "installer_url": payload.installer_url,
        "marker_path": manifest_files[0]["asset_path"],
        "source_sha256": hashlib.sha256(payload.source_data).hexdigest(),
        "version": payload.version,
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def validate_source_metadata(
    source_data: bytes, installer_url: str, installer_data: bytes
) -> None:
    try:
        source = json.loads(source_data)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Prepared runtime source metadata is invalid") from exc
    if not isinstance(source, dict) or set(source) != {
        "downloads",
        "installer",
        "installer_sha256",
        "sandbox_image",
    }:
        raise RuntimeError("Prepared runtime source metadata has unexpected fields")
    if source["installer"] != installer_url:
        raise RuntimeError("Prepared runtime source has the wrong installer")
    if source["installer_sha256"] != hashlib.sha256(installer_data).hexdigest():
        raise RuntimeError("Prepared runtime source has the wrong installer hash")
    if source["sandbox_image"] != SANDBOX_IMAGE:
        raise RuntimeError("Prepared runtime source has the wrong sandbox image")
    downloads = source["downloads"]
    if not isinstance(downloads, list):
        raise RuntimeError("Prepared runtime source downloads are not a list")
    for record in downloads:
        if not isinstance(record, dict) or set(record) != {
            "requested_url",
            "resolved_url",
            "sha256",
            "size",
        }:
            raise RuntimeError("Prepared runtime source download is invalid")
        for key in ("requested_url", "resolved_url"):
            parsed = urllib.parse.urlparse(str(record[key]))
            if parsed.scheme not in {"http", "https"} or not parsed.hostname:
                raise RuntimeError("Prepared runtime source contains an invalid URL")
        if not re.fullmatch(r"[0-9a-f]{64}", str(record["sha256"])):
            raise RuntimeError("Prepared runtime source contains an invalid hash")
        if not isinstance(record["size"], int) or record["size"] < 0:
            raise RuntimeError("Prepared runtime source contains an invalid size")


def read_prepared_payload(directory: Path) -> PreparedPayload:
    try:
        manifest = json.loads((directory / "manifest.json").read_text("utf-8"))
        archive_data = (directory / "release.zip").read_bytes()
        installer_data = (directory / "install_dvdcss.sh").read_bytes()
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            f"Unable to read prepared MiSTer DVD payload: {directory}"
        ) from exc
    if not isinstance(manifest, dict):
        raise RuntimeError("Prepared MiSTer DVD manifest is not an object")

    asset_root = str(manifest.get("asset_root") or "")
    root_match = re.fullmatch(
        rf"{re.escape(FOLDER)}/runtime/([0-9a-f]{{64}})", asset_root
    )
    if root_match is None:
        raise RuntimeError(f"Invalid prepared runtime asset root: {asset_root}")
    manifest_files = manifest.get("files")
    if not isinstance(manifest_files, list) or not manifest_files:
        raise RuntimeError("Prepared runtime manifest has no files")

    members = read_archive_members(archive_data)
    selected = selected_files(members)
    bundled_installers = [
        member.data for member in members if member.path == INSTALLER_PATH
    ]
    if bundled_installers != [installer_data]:
        raise RuntimeError("Prepared installer differs from its release ZIP copy")

    installer_url = str(manifest.get("installer_url") or "")
    source_path = directory / "files" / asset_root / ".metadata/source.json"
    try:
        source_data = source_path.read_bytes()
    except OSError as exc:
        raise RuntimeError(f"Prepared runtime asset is incomplete: {asset_root}") from exc
    if manifest.get("source_sha256") != hashlib.sha256(source_data).hexdigest():
        raise RuntimeError("Prepared runtime source metadata does not match its hash")
    validate_source_metadata(source_data, installer_url, installer_data)

    files = []
    seen_install_paths = set()
    try:
        for item in manifest_files:
            if not isinstance(item, dict) or set(item) != {
                "asset_path",
                "install_path",
            }:
                raise RuntimeError("Prepared runtime file is invalid")
            install_path = normalize_install_path(str(item["install_path"]))
            if install_path == INSTALLER_PATH:
                raise RuntimeError("Prepared runtime includes the seeded installer")
            if install_path in seen_install_paths:
                raise RuntimeError(
                    f"Duplicate prepared runtime destination: {install_path}"
                )
            seen_install_paths.add(install_path)
            asset_path = str(item["asset_path"])
            if asset_path != f"{asset_root}/{install_path}":
                raise RuntimeError(
                    f"Prepared runtime asset has the wrong path: {asset_path}"
                )
            data = (directory / "files" / asset_path).read_bytes()
            files.append(
                PreparedFile(
                    install_path=install_path,
                    asset_path=asset_path,
                    data=data,
                )
            )
    except OSError as exc:
        raise RuntimeError(f"Prepared runtime asset is incomplete: {asset_root}") from exc

    captured = tuple(
        CapturedFile(install_path=item.install_path, data=item.data)
        for item in files
    )
    if runtime_digest(captured, source_data) != root_match.group(1):
        raise RuntimeError("Prepared runtime bundle does not match its content hash")

    sorted_files = tuple(sorted(files, key=lambda item: item.install_path))
    if manifest.get("marker_path") != sorted_files[0].asset_path:
        raise RuntimeError("Prepared runtime marker path is invalid")
    archive_url = str(manifest.get("archive_url") or "")
    version = str(manifest.get("version") or "")
    if not ASSET_PATTERN.fullmatch(f"MiSTer_DVD_{version}.zip"):
        raise RuntimeError(f"Invalid prepared MiSTer DVD version: {version}")
    if not archive_url.startswith("https://github.com/"):
        raise RuntimeError(f"Invalid prepared release URL: {archive_url}")
    if not installer_url.startswith("https://github.com/"):
        raise RuntimeError(f"Invalid prepared installer URL: {installer_url}")

    expected_files = {item.install_path for item in files}.union(
        {".metadata/source.json"}
    )
    asset_directory = directory / "files" / asset_root
    actual_files = {
        path.relative_to(asset_directory).as_posix()
        for path in asset_directory.rglob("*")
        if path.is_file()
    }
    if actual_files != expected_files:
        raise RuntimeError(
            "Prepared runtime bundle has unexpected files: "
            + ", ".join(sorted(actual_files ^ expected_files))
        )

    return PreparedPayload(
        archive_url=archive_url,
        archive_data=archive_data,
        selected_files=selected,
        installer_url=installer_url,
        installer_data=installer_data,
        asset_root=asset_root,
        files=sorted_files,
        source_data=source_data,
        version=version,
    )


def main() -> int:
    parser = generator_parser(FOLDER, "Generate the MiSTer DVD database")
    parser.add_argument(
        "--prepare-payload",
        type=Path,
        default=None,
        help="Run the installer sandbox and prepare its files for publication",
    )
    args = parser.parse_args()

    if args.prepare_payload is not None:
        write_prepared_payload(prepare_payload(), args.prepare_payload)
        print(f"Prepared MiSTer DVD payload in {args.prepare_payload}", flush=True)
        return 0

    prepared_directory = os.getenv(PREPARED_DIRECTORY_ENV, "").strip()
    payload = (
        read_prepared_payload(Path(prepared_directory))
        if prepared_directory
        else prepare_payload()
    )
    payload_revision = os.getenv(PAYLOAD_REVISION_ENV, "").strip()
    if not payload_revision:
        payload_revision = github_commit_sha(args.repository, PAYLOAD_BRANCH)
    direct_files = []
    for item in payload.files:
        payload_url = github_raw_url(
            args.repository, payload_revision, item.asset_path
        )
        if http_get_bytes(payload_url) != item.data:
            raise RuntimeError(
                f"Published runtime file differs from prepared data: {payload_url}"
            )
        direct_files.append(
            DirectFile(
                path=item.install_path,
                url=payload_url,
                data=item.data,
            )
        )

    database = build_selective_archive_database(
        folder=FOLDER,
        repository=args.repository,
        timestamp=generation_timestamp(args.timestamp),
        archive_url=payload.archive_url,
        archive_data=payload.archive_data,
        selected_files=payload.selected_files,
        direct_files=tuple(direct_files),
        description=f"Installing MiSTer DVD {payload.version}",
        filter_terms=(FOLDER, "other", "dvdcss"),
        tag_aliases=((FOLDER, "dvd"),),
    )
    write_bundle(database, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
