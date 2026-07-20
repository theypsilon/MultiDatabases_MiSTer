# MMS2 GB Core database

- Database ID:
  [`MultiDatabases/mms2-gb`](https://theypsilon.github.io/DB-Inspector_MiSTer/?database-url=https%3A%2F%2Fraw.githubusercontent.com%2Ftheypsilon%2FMultiDatabases_MiSTer%2Fdb%2Fmms2-gb%2Fdb.json)
- Upstream:
  [`Heber-co-uk/Gameboy_MiSTer_Cart`](https://github.com/Heber-co-uk/Gameboy_MiSTer_Cart)
- Database URL:
  `https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/mms2-gb/db.json`

The generator selects the newest `Gameboy_YYYYMMDD.rbf` published in the
upstream `releases` directory. It installs the core in `MMS2`, adds a
cartridge-launch shortcut and its configuration, and marks core changes as
requiring a reboot. Successive dated RBF files are entangled so an update
removes the superseded core.

## Installation

Download
[`downloader_MultiDatabases_mms2-gb.zip`](https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/mms2-gb/downloader_MultiDatabases_mms2-gb.zip),
extract it to `/media/fat` on the MiSTer SD card, and run the MiSTer updaters.

No `MiSTer.ini` changes, BIOS files, or game files are required. This core
requires a Heber Multisystem 2 with compatible cartridge hardware and a
physical Game Boy or Game Boy Color cartridge. Hold the MiSTer USER button
while inserting or removing a cartridge.
