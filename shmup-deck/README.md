# Shmup Deck database

- Database ID:
  [`MultiDatabases/shmup-deck`](https://theypsilon.github.io/DB-Inspector_MiSTer/?database-url=https%3A%2F%2Fraw.githubusercontent.com%2Ftheypsilon%2FMultiDatabases_MiSTer%2Fdb%2Fshmup-deck%2Fdb.json)
- Upstream:
  [`searchsolved/shmup-deck`](https://github.com/searchsolved/shmup-deck)
- Database URL:
  `https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/shmup-deck/db.json`

Shmup Deck is a flyer-wall launcher for shoot 'em ups on the MiSTer. It runs
on the MiSTer itself: you open `http://shmupdeck.local` on your phone, tap a
flyer, and the MiSTer loads that game through its own `/dev/MiSTer_cmd`
interface. It covers 178 arcade shooters across Toaplan, Cave, CPS1/CPS2,
PGM, Psikyo, Raizing, Konami, Irem, NMK, Taito F3, Seta, ST-V, Neo Geo and
more, shows only the games actually installed on your SD card or USB drives,
keeps shared favourites and play statistics on the MiSTer, and has a checklist
page that tells you which MRA, core or ROM zips each game still needs.

It is plain ARM software, not an FPGA core and not a hybrid FPGA/ARM port: a
single standard-library Python 3 file, `shmup_deck.py`, that runs as a
background service on the MiSTer's own Linux, using about 14 MB of RAM with
idle CPU near zero. Games run on the ordinary arcade cores you already have.

The generator follows the latest GitHub release and installs the two assets it
publishes:

- `Scripts/shmup_deck.sh`, the release's launcher, as a direct file.
- The contents of `shmup_deck.zip` under `Scripts/.config/shmup_deck/`: the
  `shmup_deck.py` service and its `app/` web pages, game list, art manifest and
  core table, at the same paths the launcher itself unpacks them to.

Both assets are looked up by the exact names the launcher expects, and the
release is validated before it is accepted: the tag must be `vX.Y.Z` and match
the version the service declares, the ZIP must ship `shmup_deck.py` and the
`app/` files and nothing else, no binaries, and the launcher must run the
service from the folder this database installs it to and register it at boot
the reviewed way described below. A release that changes any of that fails
the build for review instead of being published. The service is marked as
requiring a reboot, because it is started at boot and a new version only takes
over on the next start.

The database never installs what Shmup Deck writes for itself inside
`Scripts/.config/shmup_deck/`: the `VERSION` note the launcher keeps, the
downloaded flyer art in `art/`, the MRA index, `plays.json` and
`favourites.json`. An update cannot touch them, and the generator rejects a
release that ships any of them.

## Installation

Download
[`downloader_MultiDatabases_shmup-deck.zip`](https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/shmup-deck/downloader_MultiDatabases_shmup-deck.zip),
extract it to `/media/fat` on the MiSTer SD card, and run the MiSTer updaters.

Then run **shmup_deck** once from the MiSTer **Scripts** menu. Upstream's
launcher does what the database cannot: it adds Shmup Deck to
`/media/fat/linux/user-startup.sh` so the service starts at every boot, starts
it right away, and shows the address to open on your phone,
`http://shmupdeck.local`, or the numbered `http://<mister-ip>:8190` if that
name does not resolve on your network. The MiSTer needs network access for
this run: the launcher checks GitHub for the latest release, and because the
database installs no `VERSION` note, it fetches the release once more to
record which version is installed. Later runs only check for updates.

The first start scans your arcade folders and downloads the flyer art, which
takes a few minutes. Games appear as soon as the scan finishes and flyers fill
in as they arrive.

The launcher also updates Shmup Deck on its own when run again. If it installs
a release before this database has followed it, the next updater run puts the
database's release back until the database catches up, which normally happens
within the hour.

### Startup entry and removal

The boot entry is a single line appended to `/media/fat/linux/user-startup.sh`
and marked with the comment `# shmup_deck`. The database does not write it:
`linux` is a folder no database may touch, so it is only added by running the
launcher, and it is only removed by running the launcher's uninstall command
over SSH:

```
/media/fat/Scripts/shmup_deck.sh uninstall
```

That stops the service and deletes the marked line, the same as running
`sed -i "/# shmup_deck/d" /media/fat/linux/user-startup.sh`. The installed
files are kept; remove the `[MultiDatabases/shmup-deck]` section from your
`downloader.ini` and delete `/media/fat/Scripts/shmup_deck.sh` and
`/media/fat/Scripts/.config/shmup_deck/` to remove them too. Updating the
database never adds or removes the boot entry.

## Requirements

No `MiSTer.ini` changes are required. No FPGA core of its own and no BIOS files
are required either. Shmup Deck contains no ROMs, MRAs or cores: it launches
the arcade MRAs, ROM zips and cores already on your MiSTer, in any folder under
`_Arcade` or another top-level `_` folder on the SD card or a USB drive, and
Neo Geo games from `games/NeoGeo` through the Neo Geo core. Upstream's
[ROMS.md](https://github.com/searchsolved/shmup-deck/blob/main/ROMS.md) lists
every supported game with its core and ROM zips, and
`http://shmupdeck.local/check.html` checks them against your SD card.

The service serves the web app on port 8190, and on port 80 when that port is
free, and answers mDNS lookups for `shmupdeck.local` itself. Flyer art is not
part of this database: it is downloaded once by the service, from the
upstream art mirror or the original scan sources, into
`/media/fat/Scripts/.config/shmup_deck/art/`.
