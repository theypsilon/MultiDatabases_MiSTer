# MiSTerVision database

- Database ID:
  [`MultiDatabases/mister-vision`](https://theypsilon.github.io/DB-Inspector_MiSTer/?database-url=https%3A%2F%2Fraw.githubusercontent.com%2Ftheypsilon%2FMultiDatabases_MiSTer%2Fdb%2Fmister-vision%2Fdb.json)
- Upstream:
  [`trentnix/mistervision`](https://github.com/trentnix/mistervision)
- Database URL:
  `https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/mister-vision/db.json`

MiSTerVision is a [Jellyfin](https://jellyfin.org) and
[Plex](https://www.plex.tv) client for CRT televisions on MiSTer, formerly
released as MiSTerFin CRT. It is ARM software, not a hybrid FPGA/ARM port: it
runs from the Scripts menu on the standard `menu.rbf`, draws to the MiSTer
framebuffer at 240p or 288p, and plays server-transcoded video through its own
bundled `mplayer-arm`. For optional 480i or 576i output it ships
`InterlacedMenu.rbf`, a standalone Menu core that the client loads itself and
swaps back for the normal menu on exit; nothing is installed over `MiSTer`,
`menu.rbf` or the kernel.

The generator follows the latest GitHub release ZIP named
`mistervision-vX.Y.Z-progressive.zip` and installs everything it publishes
under `mistervision/` plus `Scripts/MiSTerVision.sh`, skipping only the
top-level `INSTALL.txt` and `SHA256SUMS`. Upstream also publishes an
`-interlaced` ZIP with the same binaries and core; the two differ only in the
display mode the launcher seeds on a first run, and this database follows the
progressive one, which upstream documents as the default.

## Installation

Download
[`downloader_MultiDatabases_mister-vision.zip`](https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/mister-vision/downloader_MultiDatabases_mister-vision.zip),
extract it to `/media/fat` on the MiSTer SD card, and run the MiSTer updaters.
Then launch **MiSTerVision** from the MiSTer **Scripts** menu.

### 480i / 576i output

This database installs the progressive preset, so a new installation starts at
240p (NTSC) or 288p (PAL). Interlaced output is already installed and only
needs switching on: exit the client and put this in
`/media/fat/mistervision/settings.json`, keeping any other settings in the
file:

```json
{
  "display": {
    "interlaced": true
  }
}
```

The setting is yours: neither this database nor a later update changes it back.
Set it to `false` to return to progressive output.

No `MiSTer.ini` changes are required from you in either mode. Be aware that
with interlacing enabled the client edits `/media/fat/MiSTer.ini` on its own:
it adds a marked `[MiSTerVisionInterlaced]` section and first saves a backup as
`/media/fat/mistervision/MiSTer.ini.before-interlaced`. See the upstream
[display guide](https://github.com/trentnix/mistervision/blob/main/docs/GO_DISPLAY.md)
for cabling, kernel requirements and the tested scope.

### Server and sign-in

No BIOS files and no game files are required. You need your own Jellyfin or
Plex server: on first launch the client discovers a local Jellyfin server and
signs in through Quick Connect, and Plex is linked from **About → Connections**
with a code entered at `plex.tv/link`. For an explicit server address, copy the
installed `settings.example.json` to `/media/fat/mistervision/settings.json`
and set `server.provider` and `server.url`. The database never installs
`settings.json`, `jellyfin.conf` or anything under `state/`, so your server,
login and display mode survive updates; the generator rejects a release that
ships one of them.

MiSTerVision also has a built-in updater on its About screen. Leave it alone if
you install through this database: it writes over the same files the downloader
manages, so the next downloader run restores the version this database pins.

When moving from MiSTerFin CRT, follow upstream's `INSTALL.txt` notes to carry
your settings and state into `/media/fat/mistervision` before the first launch.
