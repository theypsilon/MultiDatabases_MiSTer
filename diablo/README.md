# Diablo database

- Database ID:
  [`MultiDatabases/diablo`](https://theypsilon.github.io/DB-Inspector_MiSTer/?database-url=https%3A%2F%2Fraw.githubusercontent.com%2Ftheypsilon%2FMultiDatabases_MiSTer%2Fdb%2Fdiablo%2Fdb.json.zip)
- Upstream: [`meathax/dbdiablo`](https://github.com/meathax/dbdiablo)
  (Downloader database); source at
  [`meathax/diablo`](https://github.com/meathax/diablo)
- Database URL:
  `https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/diablo/db.json.zip`

Diablo and Hellfire for MiSTer is a hybrid FPGA/ARM port built on the
DevilutionX engine rather than a standalone FPGA core. The generator follows
upstream's Downloader database and forwards a reviewed slice of it, at the
upstream paths:

- `_Other/Diablo.rbf` and `_Other/Hellfire.rbf`, the FPGA cores.
- `_Other/Diablo/`, the runtime package: the ARM DevilutionX engine, the Python
  launcher, its manifests, the redistributable engine assets, and the licence
  notices.
- `games/Diablo/`, the redistributable data archives: the DevilutionX
  translation and font archives, the Spanish, Polish and Russian language
  archives, and the Diablo shareware archive `spawn.mpq`.

Nothing else upstream publishes is forwarded, and every forwarded file must be
served from upstream's own pinned commit. In particular:

- The retail Diablo and Hellfire archives (`DIABDAT.MPQ`, `hellfire.mpq`,
  `hfmonk.mpq`, `hfmusic.mpq`, `hfvoice.mpq`) are never forwarded. Upstream
  fetches them from archive.org; here they are commercial game data that you
  supply yourself.
- Upstream's `Diablo` file at the root of the SD card, its fork of the MiSTer
  main frontend that starts the engine when a core is selected, is outside the
  forwarded paths and is not installed by this database.

## Installation

Download
[`downloader_MultiDatabases_diablo.zip`](https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/diablo/downloader_MultiDatabases_diablo.zip),
extract it to `/media/fat` on the MiSTer SD card, and run the MiSTer updaters.

Copy the data archives from your own legally obtained Diablo and Hellfire
installations to `/media/fat/games/Diablo/`:

- `DIABDAT.MPQ` from Diablo, for the full base game. Without it the port runs
  the shareware portion from the installed `spawn.mpq`.
- `hellfire.mpq`, `hfmonk.mpq`, `hfmusic.mpq`, and `hfvoice.mpq` from Hellfire,
  for the expansion.

Configuration and saved games are kept in `/media/fat/config/Diablo/` and
`/media/fat/saves/Diablo/`. No BIOS file is required.

This database requires no `MiSTer.ini` change by itself. Launching the game
also needs upstream's `Diablo` main frontend at `/media/fat/Diablo`, which
this database does not install; see the
[upstream README](https://github.com/meathax/dbdiablo#readme) for it and for
its `MiSTer.ini` setup. Upstream's `_Other/Diablo/Diablo.sh` and `Hellfire.sh`
are installed with the runtime package; copying them to `/media/fat/Scripts/`
adds Scripts-menu entries that start each campaign, as described in the
installed `_Other/Diablo/SETUP.md`.

The FPGA cores are installed at `/media/fat/_Other/Diablo.rbf` and
`/media/fat/_Other/Hellfire.rbf`. The FPGA core is GPL-licensed and the engine
is distributed under the DevilutionX Sustainable Use License; see the
installed `_Other/Diablo/NOTICE.txt`, `LICENSE.fpga`, `LICENSE.engine.md`, and
`licenses/` for the full terms.
