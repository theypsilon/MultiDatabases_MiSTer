# SM64 H2X database

- Database ID:
  [`MultiDatabases/sm64-h2x`](https://theypsilon.github.io/DB-Inspector_MiSTer/?database-url=https%3A%2F%2Fraw.githubusercontent.com%2Ftheypsilon%2FMultiDatabases_MiSTer%2Fdb%2Fsm64-h2x%2Fdb.json)
- Upstream:
  [`DavidFallows/sm64`](https://github.com/DavidFallows/sm64)
- Database URL:
  `https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/sm64-h2x/db.json`

The generator follows the newest non-draft GitHub release, including
prereleases, and installs the SM64 H2X BPS patch and upstream patching
instructions in `games/N64/SM64 H2X`. H2X is an experimental Super Mario 64
modification that renders the game at 640×240 while retaining its original
320×240 logical layout. The database does not contain a Super Mario 64 ROM.

## Installation

The updater installs the patch and its upstream `README.txt`, not a playable
ROM. Complete these steps to create and play the game:

1. Download
   [`downloader_MultiDatabases_sm64-h2x.zip`](https://raw.githubusercontent.com/theypsilon/MultiDatabases_MiSTer/db/sm64-h2x/downloader_MultiDatabases_sm64-h2x.zip),
   extract it to `/media/fat` on the MiSTer SD card, and run the MiSTer
   updaters.
2. Confirm that these files were installed:

   - `/media/fat/games/N64/SM64 H2X/SM64 H2X.bps`
   - `/media/fat/games/N64/SM64 H2X/README.txt`

3. Supply your own legally obtained **Super Mario 64 (USA)** ROM. It must be
   the big-endian `.z64` version with this SHA-1:

   ```text
   9bef1128717f958171a4afac3ed78ee2bb4e86ce
   ```

   A differently ordered `.n64` or `.v64` dump, another region, or another
   revision will not work with this patch.
4. Access the SD card from a computer, or copy the installed BPS file to one.
   Open a BPS-compatible patcher such as Floating IPS, choose **Apply Patch**,
   select `SM64 H2X.bps`, and then select the verified `.z64` ROM as the source
   file.
5. Save the patched output with a descriptive `.z64` filename, such as
   `Super Mario 64 H2X.z64`. For the current `v1.0-rc1` release, the correctly
   patched ROM has this SHA-1:

   ```text
   305f9ac1878269f175dbfb585c8ea2a1a392dbd6
   ```

   If the installed upstream `README.txt` names a newer release, use the
   output checksum documented there instead.
6. Copy the patched `.z64` to `/media/fat/games/N64` on the MiSTer SD card.
   The original clean ROM and the BPS file do not need to be in the same folder
   as the patched ROM.
7. Start the standard N64 core, load the patched `.z64`, and set its memory to
   **8 MB / Expansion Pak** in the core OSD. The game will not run with the
   4 MB Jumper Pak setting.

No BIOS file or `MiSTer.ini` change is required. This entry uses the FPGA N64
core and has no ARM software component.
