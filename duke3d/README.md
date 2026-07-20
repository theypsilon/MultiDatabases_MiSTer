# MiSTer Duke3D database

- Database ID:
  [`MultiDatabases/duke3d`](https://theypsilon.github.io/DB-Inspector_MiSTer/?database-url=https%3A%2F%2Fraw.githubusercontent.com%2Ftheypsilon%2FMultiDatabases_MiSTer%2Fdb%2Fduke3d%2Fdb.json)
- Upstream: [`neofreno/Mister_Duke3d`](https://github.com/neofreno/Mister_Duke3d)
- Database URL:
  `https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/duke3d/db.json`

MiSTer Duke3D is a hybrid FPGA/ARM port rather than a standalone FPGA core.
The generator follows the latest GitHub release asset named
`Mister_duke3d_YYYYMMDD.zip`. It installs the launcher, RBF, runtime, libraries,
and other files published in that ZIP.

## Installation

Download
[`downloader_MultiDatabases_duke3d.zip`](https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/duke3d/downloader_MultiDatabases_duke3d.zip),
extract it to `/media/fat` on the MiSTer SD card, and run the MiSTer updaters.

Add these sections to `/media/fat/MiSTer.ini`:

```ini
[DUKE3D]
main=Mister_duke3d
vga_scaler=0

[Mister_duke3d]
main=Mister_duke3d
vga_scaler=0
```

Copy your own `DUKE3D.GRP` game data file to
`/media/fat/games/DUKE3D/duke3d.grp`. The database does not include it.
