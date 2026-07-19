# MultiDatabases MiSTer

This repository generates independent custom databases for the
[MiSTer Downloader](https://github.com/MiSTer-devel/Downloader_MiSTer).
Each database follows an upstream project and installs only the files published
by that project. Commercial game data, BIOS files, and `MiSTer.ini` changes are
outside the databases.

| Folder | Database ID | Upstream |
| --- | --- | --- |
| [`dreamster`](dreamster/) | `MultiDatabases/dreamster` | `skmp/DreamSTer` |
| [`duke3d`](duke3d/) | `MultiDatabases/duke3d` | `neofreno/Mister_Duke3d` |
| [`mister-quake`](mister-quake/) | `MultiDatabases/mister-quake` | `neofreno/Mister_Quake` |
| [`sonic-mania`](sonic-mania/) | `MultiDatabases/sonic-mania` | `kimchiman52/sonic-mania-mister` |
| [`paprium`](paprium/) | `MultiDatabases/paprium` | `MisterPezz82/Paprium_MegaDrive_MiSTer` |

Open a database folder above for its installation instructions.

## Published files

GitHub Actions publishes the database files to the orphan `db` branch using
this layout:

```text
<folder>/
  db.json
  db.json.zip
  downloader_MultiDatabases_<folder>.ini
  downloader_MultiDatabases_<folder>.zip
```

For example, DreamSTer is published at:

```text
https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/dreamster/db.json.zip
```
