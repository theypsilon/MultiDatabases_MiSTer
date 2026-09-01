# DVD-Player database

- Database ID:
  [`MultiDatabases/dvd-player`](https://theypsilon.github.io/DB-Inspector_MiSTer/?database-url=https%3A%2F%2Fraw.githubusercontent.com%2Ftheypsilon%2FMultiDatabases_MiSTer%2Fdb%2Fdvd-player%2Fdb.json)
- Upstream:
  [`joedaniels198512-gif/dvd-core`](https://github.com/joedaniels198512-gif/dvd-core)
- Database URL:
  `https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/dvd-player/db.json`

DVD-Player is a hybrid FPGA/ARM DVD-Video player for physical DVDs and
DVD-Video ISOs. The generator follows the latest full GitHub release and
installs its ready-to-use package, not the separately published source ZIP. It
includes the FPGA core, core-specific MiSTer Main, ARM player and required
libdvdread and libdvdnav libraries.

## Installation

Download
[`downloader_MultiDatabases_dvd-player.zip`](https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/dvd-player/downloader_MultiDatabases_dvd-player.zip),
extract it to `/media/fat` on the MiSTer SD card, and run the MiSTer updaters.

Add this section to `/media/fat/MiSTer.ini` without replacing the existing
contents:

```ini
[DVD-Player]
main=MiSTer_DVD
```

DVD-Player works without `libdvdcss.so.2` for unencrypted physical DVDs and
decrypted DVD-Video ISOs. CSS-encrypted commercial DVDs and encrypted ISOs
require a user-supplied 32-bit ARM hard-float build at
`/media/fat/DVD/lib/libdvdcss.so.2`. The database does not provide, remove or
overwrite that optional file. No BIOS is required, and no DVD images or other
media are included.
