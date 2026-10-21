# MiSTerEmby database

- Database ID:
  [`MultiDatabases/misteremby`](https://theypsilon.github.io/DB-Inspector_MiSTer/?database-url=https%3A%2F%2Fraw.githubusercontent.com%2Ftheypsilon%2FMultiDatabases_MiSTer%2Fdb%2Fmisteremby%2Fdb.json.zip)
- Upstream:
  [`freemchr/MiSTerEmby`](https://github.com/freemchr/MiSTerEmby)
- Database URL:
  `https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/misteremby/db.json.zip`

MiSTerEmby is an [Emby](https://emby.media) media client for MiSTer, ported
from MiSTerFin. It is plain ARM software, not a hybrid FPGA/ARM port and not
an FPGA core: it runs from the Scripts menu on the standard `menu.rbf` and
draws to the regular MiSTer framebuffer, with video transcoded server-side by
Emby and played through its own bundled `mplayer-arm`.

The generator follows the latest GitHub release ZIP named
`misteremby-vX.Y.Z.zip` and installs everything it publishes: the
`misteremby-arm` client, `mplayer-arm`, the font, subtitle-font and UI sound
assets, and `emby.conf.example`. The release packs its launcher inside the
app folder, so the generator maps that one file to `Scripts/MiSTerEmby.sh`,
which is where upstream's install instructions put it and the only place the
MiSTer menu reads it from.

## Installation

Download
[`downloader_MultiDatabases_misteremby.zip`](https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/misteremby/downloader_MultiDatabases_misteremby.zip),
extract it to `/media/fat` on the MiSTer SD card, and run the MiSTer updaters.
Then launch **MiSTerEmby** from the MiSTer **Scripts** menu.

No FPGA core, no BIOS files, and no game files are required.

You must supply `/media/fat/misteremby/emby.conf` yourself. The only line it
needs is your Emby server's address (`SERVER=http://...:8096`); MiSTerEmby
then shows an Emby Connect PIN to enter at emby.media/pin. A username and
password or an API key also work. Copy the installed `emby.conf.example` and
fill it in over SSH or by pulling the SD card. The database never installs
`emby.conf`, or the `token.conf` and `device.conf` files the app writes, so an
update never overwrites your server address or sign-in; the generator rejects
a release that ships any of them.

No `MiSTer.ini` changes are required to run the client over HDMI. Analog and
CRT output depends on your own cable chain and may need display-specific
settings such as a `[Menu]` `video_mode` override — see the upstream
[display compatibility guide](https://github.com/freemchr/MiSTerEmby/blob/main/docs/DISPLAY_COMPATIBILITY.md).

MiSTerEmby also has a built-in updater on its About screen. Leave it alone if
you install through this database: it writes over the same files the
downloader manages, so the next downloader run restores the version this
database pins.
