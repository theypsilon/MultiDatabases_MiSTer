# Distribution MiSTer Pinned Linux database

- Database ID:
  [`distribution_mister`](https://theypsilon.github.io/DB-Inspector_MiSTer/?database-url=https%3A%2F%2Fraw.githubusercontent.com%2Ftheypsilon%2FMultiDatabases_MiSTer%2Fdb%2Fdistribution-mister-pinned-linux%2Fdb.json.zip)
- Upstream:
  [`MiSTer-devel/Distribution_MiSTer`](https://github.com/MiSTer-devel/Distribution_MiSTer)
- Database URL:
  `https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/distribution-mister-pinned-linux/db.json.zip`
- Previous database URL, still published as an identical copy:
  `https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/stale-distribution-mister/db.json.zip`

This database is a clone of the official MiSTer distribution with one
difference: its Linux system stays on the `linux_release_20260912` image from
the official distribution's `all_releases` assets. Cores,
the MiSTer main binary, `menu.rbf`, cheats, filters, palettes and every other
file keep tracking the official distribution. It is meant for setups that need
to hold Linux back, for instance while a newer image misbehaves with a
particular board or peripheral, without giving up core updates.

The generator downloads the official `db.json.zip` and republishes that
document unchanged, except for its top-level `linux` section, which becomes
the reviewed release:

```json
{
  "hash": "7cec2206e2a1133aa307c541219aa08f",
  "size": 126546478,
  "url": "https://github.com/MiSTer-devel/Distribution_MiSTer/releases/download/all_releases/linux_release_20260912.7z",
  "version": "260912"
}
```

Linux images are published as versioned assets in the official distribution's
[`all_releases` release](https://github.com/MiSTer-devel/Distribution_MiSTer/releases/tag/all_releases).
The hash and size were verified against that exact asset when the pin was
reviewed, and `generate_db.py --verify-linux-payload` re-downloads and re-checks
it on demand.

## Installation

Open `/media/fat/downloader.ini` and find the `[distribution_mister]` section. Set its db_url line to the value shown below.

If the section doesn’t exist, add both lines:

```ini
[distribution_mister]
db_url = https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/distribution-mister-pinned-linux/db.json.zip
```

Then run the update_all as usual.

This database was first published as `stale-distribution-mister`. A
`downloader.ini` that still points at that URL keeps working: the generator
writes a byte-for-byte copy of this bundle to the old path on every build, so
there is no need to edit it.
