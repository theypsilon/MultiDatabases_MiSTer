# Paprium MegaDrive database

- Database ID: `MultiDatabases_MiSTer/paprium`
- Upstream:
  [`MisterPezz82/Paprium_MegaDrive_MiSTer`](https://github.com/MisterPezz82/Paprium_MegaDrive_MiSTer)
- Database URL:
  `https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/paprium/db.json.zip`

The generator follows the newest `MegaDrive_Paprium_YYYYMMDD.rbf` asset in the
latest release. It installs that core and `PapriumMD.mgl`, creates
`games/PapriumMD`, marks core changes as requiring a reboot, and entangles
successive dated RBF files so a failed update does not remove the working core.
The launcher is maintained in this folder and served from the repository's
`main` branch.

Paprium ROM/WAV data is not included.

Add this section to `downloader.ini`:

```ini
[MultiDatabases_MiSTer/paprium]
db_url = https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/paprium/db.json.zip
```

Generate only this database with:

```bash
python3 paprium/generate_db.py
```
