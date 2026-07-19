# DreamSTer database

- Database ID: `MultiDatabases_MiSTer/dreamster`
- Upstream: [`skmp/DreamSTer`](https://github.com/skmp/DreamSTer)
- Database URL:
  `https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/dreamster/db.json.zip`

The generator follows the newest published DreamSTer release containing a
DreamSTer ZIP, including releases marked as pre-release. It installs the
upstream `Scripts/DreamSTer.sh` and `minicast` runtime and creates
`games/Dreamcast`.

Dreamcast BIOS files and games are not included. `MiSTer.ini` is not modified.

Add this section to `downloader.ini`:

```ini
[MultiDatabases_MiSTer/dreamster]
db_url = https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/dreamster/db.json.zip
```

Generate only this database with:

```bash
python3 dreamster/generate_db.py
```
