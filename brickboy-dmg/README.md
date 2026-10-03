# BrickBoy DMG database

- Database ID:
  [`MultiDatabases/brickboy-dmg`](https://theypsilon.github.io/DB-Inspector_MiSTer/?database-url=https%3A%2F%2Fraw.githubusercontent.com%2Ftheypsilon%2FMultiDatabases_MiSTer%2Fdb%2Fbrickboy-dmg%2Fdb.json)
- Upstream:
  [`kandowontu2/BrickBoy_MiSTer`](https://github.com/kandowontu2/BrickBoy_MiSTer)
- Database URL:
  `https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/brickboy-dmg/db.json`

The generator follows the latest published upstream release and requires its
`BrickBoy.rbf` asset. It installs the core in `_Custom Cores/Cores` and adds
`BrickBoy_DMG.mgl` to `Custom Cores`. Core updates do not require a reboot.

## Upstream moved, and so did the core file

This database originally followed `kandowontu/brickboy-dmg-fpgacore`. That
repository and its account were removed, which left the published core download
dead, and the author continued the project as
[`kandowontu2/BrickBoy_MiSTer`](https://github.com/kandowontu2/BrickBoy_MiSTer).
This database follows the new repository from its `0.5.1` release.

Upstream renamed the core binary, so the installed core moved from
`_Custom Cores/Cores/BrickBoy_DMG.rbf` to `_Custom Cores/Cores/BrickBoy.rbf`.
The next Downloader run installs the new file and removes the old one.

The launcher keeps its `BrickBoy_DMG.mgl` name and its `BrickBoy_DMG` save
directory, so the menu entry stays where it was and existing saves and core
settings are still picked up. Only the core it launches changed.

## Installation

Download
[`downloader_MultiDatabases_brickboy-dmg.zip`](https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/brickboy-dmg/downloader_MultiDatabases_brickboy-dmg.zip),
extract it to `/media/fat` on the MiSTer SD card, and run the MiSTer updaters.

No `MiSTer.ini` changes or BIOS files are required. Supply your own compatible
Game Boy ROMs and load them through the core menu.
