# MiSTer Disc database

- Database ID:
  [`MultiDatabases/mister-disc`](https://theypsilon.github.io/DB-Inspector_MiSTer/?database-url=https%3A%2F%2Fraw.githubusercontent.com%2Ftheypsilon%2FMultiDatabases_MiSTer%2Fdb%2Fmister-disc%2Fdb.json)
- Upstream: [`theshaneobrien/mister-disc-drive-support`](https://github.com/theshaneobrien/mister-disc-drive-support)
- Database URL:
  `https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/mister-disc/db.json`

Play CD games on a MiSTer straight from a USB CD or DVD drive, no ripping.
Seven consoles from real discs (PlayStation, Saturn, Mega CD, Neo Geo CD, 3DO,
TurboGrafx-CD, and CD-i), plus audio CDs, Video CDs, and CD+G karaoke. Live
disc swapping (multi-disc RPGs, Monster Rancher, Vib Ribbon with any album), per-disc memory
cards and regional BIOS on PlayStation, disc integrity telemetry, and
RetroAchievements earned from the physical disc on the RA build. ARM-side
Main binary only: the FPGA cores stay completely stock, nothing is forked or
patched, and the official cores must already be installed. The generator
follows the latest upstream GitHub release.

*The disc backend that powers other CD loaders.*

## Installation

Download
[`downloader_MultiDatabases_mister-disc.zip`](https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/mister-disc/downloader_MultiDatabases_mister-disc.zip),
extract it to `/media/fat` on the MiSTer SD card, and run the MiSTer updaters.

Add this section to `/media/fat/MiSTer.ini`:

```ini
[CD-*]
main=MiSTer_Disc
```

Use a USB optical drive that MiSTer exposes as `/dev/sr0`. Launch a console
from `_Disc Cores` with your disc in the drive and it mounts automatically a
moment after the core comes up. Insert disc, pick console, play. Each core
needs its own BIOS files exactly as it would for ripped games (PlayStation
uses `games/PSX/boot.rom` = US, `boot1.rom` = JP, `boot2.rom` = EU); the
database includes no BIOS or game files.

In this side-by-side setup your MiSTer stays stock and you pick the console
yourself. The upstream fork can do more when installed as the main MiSTer
binary - insert any disc at the menu and it identifies it, loads the right
core, and boots it - see the
[upstream README](https://github.com/theshaneobrien/mister-disc-drive-support)
for that optional full installation.

RetroAchievements users on the odelot/MiSTer Companion setup: copy the
installed `MiSTer_Disc_RA` file over `/media/fat/MiSTer_RA` (back up the
original first) and your existing hand-picked RA core launchers become
disc-capable, with achievements earned from the physical disc.
