#!/usr/bin/env python3

from __future__ import annotations

import sys
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".github"))

from db_helpers import (  # noqa: E402
    ArchiveMember,
    ScriptsApp,
    SelectiveArchive,
    build_multi_selective_archive_database,
    compatible_release_zip,
    generation_timestamp,
    generator_parser,
    github_latest_release,
    read_scripts_app,
    release_tag,
    shell_variable,
    write_bundle,
)


FOLDER = "mister-hifi"
NAME = "MiSTer Hi-Fi"
UPSTREAM = "Anime0t4ku/MiSTer_Hi-Fi"
ARCHIVE_ID = "release"
# MiSTer Hi-Fi writes these itself: config.json holds the user's settings and
# smb.json their share credentials. The release only ships smb.example.json,
# and a release that started packing the real files would overwrite them on
# every downloader run.
USER_OWNED = ("config.json", "smb.json")


def read_app(members: Sequence[ArchiveMember]) -> ScriptsApp:
    app = read_scripts_app(members, name=NAME, user_owned=USER_OWNED)
    version = shell_variable(app.launcher.data.decode("utf-8", "replace"), "VERSION")
    print(f"{NAME} launcher declares version {version}", flush=True)
    return app


def main() -> int:
    args = generator_parser(FOLDER, f"Generate the {NAME} database").parse_args()
    release = github_latest_release(UPSTREAM)
    tag = release_tag(release)
    url, data, app = compatible_release_zip(
        release, accept=read_app, context=f"{UPSTREAM} release {tag}"
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
                selected_files=app.files,
                description=f"Installing {NAME} {tag}",
            ),
        ),
        filter_terms=(FOLDER, "utility"),
        tag_aliases=((FOLDER, "hifi"),),
    )
    write_bundle(database, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
