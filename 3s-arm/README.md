# 3S-ARM database

- Database ID:
  [`MultiDatabases/3s-arm`](https://theypsilon.github.io/DB-Inspector_MiSTer/?database-url=https%3A%2F%2Fraw.githubusercontent.com%2Ftheypsilon%2FMultiDatabases_MiSTer%2Fdb%2F3s-arm%2Fdb.json)
- Upstream:
  [`kimchiman52/3s-mister-arm`](https://github.com/kimchiman52/3s-mister-arm)
- Database URL:
  `https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/3s-arm/db.json`

3S-ARM is a hybrid FPGA/ARM port rather than a standalone FPGA core. The
generator follows the latest GitHub release ZIP and selectively maps its
launcher, `_Other` core, and `games/3s-arm` runtime into their MiSTer
locations. Upstream dates the core the way MiSTer does, so the installed core
is `_Other/3S-ARM_YYYYMMDD.rbf` and that date moves whenever upstream rebuilds
it; each release has to publish exactly one such core, and any other core name
fails the generator instead of moving the file users have installed. The
upstream README and any bundled `SF33RD.AFS` game data are excluded.

## Installation

Download
[`downloader_MultiDatabases_3s-arm.zip`](https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/3s-arm/downloader_MultiDatabases_3s-arm.zip),
extract it to `/media/fat` on the MiSTer SD card, and run the MiSTer updaters.

Add this section to `/media/fat/MiSTer.ini`:

```ini
[3S-ARM]
main=MiSTer_3S-ARM
```

The section name stays `[3S-ARM]` as the core's date changes, because MiSTer
derives a core's identity from its filename with the `_YYYYMMDD` datecode
stripped.

The merged CPS-3 arcade romset `sfiii3.zip` is required, and you supply it
yourself: copy it to your arcade ROM folder, `/media/fat/games/mame/`, or to
`/media/fat/games/3s-arm/resources/`, which this database creates for you. The
flat `sfiii3nr1.zip` alone is not enough, as it carries no graphics data.
`sfiii2.zip` and `sfiii.zip` in the same folder are optional and add the 2nd
Impact and New Generation stages. No BIOS file is required.

`SF33RD.AFS` from your own PlayStation 2 copy of Street Fighter III: Third
Strike is optional: copy it to
`/media/fat/games/3s-arm/resources/SF33RD.AFS` for the arranged soundtrack and
the PlayStation 2 screen art. Without it the game runs from the arcade romset
alone. The database includes neither the romset nor the game data.

Then launch **3S-ARM** from MiSTer's `_Other` menu.

**Upgrading from a database generated before upstream v20261117:** add
`sfiii3.zip` as above before updating. Up to v20260417 the game ran from
`SF33RD.AFS` alone, and it no longer boots that way. The core also moved from
`_Other/3S-ARM.rbf` to its dated name in the same release; the old file leaves
this database, so the Downloader removes it for you and 3S-ARM stays a single
entry in the `_Other` menu.

Since upstream v20261117 the app also plays online: a lobby, LAN play, room
codes and spectating, reachable from its OSD. It also refreshes the week's
best Fightcade replays in the background (upstream documents this as once a
day), which you can turn off by putting `replay-proxy-host = off` in
`/media/fat/games/3s-arm/config`.
