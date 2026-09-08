# MegaVGMDrive database

- Database ID:
  [`MultiDatabases/megavgmdrive`](https://theypsilon.github.io/DB-Inspector_MiSTer/?database-url=https%3A%2F%2Fraw.githubusercontent.com%2Ftheypsilon%2FMultiDatabases_MiSTer%2Fdb%2Fmegavgmdrive%2Fdb.json)
- Upstream:
  [`dai-VGM/MegaVGMDrive`](https://github.com/dai-VGM/MegaVGMDrive)
- Database URL:
  `https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/megavgmdrive/db.json`

This entry is pinned to upstream release `v1.0.2` and serves its
`MegaVGMDrive_MiSTer_v1.0.2.rbf` core. Upstream's v2.0 stopped attaching a core
to its releases and turned MegaVGMPlayer into a self-installing hybrid FPGA/ARM
package: two engines an ARM supervisor picks between at run time, a modified
Main, a Remote service, and an installer that appends to
`linux/user-startup.sh`, a root folder no database may write. Review chose not
to follow that package (pull request #7), so releases published after `v1.0.2`
are skipped on purpose and this database keeps serving the v1.0.2 core for the
foreseeable future, until a human revisits the entry and changes the
generator's `PINNED_RELEASE`. The pin is still checked on every build:
generation fails if upstream stops publishing `v1.0.2`, or if that release
stops shipping exactly one MiSTer core.

With the pin cleared, the generator follows the MiSTer core `.rbf` asset of the
highest version-tagged upstream release. Upstream also publishes beta snapshots
as ordinary releases, sometimes without any asset, so snapshots are skipped, but
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
