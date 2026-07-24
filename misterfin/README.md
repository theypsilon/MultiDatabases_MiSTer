# MiSTerFin database

- Database ID:
  [`MultiDatabases/misterfin`](https://theypsilon.github.io/DB-Inspector_MiSTer/?database-url=https%3A%2F%2Fraw.githubusercontent.com%2Ftheypsilon%2FMultiDatabases_MiSTer%2Fdb%2Fmisterfin%2Fdb.json.zip)
- Upstream:
  [`puddingstudio/MiSTerFin`](https://github.com/puddingstudio/MiSTerFin)
- Database URL:
  `https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/misterfin/db.json.zip`

This entry serves the compressed database: one JSON entry per bundled asset
makes it far larger than the rest, and the ZIP is around a sixth of the size.
The uncompressed `db.json` is still published next to it, but `db_url` points
at the ZIP and will not change.

MiSTerFin is a [Jellyfin](https://jellyfin.org) media client for MiSTer. It is
plain ARM software, not a hybrid FPGA/ARM port and not an FPGA core: it runs
from the Scripts menu on the standard `menu.rbf` and draws to the regular
MiSTer framebuffer, with video transcoded server-side by Jellyfin and played
through its own bundled `mplayer-arm`.

The generator follows the latest GitHub release ZIP named
`misterfin-vX.Y.Z.zip` and installs everything it publishes: the
`misterfin-arm` client, `mplayer-arm`, the font, subtitle-font and Toasty
Squadron assets, and `jellyfin.conf.example`. The release packs its launcher
inside the app folder, so the generator maps that one file to
`Scripts/MiSTerFin.sh`, which is where upstream's install instructions put it
and the only place the MiSTer menu reads it from.

## Installation

Download
[`downloader_MultiDatabases_misterfin.zip`](https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/misterfin/downloader_MultiDatabases_misterfin.zip),
extract it to `/media/fat` on the MiSTer SD card, and run the MiSTer updaters.
Then launch **MiSTerFin** from the MiSTer **Scripts** menu.

No FPGA core, no BIOS files, and no game files are required.

You must supply `/media/fat/misterfin/jellyfin.conf` yourself — four lines
holding your Jellyfin server URL, an API key, your username, and `PAL` or
`NTSC`. Copy the installed `jellyfin.conf.example` and fill it in over SSH or
by pulling the SD card; there is no on-screen setup keyboard. The database
never installs `jellyfin.conf`, so your credentials are not overwritten by an
update; the generator rejects a release that ships one.

No `MiSTer.ini` changes are required to run the client over HDMI. Analog and
CRT output depends on your own cable chain and needs display-specific settings
such as `ypbpr`, `composite_sync`, `vga_scaler` and a `[Menu]` `video_mode`
override — see the upstream
[display compatibility guide](https://github.com/puddingstudio/MiSTerFin/blob/main/docs/DISPLAY_COMPATIBILITY.md)
for verified combinations.

MiSTerFin also has a built-in updater on its About screen. Leave it alone if
you install through this database: it writes over the same files the downloader
manages, so the next downloader run restores the version this database pins.
