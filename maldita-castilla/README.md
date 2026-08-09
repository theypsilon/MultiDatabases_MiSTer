# Maldita Castilla MiSTer database

- Database ID:
  [`MultiDatabases/maldita-castilla`](https://theypsilon.github.io/DB-Inspector_MiSTer/?database-url=https%3A%2F%2Fraw.githubusercontent.com%2Ftheypsilon%2FMultiDatabases_MiSTer%2Fdb%2Fmaldita-castilla%2Fdb.json)
- Upstream:
  [`gmcnaught/maldita.castilla-mister`](https://github.com/gmcnaught/maldita.castilla-mister)
- Database URL:
  `https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/maldita-castilla/db.json`

Maldita Castilla MiSTer is a hybrid FPGA/ARM port of Locomalito's GameMaker
game. The ARM-side `gmloader` engine runs the original game while a custom FPGA
core accelerates rasterisation. The database follows the latest stable,
versioned upstream release and installs its dated core, launchers, ARM engine,
runtime libraries, optional write-combining kernel module, and included game.
It omits only the ZIP's generic top-level `README.md`, which is not needed at
runtime and would otherwise overwrite the same SD-card-root path used by other
packages.

The original `game.droid` data is byte-identical to Locomalito's original
`data.win`. Locomalito publishes the original game—not the commercial EX
edition—under
[CC BY-NC-ND 4.0](https://creativecommons.org/licenses/by-nc-nd/4.0/legalcode.en).
That permits noncommercial sharing of unmodified material with attribution.
See the [official game page](https://locomalito.com/games/maldita-castilla) and
the [license terms](https://creativecommons.org/licenses/by-nc-nd/4.0/legalcode.en).

## Installation

Download
[`downloader_MultiDatabases_maldita-castilla.zip`](https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/maldita-castilla/downloader_MultiDatabases_maldita-castilla.zip),
extract it to `/media/fat` on the MiSTer SD card, and run the MiSTer updaters.
Start the game from **Scripts → MalditaCastilla**; loading its RBF directly
does not start the ARM engine by default. If the Downloader requests a reboot
after installing or updating the `mem_wc` kernel module, reboot before the next
launch so an already-loaded copy cannot remain resident.

No `MiSTer.ini` change, BIOS file, or separately supplied game file is
required. The optional **Scripts → MalditaCastilla_CoresMenu** entry backs up
`MiSTer.ini` and toggles this section so the Cores browser can start the engine
too:

```ini
[Maldita Castilla]
main=/media/fat/games/gmloader/MiSTer_Maldita
```

That setting replaces the running MiSTer binary for this core; do not point
`main=` at a shell script. The normal Scripts launcher avoids the replacement
entirely and remains available whether the optional setting is armed or not.

No daemon is required. When upgrading an older manual installation, delete a
leftover `/media/fat/games/Maldita Castilla/_handler.sh` before launching: the
Master_Daemon treats that filename as a hook and can otherwise start a second
engine. If multiple dated `_Other/MalditaCastilla_*.rbf` files remain after an
update, remove the older copies so the Cores menu cannot launch a stale core.
