# Sonic Mania MiSTer database

- Database ID:
  [`MultiDatabases/sonic-mania`](https://theypsilon.github.io/DB-Inspector_MiSTer/?database-url=https%3A%2F%2Fraw.githubusercontent.com%2Ftheypsilon%2FMultiDatabases_MiSTer%2Fdb%2Fsonic-mania%2Fdb.json)
- Upstream:
  [`kimchiman52/sonic-mania-mister`](https://github.com/kimchiman52/sonic-mania-mister)
- Database URL:
  `https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/sonic-mania/db.json`

Sonic Mania MiSTer is a hybrid FPGA/ARM port rather than a standalone FPGA
core. The generator follows the latest GitHub release ZIP and selectively maps
its launcher, `_Other` files, and `games/sonic-mania` runtime into their MiSTer
locations. README/license files and any bundled `Data.rsdk` placeholder are
excluded.

## Installation

Download
[`downloader_MultiDatabases_sonic-mania.zip`](https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/sonic-mania/downloader_MultiDatabases_sonic-mania.zip),
extract it to `/media/fat` on the MiSTer SD card, and run the MiSTer updaters.

Add these sections to `/media/fat/MiSTer.ini`:

```ini
[Sonic Mania]
main=MiSTer_SonicMania

[Sonic Mania (4:3)]
main=MiSTer_SonicMania
```

Copy `Data.rsdk` from your own Sonic Mania installation to
`/media/fat/games/sonic-mania/Data.rsdk`. The database does not include the
game data.
