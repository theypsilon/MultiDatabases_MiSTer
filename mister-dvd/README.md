# MiSTer DVD database

- Database ID:
  [`MultiDatabases/mister-dvd`](https://theypsilon.github.io/DB-Inspector_MiSTer/?database-url=https%3A%2F%2Fraw.githubusercontent.com%2Ftheypsilon%2FMultiDatabases_MiSTer%2Fdb%2Fmister-dvd%2Fdb.json)
- Upstream:
  [`owenb321/MiSTer_DVD`](https://github.com/owenb321/MiSTer_DVD)
- Database URL:
  `https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/mister-dvd/db.json`

MiSTer DVD is an FPGA DVD-Video player with support for decrypted DVD ISOs,
VCDs and SVCDs. Its optional custom MiSTer Main adds physical DVD playback and
CSS-encrypted ISO playback. The generator follows the latest stable GitHub
release and installs the dated DVD core, custom Main and libdvdcss library. It
runs upstream's installer in an isolated Docker filesystem and publishes the
files it leaves on the simulated `/media/fat` immutably with source metadata.
It excludes only the copied `install_dvdcss.sh` installer; any other file the
installer creates, including another script, is retained. The upstream install
note is omitted because its manual installation step no longer applies.
Upstream's `Scripts/set_dvd_region.sh` is deliberately withheld: it sets a USB
DVD drive's region, a change drives allow only about five times and never
undo, and playback does not need it. Take it from the upstream release if you
want it.

## Installation

Download
[`downloader_MultiDatabases_mister-dvd.zip`](https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/mister-dvd/downloader_MultiDatabases_mister-dvd.zip),
extract it to `/media/fat` on the MiSTer SD card, and run the MiSTer updaters.

The bare core plays decrypted DVD ISOs, VCDs and SVCDs without an INI change.
To enable physical DVDs and CSS-encrypted ISOs, add this section to
`/media/fat/MiSTer.ini`:

```ini
[DVD]
main=MiSTer_DVDcss
```

Most commercial DVDs and raw encrypted ISOs also require libdvdcss. This
database installs it directly at `/media/fat/dvdcss/libdvdcss.so.2`; no Scripts
menu installation step is required. No BIOS file is required, and the database
includes no disc images or other media.
