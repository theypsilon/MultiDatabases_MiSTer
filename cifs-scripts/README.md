# CIFS Scripts database

- Database ID:
  [`MultiDatabases/cifs-scripts`](https://theypsilon.github.io/DB-Inspector_MiSTer/?database-url=https%3A%2F%2Fraw.githubusercontent.com%2Ftheypsilon%2FMultiDatabases_MiSTer%2Fdb%2Fcifs-scripts%2Fdb.json)
- Upstream:
  [`MiSTer-devel/Scripts_MiSTer`](https://github.com/MiSTer-devel/Scripts_MiSTer)
- Database URL:
  `https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/cifs-scripts/db.json`

The generator follows the `master` branch of the official scripts repository
and installs only `Scripts/cifs_mount.sh` and `Scripts/cifs_umount.sh`, which
mount and unmount a CIFS/SMB network share on the MiSTer. Each script is served
from the newest upstream commit that changed it, so the database only updates
when one of the two scripts does. These are ARM shell scripts; no core is
installed.

## Installation

Download
[`downloader_MultiDatabases_cifs-scripts.zip`](https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/cifs-scripts/downloader_MultiDatabases_cifs-scripts.zip),
extract it to `/media/fat` on the MiSTer SD card, and run the MiSTer updaters.

No `MiSTer.ini` changes and no BIOS or game files are required.

## Usage

### Configure the share

Create `/media/fat/Scripts/cifs_mount.ini` next to the scripts. Keep your
settings there rather than editing `cifs_mount.sh`: the database overwrites the
scripts on update and never touches the INI file. It takes one `KEY="value"`
per line, and only `SERVER` is mandatory:

```ini
SERVER="192.168.1.10"
SHARE="MiSTer"
USERNAME="mister"
PASSWORD="secret"
LOCAL_DIR="cifs"
MOUNT_AT_BOOT="false"
```

| Option | Default | Meaning |
| --- | --- | --- |
| `SERVER` | empty | NAS or PC name, or its IP address. The script refuses to run while it is empty. |
| `SHARE` | `MiSTer` | Share name on the server. |
| `SHARE_DIRECTORY` | empty | Mount only this directory of the share instead of its root. |
| `USERNAME` | empty | Leave empty for guest access. |
| `PASSWORD` | empty | Ignored for guest access. |
| `DOMAIN` | empty | Optional user domain; leave empty when in doubt. |
| `LOCAL_DIR` | `cifs` | Where the share is mounted under `/media/fat`; see below. |
| `ADDITIONAL_MOUNT_OPTIONS` | empty | Extra `mount` options. For problems unrelated to the credentials, try `vers=2.0` or `vers=3.0`. |
| `WAIT_FOR_SERVER` | `false` | `true` waits up to 60 seconds for the server to become reachable. |
| `MOUNT_AT_BOOT` | `false` | `true` mounts the share on every boot; see below. |

`LOCAL_DIR` accepts three forms:

- A single directory such as `cifs` mounts the share on `/media/fat/cifs`.
  This is the suggested setting: MiSTer looks for games in `/media/fat/cifs`
  before `/media/fat/games`, so lay the share out like the SD card's `games`
  folder (`\\NAS\MiSTer\NES`, `\\NAS\MiSTer\SNES`, ...).
- A `|` separated list such as `Amiga|C64|NES` mounts each share subdirectory
  with that name on `/media/fat/Amiga`, `/media/fat/C64` and `/media/fat/NES`.
- `*` mounts every directory found on the share on the SD card directory with
  the same name, except `config`, `linux` and `System Volume Information`.

### Mount and unmount

Run `cifs_mount` from the MiSTer `Scripts` menu, or
`/media/fat/Scripts/cifs_mount.sh` over SSH. It reports each target as
`mounted`, `already mounted` or `not mounted`, and ends with `Done!` or with the
number of failures. If it says the kernel does not support CIFS, update the
MiSTer Linux system first.

Run `cifs_umount` to unmount what `cifs_mount.sh` mounted; it reads `LOCAL_DIR`
from the same `cifs_mount.ini`. A busy target falls back to a lazy unmount.
Over SSH, `cifs_umount.sh --all` unmounts every CIFS mount on the system
instead, including ones the mount script did not create.

### Mount at boot

Set `MOUNT_AT_BOOT="true"` and run `cifs_mount` once. The script registers
itself in `/media/fat/linux/user-startup.sh`, falling back to an `/etc/init.d`
entry when that file is unavailable, and from then on waits for the network
and the server on each boot before mounting. Boot runs are logged to
`/tmp/cifs_mount.log`. To disable it, set `MOUNT_AT_BOOT="false"` and run
`cifs_mount` once more; that run removes the boot entry.
