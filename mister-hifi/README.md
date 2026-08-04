# MiSTer Hi-Fi database

- Database ID:
  [`MultiDatabases/mister-hifi`](https://theypsilon.github.io/DB-Inspector_MiSTer/?database-url=https%3A%2F%2Fraw.githubusercontent.com%2Ftheypsilon%2FMultiDatabases_MiSTer%2Fdb%2Fmister-hifi%2Fdb.json)
- Upstream:
  [`Anime0t4ku/MiSTer_Hi-Fi`](https://github.com/Anime0t4ku/MiSTer_Hi-Fi)
- Database URL:
  `https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/mister-hifi/db.json`

MiSTer Hi-Fi is a controller-first music player for MiSTer. It plays MP3, FLAC
and WAV files plus M3U/M3U8 playlists and physical Audio CDs, from the SD card,
USB storage or SMB shares, with album artwork, a spectrum visualizer, a 5-band
equalizer, OLED mode and Zaparoo NFC launching. It is plain ARM software, not an
FPGA core and not a hybrid FPGA/ARM port: it runs from the Scripts menu on the
standard `menu.rbf`.

The generator follows the latest GitHub release and installs the three files it
publishes: `Scripts/misterhifi.sh`, the `mister_hifi` ARM binary and
`smb.example.json` under `Scripts/.config/MiSTerHiFi`. The upstream asset is
unversioned today, so the generator accepts any ZIP asset of the release and
validates its layout instead of its name: it requires one launcher in
`Scripts`, one 32-bit ARM binary inside a `Scripts/.config` application folder,
nothing outside those, and a launcher that runs the binary from the exact path
this database installs it to.

## Installation

Download
[`downloader_MultiDatabases_mister-hifi.zip`](https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/mister-hifi/downloader_MultiDatabases_mister-hifi.zip),
extract it to `/media/fat` on the MiSTer SD card, and run the MiSTer updaters.
Then launch **misterhifi** from the MiSTer **Scripts** menu.

No `MiSTer.ini` changes are required. No FPGA core, no BIOS files and no game
files are required either. Music and album artwork are yours to supply: the
database installs the player only, and MiSTer Hi-Fi writes its own
`config.json` on first launch.

For SMB shares you write `/media/fat/Scripts/.config/MiSTerHiFi/smb.json`
yourself, using the installed `smb.example.json` as a template — it holds your
server address and credentials. The database never installs `smb.json` or
`config.json`, so an update cannot overwrite your settings or credentials; the
generator rejects a release that ships either of them.

Physical Audio CD playback needs an optical drive connected to the MiSTer, and
Zaparoo NFC launching needs Zaparoo installed separately. Neither is part of
this database.
