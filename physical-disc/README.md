# Physical Disc database

- Database ID:
  [`MultiDatabases/physical-disc`](https://theypsilon.github.io/DB-Inspector_MiSTer/?database-url=https%3A%2F%2Fraw.githubusercontent.com%2Ftheypsilon%2FMultiDatabases_MiSTer%2Fdb%2Fphysical-disc%2Fdb.json)
- Upstream:
  [`Anime0t4ku/*_Physical_Disc`](https://github.com/Anime0t4ku?tab=repositories)
- Database URL:
  `https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/physical-disc/db.json`

This database installs physical CD core forks and custom firmware. It follows
the latest published release from every public `Anime0t4ku` repository whose
name ends in `_Physical_Disc`, selecting the ZIP that matches the expected
firmware or core-package layout. Other ZIP assets may coexist in the release;
a repository without one unambiguous compatible package fails validation
instead of being silently omitted.

## Installation

Download
[`downloader_MultiDatabases_physical-disc.zip`](https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/physical-disc/downloader_MultiDatabases_physical-disc.zip),
extract it to `/media/fat` on the MiSTer SD card, and run the MiSTer updaters.

Add this section to `/media/fat/MiSTer.ini`:

```ini
[CD-*]
main=MiSTer_Physical-CD
```

Use a supported USB optical drive that MiSTer exposes as `/dev/sr0`. Launch
the desired system from `_Physical Disc Cores`, enable its physical-disc
option, and insert your own compatible game disc. No disc-image game files are
required. Keep any other optical-disc reader, including Zaparoo's, disabled
during playback so it does not compete for the drive.

Install these BIOS files from your own hardware:

- Mega CD: `/media/fat/games/MegaCD/boot.rom`
- PlayStation: `/media/fat/games/PSX/boot.rom` for the US BIOS; optional
  `boot1.rom` and `boot2.rom` provide Japanese and European BIOSes
- TurboGrafx-CD / PC Engine CD:
  `/media/fat/games/TGFX16-CD/cd_bios.rom`

The database supplies the custom MiSTer main, physical-disc cores, and their
MGL launchers. It does not supply BIOS files or games.
