# Sonic Mania MiSTer database

- Database ID: `MultiDatabases_MiSTer/sonic-mania`
- Upstream:
  [`kimchiman52/sonic-mania-mister`](https://github.com/kimchiman52/sonic-mania-mister)
- Database URL:
  `https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/sonic-mania/db.json.zip`

The generator follows the latest GitHub release ZIP and selectively maps its
launcher, `_Other` files, and `games/sonic-mania` runtime into their MiSTer
locations. README/license files and any bundled `Data.rsdk` placeholder are
excluded.

The real `Data.rsdk` game data is not included. `MiSTer.ini` is not modified.

Add this section to `downloader.ini`:

```ini
[MultiDatabases_MiSTer/sonic-mania]
db_url = https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/sonic-mania/db.json.zip
```

Generate only this database with:

```bash
python3 sonic-mania/generate_db.py
```
