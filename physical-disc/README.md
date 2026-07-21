# Physical Disc database

- Database ID:
  [`MultiDatabases/physical-disc`](https://theypsilon.github.io/DB-Inspector_MiSTer/?database-url=https%3A%2F%2Fraw.githubusercontent.com%2Ftheypsilon%2FMultiDatabases_MiSTer%2Fdb%2Fphysical-disc%2Fdb.json)
- Upstream:
  [`Anime0t4ku/Main_MiSTer_Physical_Disc`](https://github.com/Anime0t4ku/Main_MiSTer_Physical_Disc)
- Database URL:
  `https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/physical-disc/db.json`

This database installs the physical-CD MiSTer main plus its MGL launchers so
that supported systems load a disc automatically from a USB optical drive. It
follows the latest published release of `Anime0t4ku/Main_MiSTer_Physical_Disc`,
selecting the ZIP that matches the expected firmware-and-launcher layout. Most
systems (PlayStation, Mega CD, TurboGrafx-16 CD / PC Engine CD, and Sega
Saturn) reuse their official stable cores, so only their MGL launchers are
installed. Philips CD-i is the exception: its stable core does not work with
physical discs, so the release bundles an experimental CD-i core fork that this
database installs alongside the launchers.

## Installation

Download
[`downloader_MultiDatabases_physical-disc.zip`](https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/physical-disc/downloader_MultiDatabases_physical-disc.zip),
extract it to `/media/fat` on the MiSTer SD card, and run the MiSTer updaters.

Add this section to `/media/fat/MiSTer.ini`:

```ini
[CD-*]
main=MiSTer_Physical-CD
```

Use a supported USB optical drive that MiSTer exposes as `/dev/sr0`. Launch the
desired system from `_Physical Disc Cores`, and insert your own compatible game
disc. No disc-image game files are required. Keep any other optical-disc
reader, including Zaparoo's, disabled during playback so it does not compete for
the drive. The official PlayStation, Mega CD, TurboGrafx-16 CD, and Sega Saturn
cores must already be installed from the standard MiSTer distribution; this
database supplies only the physical-CD main, the MGL launchers, and the CD-i
core fork.

Install these BIOS files from your own hardware:

- Mega CD: `/media/fat/games/MegaCD/boot.rom`
- PlayStation: `/media/fat/games/PSX/boot.rom` for the US BIOS; optional
  `boot1.rom` and `boot2.rom` provide Japanese and European BIOSes
- TurboGrafx-CD / PC Engine CD: `/media/fat/games/TGFX16-CD/cd_bios.rom`
- Sega Saturn: place your Saturn BIOS in `/media/fat/games/Saturn/`
- Philips CD-i: place your CD-i BIOS in `/media/fat/games/CD-i/`

The database supplies the custom MiSTer main, the MGL launchers, and the CD-i
core fork. It does not supply BIOS files, games, or the official stable cores.
