# IMSAI 8080 prototype database

- Proposed database ID:
  [`MultiDatabases/imsai8080`](https://theypsilon.github.io/DB-Inspector_MiSTer/?database-url=https%3A%2F%2Fraw.githubusercontent.com%2Ftheypsilon%2FMultiDatabases_MiSTer%2Fdb%2Fimsai8080%2Fdb.json)
- Upstream: [`toby01019/IMSAI8080-MiSTer`](https://github.com/toby01019/IMSAI8080-MiSTer)
- Proposed stable database URL:
  `https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/imsai8080/db.json`

**Submission candidate: these database/drop-in URLs are not published yet.**
Do not distribute the preview drop-in as an operational installer before this
entry is merged and its database is published.

Experimental FPGA implementation with an 8080 CPU, green terminal and virtual
LED/switch panel. This is not hybrid FPGA/ARM emulation. F7 switches between the
combined terminal/panel and enlarged panel views. It remains a prototype;
STEP/POWER are display-only and historical peripheral compatibility is limited.

The generator follows the newest eligible `mister-downloader-YYYYMMDD[-games]` release,
requires exactly one `IMSAI8080-MiSTer-Downloader-YYYYMMDD[-games].zip`, verifies its
GitHub SHA256 and exact supported layout, then installs only its SD payload.
Other release families in the same repository (including MEGA65) are ignored.
Drafts and ordinary prereleases are skipped. The prereleases
`mister-downloader-20261028` and `mister-downloader-20261028-games` are explicit
**proposed prerelease exceptions for maintainer review** for this explicitly enabled prototype. The upstream package is published at the matching release tag. A newer eligible release with a
missing or changed payload fails instead of silently retaining a stale build.

## Installed files and existing installations

- `_Computer/IMSAI8080_Downloader.rbf`
- `_Computer/IMSAI8080 - Terminal (Updater).mgl`
- `games/IMSAI8080/Examples/terminal-demo.bin` (install only if absent)
- Six additional program launchers and BIN files under `games/IMSAI8080/Programs/`.
- Guides, credits, licenses, original Star Trek listing and screenshots under `docs/IMSAI8080/Downloader/`.

The fixed updater-specific core/launcher and `IMSAI8080_Downloader` setname avoid
renaming existing dated cores or reusing their configurations. Every bundled BIN program has
`overwrite: false`, so updates retain customized copies. No saves, user programs,
existing launchers or configuration files are database-owned. Core, launcher and
managed documentation are updated normally. Keep personal files outside managed
paths. No reboot is required. Removing the database through an updater may remove
the files it owns; this preservation policy is for normal updates, not uninstall.

## Installation after maintainer publication

Download
[`downloader_MultiDatabases_imsai8080.zip`](https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/imsai8080/downloader_MultiDatabases_imsai8080.zip),
extract it to `/media/fat` on the MiSTer SD card, and run `update` or `update_all`.
Start **Computer → IMSAI8080 - Terminal (Updater)** and type a line plus Enter.
Use F7 to enlarge/restore the panel and F12 for the core menu.

No BIOS files, extra SDRAM module or `MiSTer.ini` changes are required. The bundled
MIT-licensed project terminal demo is enough to use this installation. Other
compatible 8080 BIN programs (maximum 64 KiB) can be loaded at 0000 through F12;
terminal programs must match the implemented custom ports 10h/11h. Historical
BASIC 4.0, Tiny BASIC, Super Star Trek, Kill the Lights and two switch tests
are included in the games package, retaining their own provenance and rights.
No open redistribution license for the historical Microsoft/MITS runtime has
been established; see the included SOURCES_AND_LICENSING.md. This is not a universal 8080 software loader.

## Source, testing and licensing

The payload reuses the MiSTer FPGA build dated 23 October 2026, without changing
its bytes. That build has hardware checks recorded upstream. The new launcher/package passed a real MiSTer smoke test on 28 October 2026:
terminal echo and F7 enlarged view/return with terminal contents preserved.
This was an additive installation, not a blank-SD test.
Local tests exercise the unmodified official Windows PC Downloader with fixture
transport: clean install, real payload update preserving a modified example and
old files, and failed archive update retaining the working core. The official downloader_test.py also passed under Linux against the published
HTTPS release on 28 October 2026 (exit 0, no errors).

Corresponding HDL/project sources and component notices are available in the
matching release's `Sources.zip`. Project-specific code/demo is MIT; MiSTer glue
is GPL-2.0-or-later and vm80a is CC BY 3.0; framework files retain their notices.
There is no blanket MIT claim for the combined core. Development was AI-assisted
and the virtual-panel background is AI-generated, as disclosed upstream.
