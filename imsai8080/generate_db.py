#!/usr/bin/env python3
"""Opt-in IMSAI prototype database; only reviewed MiSTer packages are eligible."""
from __future__ import annotations

import hashlib
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.github'))
from db_helpers import (build_selective_archive_database, generation_timestamp,
    generator_parser, github_releases, http_get_bytes, read_archive_members,
    validate_database, write_bundle)

FOLDER = 'imsai8080'
UPSTREAM = 'toby01019/IMSAI8080-MiSTer'
# Deliberate prerelease exception: this is an explicitly enabled prototype,
# not a claim of acceptance into MiSTer-devel or the default distribution.
REVIEWED_PRERELEASES = {'mister-downloader-20261028', 'mister-downloader-20261028-games'}
# Reviewed legacy packages depend on a pre-existing manual installation and are
# not standalone update-channel payloads. Never select them as a fallback.
LEGACY_UPDATE_TAGS = {'prototype-20261001', 'prototype-20261023-frontpanel'}
TAG = re.compile(r'mister-downloader-(\d{8})(-games)?')
CORE = '_Computer/IMSAI8080_Downloader.rbf'
LAUNCHER = '_Computer/IMSAI8080 - Terminal (Updater).mgl'
DEMO = 'games/IMSAI8080/Examples/terminal-demo.bin'
DOCS = 'docs/IMSAI8080/Downloader/'
REQUIRED = {CORE, LAUNCHER, DEMO, DOCS + 'README.txt',
            DOCS + 'CREDITS.txt', DOCS + 'LICENSE-MIT.txt',
            DOCS + 'LICENSE-MiSTer-GPL-2.0.txt', DOCS + 'CPU-NOTICE.txt'}


PROGRAMS = {
    'Super Star Trek': ('superstartrek-basic40.bin', '0'),
    'BASIC 4.0': ('basic8k40-mister.bin', '0'),
    'Tiny BASIC': ('tinybasic-v3-mister.bin', '0'),
    'Kill the Lights': ('kill-the-lights.bin', '1'),
    'Switch test': ('switch-mirror.bin', '0'),
    'Complement test': ('switch-complement.bin', '0'),
}
GAME_DOCS = {'SUPER_STAR_TREK.md', 'KILL_THE_LIGHTS.md', 'TINY_BASIC.md',
    'SOURCES_AND_LICENSING.md', 'SUPER-STAR-TREK-LICENSE.txt', 'TREKHISTORY.txt',
    'basic40-source.json', 'superstartrek.bas', 'images/super-star-trek-srs.png',
    'images/super-star-trek-lrs.png'}
GAME_LAUNCHERS = {
    f'_Computer/IMSAI8080 - {title} (Updater).mgl':
    ('games/IMSAI8080/Programs/' + filename, index)
    for title, (filename, index) in PROGRAMS.items()}
GAME_REQUIRED = REQUIRED | set(GAME_LAUNCHERS) | {
    program for program, _ in GAME_LAUNCHERS.values()} | {DOCS + p for p in GAME_DOCS}


def select_release(releases):
    candidates = []
    for release in releases:
        tag = str(release.get('tag_name') or '')
        match = TAG.fullmatch(tag)
        if release.get('draft'):
            continue
        if release.get('prerelease') and tag not in REVIEWED_PRERELEASES:
            continue
        if not match:
            payloads = [str(a.get('name', '')).lower() for a in release.get('assets', [])]
            has_mister = any(n.endswith('.rbf') or
                (n.startswith('imsai8080-mister-') and n.endswith('.zip')) for n in payloads)
            if has_mister and tag not in LEGACY_UPDATE_TAGS:
                raise RuntimeError('Unrecognized MiSTer release family; review upstream packaging')
            continue  # MEGA65, source-only releases, reviewed legacy packages.
        candidates.append((match.group(1) + (match.group(2) or ''), release))
    if not candidates:
        raise RuntimeError('No published eligible standalone MiSTer package; publish upstream first')
    candidates.sort(key=lambda item: item[0], reverse=True)
    release = candidates[0][1]
    date = release['tag_name'].removeprefix('mister-downloader-')
    name = f'IMSAI8080-MiSTer-Downloader-{date}.zip'
    assets = [a for a in release.get('assets', []) if a.get('name') == name]
    if len(assets) != 1:
        raise RuntimeError(f'Newest eligible release must have exactly one {name}')
    asset = assets[0]
    expected = f'https://github.com/{UPSTREAM}/releases/download/{release["tag_name"]}/{name}'
    if asset.get('browser_download_url') != expected:
        raise RuntimeError('Asset does not belong to the configured upstream/tag')
    return release, asset


def build_database(asset, data, repository, timestamp):
    if asset.get('size') != len(data):
        raise RuntimeError('Release asset size mismatch')
    digest = asset.get('digest')
    if not digest or digest != 'sha256:' + hashlib.sha256(data).hexdigest():
        raise RuntimeError('Release asset SHA256 mismatch or missing digest')
    members = read_archive_members(data)
    by_path = {m.path: m for m in members}
    required = GAME_REQUIRED if asset['name'].endswith('-games.zip') else REQUIRED
    expected = {'SD/' + path for path in required} | {'manifest.json'}
    if set(by_path) != expected:
        raise RuntimeError('Unexpected/missing archive files; review package layout')
    core = by_path['SD/' + CORE].data
    if len(core) < 1_000_000:
        raise RuntimeError('Invalid/truncated MiSTer core')
    launchers = {LAUNCHER: (DEMO, '0')}
    if required == GAME_REQUIRED:
        launchers.update(GAME_LAUNCHERS)
    for launcher, (program, index) in launchers.items():
        if not 1 <= len(by_path['SD/' + program].data) <= 65536:
            raise RuntimeError('Program exceeds 8080 memory')
        mgl = ET.fromstring(by_path['SD/' + launcher].data)
        if mgl.tag != 'mistergamedescription' or mgl.findtext('rbf') != CORE[:-4]:
            raise RuntimeError('Launcher/core mismatch')
        files = mgl.findall('file')
        if (len(files) != 1 or files[0].get('path') != '/media/fat/' + program
                or files[0].get('index') != index or files[0].get('type') != 'f'):
            raise RuntimeError('Launcher/program mismatch')
        setname = mgl.find('setname')
        if setname is None or setname.text != 'IMSAI8080_Downloader' or setname.get('same_dir') != '1':
            raise RuntimeError('Launcher must preserve updater configuration identity')
    db = build_selective_archive_database(
        folder=FOLDER, repository=repository, timestamp=timestamp,
        archive_url=asset['browser_download_url'], archive_data=data,
        selected_files=[(path, by_path['SD/' + path]) for path in sorted(required)],
        description='IMSAI 8080 prototype and included programs',
        filter_terms=(FOLDER, 'computer'), tag_aliases=((FOLDER, 'imsai'),))
    summary = db['archives']['release']['summary_inline']['files']
    # User-modified examples are deliberately retained, including on updates.
    for program, _ in launchers.values():
        summary[program]['overwrite'] = False
    validate_database(db)
    return db


def main():
    args = generator_parser(FOLDER, 'Generate the IMSAI 8080 prototype database').parse_args()
    _, asset = select_release(github_releases(UPSTREAM))
    data = http_get_bytes(asset['browser_download_url'])
    database = build_database(asset, data, args.repository, generation_timestamp(args.timestamp))
    write_bundle(database, args.output)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
