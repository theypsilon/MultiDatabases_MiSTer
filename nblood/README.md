# NBlood database

- Database ID:
  [`MultiDatabases/nblood`](https://theypsilon.github.io/DB-Inspector_MiSTer/?database-url=https%3A%2F%2Fraw.githubusercontent.com%2Ftheypsilon%2FMultiDatabases_MiSTer%2Fdb%2Fnblood%2Fdb.json)
- Upstream: [`meathax/blood`](https://github.com/meathax/blood)
- Database URL:
  `https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/nblood/db.json`

NBlood is a hybrid FPGA/ARM port of the Blood source port: the ARM runs the
game engine while the FPGA provides native video, audio, input, and OSD
integration. The generator follows upstream's Downloader database and installs
only its matching launcher, FPGA core, and ARM game engine. It relocates the
upstream RBF from `_Computer` to `_Other` and deliberately omits
`README_DATA.md` and every other upstream path. No commercial game data is
included.

## Installation

1. Download
   [`downloader_MultiDatabases_nblood.zip`](https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/nblood/downloader_MultiDatabases_nblood.zip),
   extract it to `/media/fat` on the MiSTer SD card, and run the MiSTer
   updaters.
2. Confirm that these three files were installed:

   - `/media/fat/Mister_NBlood`
   - `/media/fat/_Other/NBlood.rbf`
   - `/media/fat/games/NBlood/NBlood`

3. Copy your own legally obtained **Blood: Fresh Supply** data into
   `/media/fat/games/NBlood/`, alongside the installed `NBlood` engine. Copy
   everything at the top level of the game installation plus its `movie/`
   folder. This includes `BLOOD.RFF`, `blood.ini`, `sounds.rff`, `tiles*.art`,
   `blood0*.ogg`, and the other game data.

   For Cryptic Passage, flatten the contents of `addons/Cryptic Passage/` into
   that same `/media/fat/games/NBlood/` folder rather than retaining the addon
   subfolder. Copy its patched `tiles007.ART` and `tiles015.ART` last so they
   replace the base versions.
4. Add these sections to `/media/fat/MiSTer.ini`:

   ```ini
   [NBlood]
   main=Mister_NBlood

   [Mister_NBlood]
   main=Mister_NBlood
   ```

5. Reboot, or rescan/reload the menu, and launch **NBlood** from `_Other`.

No BIOS file is required. The extensionless `Mister_NBlood` launcher and
`games/NBlood/NBlood` engine are ARM executables; transfer them in binary mode
if copying them manually. NBlood creates `games/NBlood/Saves/` for user saves
and configuration on first launch; the database does not install or overwrite
that folder.
