# MiSTer Duke3D database

- Database ID: `MultiDatabases_MiSTer/duke3d`
- Upstream: [`neofreno/Mister_Duke3d`](https://github.com/neofreno/Mister_Duke3d)
- Database URL:
  `https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/duke3d/db.json.zip`

The generator follows the latest GitHub release asset named
`Mister_duke3d_YYYYMMDD.zip`. It installs the launcher, RBF, runtime, libraries,
and other files published in that ZIP.

`DUKE3D.GRP` is not included. `MiSTer.ini` is not modified.

Add this section to `downloader.ini`:

```ini
[MultiDatabases_MiSTer/duke3d]
db_url = https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/duke3d/db.json.zip
```

Generate only this database with:

```bash
python3 duke3d/generate_db.py
```
