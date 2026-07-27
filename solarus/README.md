# Solarus MiSTer database

- Database ID:
  [`MultiDatabases/solarus`](https://theypsilon.github.io/DB-Inspector_MiSTer/?database-url=https%3A%2F%2Fraw.githubusercontent.com%2Ftheypsilon%2FMultiDatabases_MiSTer%2Fdb%2Fsolarus%2Fdb.json)
- Upstream:
  [`gmcnaught/solarus-mister`](https://github.com/gmcnaught/solarus-mister)
- Database URL:
  `https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/solarus/db.json`

Solarus MiSTer is a hybrid FPGA/ARM port of the [Solarus](https://www.solarus-games.org)
2D action-RPG engine rather than a standalone FPGA core: the engine runs as ARM
software while a custom FPGA core composites the frame and drives video, audio,
and input. The generator follows the latest GitHub release ZIP named
`solarus-mister-vX.Y.Z.zip` and installs every MiSTer file it publishes — the
`_Other/Solarus_YYYYMMDD.rbf` core, the `games/Solarus` engine, launcher
scripts and libraries, the `Scripts/Solarus.sh` launcher, and the on-card
`docs/Solarus` README. Only the ZIP's own `BUILD-INFO.txt` release provenance
is left out, since it is not a MiSTer file. Updates to the auto-launch daemon
are marked as requiring a reboot, because an already-running daemon keeps
serving until the next boot.

## Installation

Download
[`downloader_MultiDatabases_solarus.zip`](https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/solarus/downloader_MultiDatabases_solarus.zip),
extract it to `/media/fat` on the MiSTer SD card, and run the MiSTer updaters.

No `MiSTer.ini` changes and no BIOS files are required. A **128 MB SDRAM
expansion board** is required, because a quest's graphics are staged into SDRAM
at load time.

Copy at least one quest (a `<name>.sol` file) into
`/media/fat/games/Solarus/quests/`, then run **Solarus** from the MiSTer
**Scripts** menu once to start the auto-launch daemon and load the core. After
that first run, loading the core from the menu is enough; pick a quest from the
OSD with **Load Quest**.

Quests are separate downloads with their own licenses — see the upstream
[Getting quests](https://github.com/gmcnaught/solarus-mister#getting-quests)
section. The database supplies only the core, the engine, and the launchers; it
does not include quest data.
