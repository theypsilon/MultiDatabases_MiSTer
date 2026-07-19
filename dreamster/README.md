# DreamSTer database

- Database ID: `MultiDatabases/dreamster`
- Upstream: [`skmp/DreamSTer`](https://github.com/skmp/DreamSTer)
- Database URL:
  `https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/dreamster/db.json`

The generator follows the newest published DreamSTer release containing a
DreamSTer ZIP, including releases marked as pre-release. It installs the
upstream `Scripts/DreamSTer.sh` and `minicast` runtime and creates
`games/Dreamcast`.

## Installation

Download
[`downloader_MultiDatabases_dreamster.zip`](https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/dreamster/downloader_MultiDatabases_dreamster.zip),
extract it to `/media/fat` on the MiSTer SD card, and run the MiSTer updaters.

No `MiSTer.ini` changes are required.

Copy both Dreamcast BIOS files to `/media/fat/games/Dreamcast/`:

- `dc_boot.bin`
- `dc_flash.bin`

Place your own Dreamcast games under `/media/fat/games/Dreamcast/` as well.
The database does not include BIOS or game files.
