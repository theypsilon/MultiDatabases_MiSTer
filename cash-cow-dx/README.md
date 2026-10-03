# Cash Cow DX MiSTer database

- Database ID:
  [`MultiDatabases/cash-cow-dx`](https://theypsilon.github.io/DB-Inspector_MiSTer/?database-url=https%3A%2F%2Fraw.githubusercontent.com%2Ftheypsilon%2FMultiDatabases_MiSTer%2Fdb%2Fcash-cow-dx%2Fdb.json)
- Upstream:
  [`gmcnaught/cash.cow.dx-mister`](https://github.com/gmcnaught/cash.cow.dx-mister)
- Database URL:
  `https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/cash-cow-dx/db.json`

Cash Cow DX MiSTer is a hybrid FPGA/ARM port of the Godot 4.3 game Cash Cow
DX: the game logic runs in a Godot engine on the ARM cores, while an FPGA
blitter core draws every frame and carries audio and the joystick. The
generator follows the latest upstream release ZIP named
`CashCowDX-MiSTer-<date>.zip` and installs every MiSTer file it publishes — the
`_Other/CashCowDX_YYYYMMDD.rbf` core and its MGL, the `Scripts/CashCowDX.sh`
and `Scripts/CashCowDX_CoresMenu.sh` entries, and the `games/CashCowDX` engine,
launcher, runtime patches and README, with the mister-hybrid `main=` hook and
this core's registry entry in `games/CashCowDX/platform/`. Updates to the
write-combining kernel module are marked as requiring a reboot, because an
already-loaded copy stays resident.

The database does not include the game. You need your own copy of the **GOG**
release of Cash Cow DX.

## Installation

Download
[`downloader_MultiDatabases_cash-cow-dx.zip`](https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/cash-cow-dx/downloader_MultiDatabases_cash-cow-dx.zip),
extract it to `/media/fat` on the MiSTer SD card, and run the MiSTer updaters.

Copy `CashCowDX.pck` from your GOG copy (`data/noarch/game/CashCowDX.pck` in
the Linux installer, or the file next to the game executable in an installed
copy) to `/media/fat/games/CashCowDX/CashCowDX.pck`. No BIOS file is required.

No manual `MiSTer.ini` edit is required. **Scripts → CashCowDX** loads the core
and starts the game. To start the game by loading **CashCowDX** from the
**_Other** core list instead, run **Scripts → CashCowDX_CoresMenu** once: it
adds this section to `MiSTer.ini`, backing the file up first, and removes it
again on the next run.

```ini
[CashCowDX]
main=/media/fat/games/CashCowDX/platform/MiSTer_hybrid
```

If you installed an upstream release by hand before, run **Scripts →
CashCowDX** once after the first update. It moves an older `[CashCowDX] main=`
line to the hook above and removes the files that older releases installed
under `linux/`.

Saves and settings are kept in `games/CashCowDX/data/`, which the database
does not touch. Creating an empty `/media/fat/games/CashCowDX/NOENGINE` file
stops the hook from starting the game without editing `MiSTer.ini`. If the
Downloader requests a reboot after updating the `mem_wc` kernel module, reboot
before the next launch.
