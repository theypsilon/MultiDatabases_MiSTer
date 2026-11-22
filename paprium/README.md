# Paprium MegaDrive database

- Database ID:
  [`MultiDatabases/paprium`](https://theypsilon.github.io/DB-Inspector_MiSTer/?database-url=https%3A%2F%2Fraw.githubusercontent.com%2Ftheypsilon%2FMultiDatabases_MiSTer%2Fdb%2Fpaprium%2Fdb.json)
- Upstream:
  [`thekoalakoa/Paprium_MiSTer`](https://github.com/thekoalakoa/Paprium_MiSTer)
- Database URL:
  `https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/paprium/db.json`

The generator follows the latest published upstream release and requires its
`Paprium_MiSTer_<version>.zip` bundle. Out of that bundle it installs the core
as `_Custom Cores/Cores/Paprium.rbf` and the Little-Man firmware the core loads
as `games/PapriumMD/little_man_firmware.bin`, and it adds `PapriumMD.mgl` to
`_Custom Cores`. Core changes are marked as requiring a reboot. The launcher is
maintained in this folder and served from the repository's `main` branch.

## Upstream retired, and the project moved

This database originally followed
[`MisterPezz82/Paprium_MegaDrive_MiSTer`](https://github.com/MisterPezz82/Paprium_MegaDrive_MiSTer)
and installed the newest dated `MegaDrive_Paprium_YYYYMMDD.rbf` asset of its
latest release, up to `V.08`. On 2026-11-11 that repository published a release
named *Retired: Paprium for MiSTer is now thekoalakoa's Paprium_MiSTer*, with no
assets, and archived itself read-only. The handover was reviewed and accepted on
pull request #22, so this database now follows
[`thekoalakoa/Paprium_MiSTer`](https://github.com/thekoalakoa/Paprium_MiSTer).

The core file changed with it. The installed core moved from
`_Custom Cores/Cores/MegaDrive_Paprium_<date>.rbf` to
`_Custom Cores/Cores/Paprium.rbf`, and the next Downloader run installs the new
file and removes the old one.

The launcher keeps its `PapriumMD.mgl` name and its `PapriumMD` setname, so the
menu entry stays where it was and the ROM folder, saves and core settings
existing users already have are still picked up. Only the core it launches
changed. Upstream's own `Paprium.mgl` is deliberately not installed: it loads a
ROM from `games/Paprium/Paprium/`, which is not where this database has users
keep theirs.

## Installation

Download
[`downloader_MultiDatabases_paprium.zip`](https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/paprium/downloader_MultiDatabases_paprium.zip),
extract it to `/media/fat` on the MiSTer SD card, and run the MiSTer updaters.

No `MiSTer.ini` changes are required.

Place your own compatible Paprium ROM image in `/media/fat/games/PapriumMD/`.
The database provides the core, the launcher and the Little-Man firmware; it
does not include the ROM. Load that firmware from the core's OSD before loading
your ROM, the order upstream's own launcher uses — it is installed in the same
folder the core's file browser opens, next to your ROM. The `paprium.cue`
CD-audio and PCM launchers the previous core shipped are not part of this
release.
