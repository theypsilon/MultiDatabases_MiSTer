# 3S-ARM database

- Database ID:
  [`MultiDatabases/3s-arm`](https://theypsilon.github.io/DB-Inspector_MiSTer/?database-url=https%3A%2F%2Fraw.githubusercontent.com%2Ftheypsilon%2FMultiDatabases_MiSTer%2Fdb%2F3s-arm%2Fdb.json)
- Upstream:
  [`kimchiman52/3s-mister-arm`](https://github.com/kimchiman52/3s-mister-arm)
- Database URL:
  `https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/3s-arm/db.json`

The generator follows the latest GitHub release ZIP and selectively maps its
launcher, `_Other` files, and `games/3s-arm` runtime into their MiSTer
locations. The upstream README and any bundled `SF33RD.AFS` game data are
excluded.

## Installation

Download
[`downloader_MultiDatabases_3s-arm.zip`](https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/3s-arm/downloader_MultiDatabases_3s-arm.zip),
extract it to `/media/fat` on the MiSTer SD card, and run the MiSTer updaters.

Add this section to `/media/fat/MiSTer.ini`:

```ini
[3S-ARM]
main=MiSTer_3S-ARM
```

Copy `SF33RD.AFS` from your own PlayStation 2 copy of Street Fighter III:
Third Strike to `/media/fat/games/3s-arm/resources/SF33RD.AFS`. No BIOS file is
required. The database does not include the game data.
