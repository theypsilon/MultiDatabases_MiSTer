# MultiDatabases MiSTer

This repository generates independent custom databases for the
[MiSTer Downloader](https://github.com/MiSTer-devel/Downloader_MiSTer).
Each database follows an upstream project and installs only the files published
by that project. Commercial game data, BIOS files, and `MiSTer.ini` changes are
outside the databases.

| Folder | Database ID | Upstream |
| --- | --- | --- |
| [`dreamster`](dreamster/) | `MultiDatabases_MiSTer/dreamster` | `skmp/DreamSTer` |
| [`duke3d`](duke3d/) | `MultiDatabases_MiSTer/duke3d` | `neofreno/Mister_Duke3d` |
| [`mister-quake`](mister-quake/) | `MultiDatabases_MiSTer/mister-quake` | `neofreno/Mister_Quake` |
| [`sonic-mania`](sonic-mania/) | `MultiDatabases_MiSTer/sonic-mania` | `kimchiman52/sonic-mania-mister` |
| [`paprium`](paprium/) | `MultiDatabases_MiSTer/paprium` | `MisterPezz82/Paprium_MegaDrive_MiSTer` |

## Published databases

Generation runs manually and every 20 minutes through GitHub Actions. The
workflow force-publishes the generated files to the orphan `db` branch, using
this layout:

```text
<folder>/
  db.json
  db.json.zip
  downloader_MultiDatabases_MiSTer_<folder>.ini
  downloader_MultiDatabases_MiSTer_<folder>.zip
```

For example, DreamSTer is published at:

```text
https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/dreamster/db.json.zip
```

Each folder README contains its database URL and `downloader.ini`
configuration.

## Generate locally

The generators use only the Python standard library and download the current
upstream release assets:

```bash
python3 scripts/generate_all.py
python3 scripts/validate_bundles.py dist
```

To generate one database:

```bash
python3 dreamster/generate_db.py
```

Use `--repository owner/repository` when generating for a fork. This changes
the generated `db_url`; database IDs remain fixed under
`MultiDatabases_MiSTer/<folder>`.
