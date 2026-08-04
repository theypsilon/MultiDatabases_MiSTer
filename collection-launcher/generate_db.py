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


FOLDER = "collection-launcher"
NAME = "CollectionLauncher"
UPSTREAM = "Anime0t4ku/MiSTer-CollectionLauncher"
ARCHIVE_ID = "release"
COLLECTIONS = "Collections"
# The user's own collections live in Collections, and the launcher writes its
# log into tmp. The release ships both as empty folders; a release that started
# packing files there would overwrite user data on every downloader run.
USER_OWNED = (f"{COLLECTIONS}/", "tmp/")


def read_app(members: Sequence[ArchiveMember]) -> ScriptsApp:
    app = read_scripts_app(members, name=NAME, user_owned=USER_OWNED)
    version = shell_variable(app.launcher.data.decode("utf-8", "replace"), "VERSION")
    print(f"{NAME} launcher declares version {version}", flush=True)
    return app


def extra_folders(app: ScriptsApp) -> tuple[str, ...]:
    """The ZIP carries Collections as an empty folder, so the database declares
    it: it is where the user drops the collections the launcher lists."""
    return (f"{app.folder}/{COLLECTIONS}",)


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
        tag_aliases=((FOLDER, "collections"),),
        extra_folders=extra_folders(app),
    )
    write_bundle(database, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
