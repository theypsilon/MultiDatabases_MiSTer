# Disc Tools database

- Database ID:
  [`MultiDatabases/disc-tools`](https://theypsilon.github.io/DB-Inspector_MiSTer/?database-url=https%3A%2F%2Fraw.githubusercontent.com%2Ftheypsilon%2FMultiDatabases_MiSTer%2Fdb%2Fdisc-tools%2Fdb.json)
- Upstream:
  [`Anime0t4ku/MiSTer-Disc-Tools`](https://github.com/Anime0t4ku/MiSTer-Disc-Tools)
- Database URL:
  `https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/disc-tools/db.json`

Disc Tools is a native ARM utility for MiSTer that can rip physical CDs to
BIN/CUE or CHD, burn BIN/CUE and CHD images, and build/burn ISO9660/Joliet data
discs for MSU1 and MD+ sets. It runs from the MiSTer Scripts menu and does not
include or require an FPGA core.

The generator follows the latest published GitHub release and downloads the
release ZIP asset itself. It validates that the ZIP contains the Disc Tools
launcher plus the ARM application and its required `cdrdao`, `cue2toc`,
`toc2cue`, `chdman`, and `xorriso` helper binaries before publishing the
payload. Files are installed from the ZIP with their packaged MiSTer paths;
raw repository files are not used.

## Installation

Download
[`downloader_MultiDatabases_disc-tools.zip`](https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/disc-tools/downloader_MultiDatabases_disc-tools.zip),
extract it to `/media/fat` on the MiSTer SD card, and run the MiSTer updaters.
Then launch **disctools** from the MiSTer **Scripts** menu.

The launcher is installed as `/media/fat/Scripts/disctools.sh`. The application,
helper binaries, licenses and runtime data live under
`/media/fat/Scripts/.config/disctools/`. Disc Tools creates and manages its own
`logs` and `temp` directories there; database updates do not install files into
those runtime directories.

No `MiSTer.ini` changes are required. No FPGA core, BIOS files, or game files
are required. An optical drive connected to the MiSTer is required for physical
disc ripping and burning. Blank writable media is required for burn operations.
