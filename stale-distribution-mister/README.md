# Stale Distribution MiSTer database

- Database ID:
  [`distribution_mister`](https://theypsilon.github.io/DB-Inspector_MiSTer/?database-url=https%3A%2F%2Fraw.githubusercontent.com%2Ftheypsilon%2FMultiDatabases_MiSTer%2Fdb%2Fstale-distribution-mister%2Fdb.json.zip)
- Upstream:
  [`MiSTer-devel/Distribution_MiSTer`](https://github.com/MiSTer-devel/Distribution_MiSTer)
  and
  [`MiSTer-devel/SD-Installer-Win64_MiSTer`](https://github.com/MiSTer-devel/SD-Installer-Win64_MiSTer)
- Database URL:
  `https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/stale-distribution-mister/db.json.zip`

This database is a clone of the official MiSTer distribution with one
difference: its Linux system stays on the `release_20250402` image from the
SD-Installer repository instead of following the newest Linux release. Cores,
the MiSTer main binary, `menu.rbf`, cheats, filters, palettes and every other
file keep tracking the official distribution. It is meant for setups that need
to hold Linux back, for instance while a newer image misbehaves with a
particular board or peripheral, without giving up core updates.

The generator downloads the official `db.json.zip` and republishes that
document unchanged, except for its top-level `linux` section, which becomes
the reviewed release:

```json
{
  "hash": "8dc3acae7d758a80a363fbd7ad31d95d",
  "size": 93727644,
  "url": "https://raw.githubusercontent.com/MiSTer-devel/SD-Installer-Win64_MiSTer/b8531c7848526d9a8227841923cc4a493cb6e631/release_20250402.7z",
  "version": "250402"
}
```

The official distribution keeps only its newest Linux image in its release
assets, so the pinned copy comes from the SD-Installer repository at the commit
that published it. The hash and size were computed from that exact URL when the
pin was reviewed, and `generate_db.py --verify-linux-payload` re-downloads
and re-checks it on demand.

The Downloader only compares the version above with `/MiSTer.version`, so a
MiSTer already on a newer Linux is moved back to `250402` on the next update,
and a MiSTer on `250402` is left alone. Switching the URL below back to the
official database resumes normal Linux updates. Downloader's own
`update_linux = false` setting still disables Linux updates entirely.

## Installation

Open `/media/fat/downloader.ini` and find the `[distribution_mister]` section. Set its db_url line to the value shown below.

If the section doesn’t exist, add both lines:

```ini
[distribution_mister]
db_url = https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/stale-distribution-mister/db.json.zip
```

Then run the update_all as usual.
