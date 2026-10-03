# Donut Dodo MiSTer database

- Database ID:
  [`MultiDatabases/donut-dodo`](https://theypsilon.github.io/DB-Inspector_MiSTer/?database-url=https%3A%2F%2Fraw.githubusercontent.com%2Ftheypsilon%2FMultiDatabases_MiSTer%2Fdb%2Fdonut-dodo%2Fdb.json)
- Upstream:
  [`gmcnaught/donut.dodo-mister`](https://github.com/gmcnaught/donut.dodo-mister)
- Database URL:
  `https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/donut-dodo/db.json`

Donut Dodo MiSTer is a hybrid FPGA/ARM port of Zapposh's Godot 3.5 game Donut
Dodo: the game logic runs in a Godot engine on the ARM cores, while an FPGA
blitter core draws every frame and carries audio and the joystick. The
generator follows the latest upstream release ZIP named
`DonutDodo-MiSTer-<date>.zip` and installs every MiSTer file it publishes — the
`_Other/DonutDodo_YYYYMMDD.rbf` core and its MGL, the `Scripts/DonutDodo.sh`
and `Scripts/DonutDodo_CoresMenu.sh` entries, and the `games/DonutDodo` engine,
libraries, launcher, README and licence, with the mister-hybrid `main=` hook and
this core's registry entry in `games/DonutDodo/platform/`. Updates to the
write-combining kernel module are marked as requiring a reboot, because an
already-loaded copy stays resident.

The database does not include the game. You need your own copy of
[Donut Dodo — RetroPie Edition](https://zapposh.itch.io/donut-dodo-retropie-edition).

## Installation

Download
[`downloader_MultiDatabases_donut-dodo.zip`](https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/donut-dodo/downloader_MultiDatabases_donut-dodo.zip),
extract it to `/media/fat` on the MiSTer SD card, and run the MiSTer updaters.

Copy `DonutDodo/gamedata/DonutDodo.pck` from the RetroPie Edition download to
`/media/fat/games/DonutDodo/gamedata/DonutDodo.pck`. No BIOS file is required.

No manual `MiSTer.ini` edit is required. **Scripts → DonutDodo** loads the core
and starts the game. To start the game by loading **DonutDodo** from the
**_Other** core list instead, run **Scripts → DonutDodo_CoresMenu** once: it
adds this section to `MiSTer.ini`, backing the file up first, and removes it
again on the next run.

```ini
[DonutDodo]
main=/media/fat/games/DonutDodo/platform/MiSTer_hybrid
```

If you installed an upstream release by hand before, run **Scripts →
DonutDodo** once after the first update. It moves an older `[DonutDodo] main=`
line to the hook above and removes the files that older releases installed
under `linux/` or next to the game.

Saves and settings are kept in `games/DonutDodo/conf/`, which the database
does not touch. Creating an empty `/media/fat/games/DonutDodo/NOENGINE` file
stops the hook from starting the game without editing `MiSTer.ini`. If the
Downloader requests a reboot after updating the `mem_wc` kernel module, reboot
before the next launch.
