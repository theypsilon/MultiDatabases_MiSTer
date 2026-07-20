# MegaVGMDrive database

- Database ID: `MultiDatabases/megavgmdrive`
- Upstream:
  [`dai-VGM/MegaVGMDrive`](https://github.com/dai-VGM/MegaVGMDrive)
- Database URL:
  `https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/megavgmdrive/db.json`

The generator follows the `VGM_MD_MiSTer.rbf` asset in the latest GitHub
release. It installs that core and `MegaVGMDrive.mgl`, creates
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
