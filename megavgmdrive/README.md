# MegaVGMDrive database

- Database ID:
  [`MultiDatabases/megavgmdrive`](https://theypsilon.github.io/DB-Inspector_MiSTer/?database-url=https%3A%2F%2Fraw.githubusercontent.com%2Ftheypsilon%2FMultiDatabases_MiSTer%2Fdb%2Fmegavgmdrive%2Fdb.json)
- Upstream:
  [`dai-VGM/MegaVGMDrive`](https://github.com/dai-VGM/MegaVGMDrive)
- Database URL:
  `https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/megavgmdrive/db.json`

The generator follows the MiSTer core `.rbf` asset of the highest
version-tagged upstream release. Upstream also publishes beta snapshots as
ordinary releases, sometimes without any asset, so snapshots are skipped, but
never quietly: generation fails instead of keeping an older core when the
newest stable release stops shipping its core or renames it, or when a
snapshot published after it carries one. Reviewed snapshot tags are recorded
in the generator's `REVIEWED_SNAPSHOTS`. The generator installs the selected
core and `MegaVGMDrive.mgl`, creates
`games/MegaVGMDrive`, and marks core changes as requiring a reboot. The
launcher is maintained in this folder and served from the repository's `main`
branch.

## Installation

Download
[`downloader_MultiDatabases_megavgmdrive.zip`](https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/megavgmdrive/downloader_MultiDatabases_megavgmdrive.zip),
extract it to `/media/fat` on the MiSTer SD card, and run the MiSTer updaters.

No `MiSTer.ini` changes or BIOS files are required.

Place your own compatible VGM files in
`/media/fat/games/MegaVGMDrive/`. The database provides only the core and
launcher; it does not include music files.
