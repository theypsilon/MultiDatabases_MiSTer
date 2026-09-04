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

Copy these required files from your own **Blood: Fresh Supply** installation
to `/media/fat/games/NBlood/`:

- `BLOOD.INI`
- `BLOOD.RFF`
- `GUI.RFF`
- `SOUNDS.RFF`
- `SURFACE.DAT`
- `VOXEL.DAT`
- `TILES000.ART` through `TILES017.ART`

The following game data is optional:

- Copy the `movie/` folder alongside the required files to include cutscenes.
- Copy `BLOOD000.DEM` through `BLOOD003.DEM` to include the original demos.
- For Cryptic Passage, copy the contents of `addons/Cryptic Passage/` alongside
  the required files without retaining the addon subfolder. Copy its patched
  `tiles007.ART` and `tiles015.ART` last so they replace the base versions.

CD-audio files such as `bloodXX.ogg` or `bloodXX.flac` are not required by this
MiSTer port. Music uses its hardware OPL3 emulation.

The database does not include the game data, and no BIOS file is required.
The RBF launch entry point is installed at `/media/fat/_Other/NBlood.rbf`.
Reboot, or rescan the menu, and launch **NBlood** from MiSTer's `_Other` menu.
