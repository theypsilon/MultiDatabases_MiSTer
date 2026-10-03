# BrickBoy DMG database (removed)

- Database ID:
  [`MultiDatabases/brickboy-dmg`](https://theypsilon.github.io/DB-Inspector_MiSTer/?database-url=https%3A%2F%2Fraw.githubusercontent.com%2Ftheypsilon%2FMultiDatabases_MiSTer%2Fdb%2Fbrickboy-dmg%2Fdb.json)
- Upstream: `kandowontu/brickboy-dmg-fpgacore` — **withdrawn, not linked
  because it no longer exists.** The repository and its owner account both
  answer `404` over the GitHub API and over HTTPS with no rename redirect, so
  the project was removed rather than moved.
- Database URL:
  `https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/brickboy-dmg/db.json`

This database used to install a Game Boy core with a detailed DMG LCD panel and
speaker model. Upstream withdrew the project in September 2026 and the
`BrickBoy_DMG.rbf` asset this database published went with it, so its download
URL answers `404` and every install was failing on the core.

The entry is retired, not repointed. The database URL above stays published and
valid, so an already configured Downloader keeps working, but the database is
now empty and installs nothing. The core is not available anywhere, and the
identically named `kathoc/brickboy-dmg-fpgacore` is the Analogue Pocket project
upstream forked from, not a replacement.

## Installation

Nothing to install, so there is nothing to download or extract.

If you installed this database before, note that the MiSTer Downloader removes
files a database no longer lists: the next run deletes
`_Custom Cores/Cores/BrickBoy_DMG.rbf` and `Custom Cores/BrickBoy_DMG.mgl`.
Copy the `.rbf` off the SD card first if you want to keep it, because it can no
longer be downloaded from anywhere.

No `MiSTer.ini` changes and no BIOS or game files are required.
