# NBlood database

- Database ID:
  [`MultiDatabases/nblood`](https://theypsilon.github.io/DB-Inspector_MiSTer/?database-url=https%3A%2F%2Fraw.githubusercontent.com%2Ftheypsilon%2FMultiDatabases_MiSTer%2Fdb%2Fnblood%2Fdb.json)
- Upstream: [`meathax/blood`](https://github.com/meathax/blood)
- Database URL:
  `https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/nblood/db.json`

NBlood is a hybrid FPGA/ARM port rather than a standalone FPGA core. The
generator follows upstream's Downloader database and installs the launcher,
RBF, and ARM game engine.

## Installation

Download
[`downloader_MultiDatabases_nblood.zip`](https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/nblood/downloader_MultiDatabases_nblood.zip),
extract it to `/media/fat` on the MiSTer SD card, and run the MiSTer updaters.

Add these sections to `/media/fat/MiSTer.ini`:

```ini
[NBlood]
main=Mister_NBlood

[Mister_NBlood]
main=Mister_NBlood
```

Copy your own **Blood: Fresh Supply** data to `/media/fat/games/NBlood/`.
Copy everything at the top level of the game installation plus its `movie/`
folder, including `BLOOD.RFF`, `blood.ini`, `sounds.rff`, `tiles*.art`, and
`blood0*.ogg`.

For Cryptic Passage, copy the contents of `addons/Cryptic Passage/` into that
same folder without retaining the addon subfolder. Copy its patched
`tiles007.ART` and `tiles015.ART` last so they replace the base versions.

The database does not include the game data, and no BIOS file is required.
The RBF launch entry point is installed at `/media/fat/_Other/NBlood.rbf`.
Reboot, or rescan the menu, and launch **NBlood** from MiSTer's `_Other` menu.
