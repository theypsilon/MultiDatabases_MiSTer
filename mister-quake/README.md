# MiSTer Quake database

- Database ID: `MultiDatabases_MiSTer/mister-quake`
- Upstream: [`neofreno/Mister_Quake`](https://github.com/neofreno/Mister_Quake)
- Database URL:
  `https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/mister-quake/db.json.zip`

The generator follows the latest GitHub release asset named
`MiSTer_Quake_YYYYMMDD.zip`. It installs the launcher, RBF, runtime, libraries,
and other files published in that ZIP.

`PAK0.PAK` and `PAK1.PAK` are not included. `MiSTer.ini` is not modified.

Add this section to `downloader.ini`:

```ini
[MultiDatabases_MiSTer/mister-quake]
db_url = https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/mister-quake/db.json.zip
```

Generate only this database with:

```bash
python3 mister-quake/generate_db.py
```
