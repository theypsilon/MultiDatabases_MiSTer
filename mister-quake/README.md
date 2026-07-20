# MiSTer Quake database

- Database ID:
  [`MultiDatabases/mister-quake`](https://theypsilon.github.io/DB-Inspector_MiSTer/?database-url=https%3A%2F%2Fraw.githubusercontent.com%2Ftheypsilon%2FMultiDatabases_MiSTer%2Fdb%2Fmister-quake%2Fdb.json)
- Upstream: [`neofreno/Mister_Quake`](https://github.com/neofreno/Mister_Quake)
- Database URL:
  `https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/mister-quake/db.json`

The generator follows the latest GitHub release asset named
`MiSTer_Quake_YYYYMMDD.zip`. It installs the launcher, RBF, runtime, libraries,
and other files published in that ZIP.

## Installation

Download
[`downloader_MultiDatabases_mister-quake.zip`](https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/mister-quake/downloader_MultiDatabases_mister-quake.zip),
extract it to `/media/fat` on the MiSTer SD card, and run the MiSTer updaters.

Add these sections to `/media/fat/MiSTer.ini`:

```ini
[Quake]
main=MiSTer_Quake
vga_scaler=0

[MiSTer_Quake]
main=MiSTer_Quake
vga_scaler=0
```

Copy your own Quake data files to `/media/fat/games/quake/id1/`:

- `PAK0.PAK` is required.
- `PAK1.PAK` is optional.

The database does not include either file.
