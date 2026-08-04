# CollectionLauncher database

- Database ID:
  [`MultiDatabases/collection-launcher`](https://theypsilon.github.io/DB-Inspector_MiSTer/?database-url=https%3A%2F%2Fraw.githubusercontent.com%2Ftheypsilon%2FMultiDatabases_MiSTer%2Fdb%2Fcollection-launcher%2Fdb.json)
- Upstream:
  [`Anime0t4ku/MiSTer-CollectionLauncher`](https://github.com/Anime0t4ku/MiSTer-CollectionLauncher)
- Database URL:
  `https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/collection-launcher/db.json`

CollectionLauncher is a controller-first collection launcher for MiSTer. Each
collection is a folder with a `collection.json`, a wallpaper and optional logo,
music and per-game artwork; picking a game writes an MGL and launches it on the
matching core, using the presets of the
[MiSTer MGL system table](https://github.com/wizzomafizzo/mrext/blob/main/docs/systems.md).
Collections open from the Scripts menu or straight from an NFC tag through
Zaparoo. It is plain ARM software, not an FPGA core and not a hybrid FPGA/ARM
port: it runs from the Scripts menu on the standard `menu.rbf`.

The generator follows the latest GitHub release and installs the two files it
publishes, `Scripts/CollectionLauncher.sh` and the `collection_launcher` ARM
binary under `Scripts/.config/CollectionLauncher`, plus the empty `Collections`
folder the release ships and the launcher reads. It accepts any ZIP asset of
the release and validates its layout instead of its name, so a renamed or
versioned asset still updates the database: it requires one launcher in
`Scripts`, one 32-bit ARM binary inside a `Scripts/.config` application folder,
nothing outside those, and a launcher that runs the binary from the exact path
this database installs it to.

## Installation

Download
[`downloader_MultiDatabases_collection-launcher.zip`](https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/collection-launcher/downloader_MultiDatabases_collection-launcher.zip),
extract it to `/media/fat` on the MiSTer SD card, and run the MiSTer updaters.
Then launch **CollectionLauncher** from the MiSTer **Scripts** menu.

No `MiSTer.ini` changes are required. No FPGA core and no BIOS files are
required either. Games, artwork, wallpapers and music are yours to supply: the
database installs the launcher only.

You build your own collections under
`/media/fat/Scripts/.config/CollectionLauncher/Collections/<YourCollection>/`,
each with a `collection.json` pointing at games already on your MiSTer — see
the [upstream README](https://github.com/Anime0t4ku/MiSTer-CollectionLauncher#collection-structure)
for the format. The database never installs anything inside `Collections` or
the launcher's `tmp` folder, so an update cannot touch your collections; the
generator rejects a release that ships files there.

Launching a collection directly from an NFC tag needs Zaparoo installed
separately; it is not part of this database.
