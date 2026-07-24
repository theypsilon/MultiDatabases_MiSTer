# Repository guidelines

## Adding an entry

- Every root directory whose name does not start with `.` is an entry. Add
  `<slug>/generate_db.py` and `<slug>/README.md`; do not maintain a central
  folder list.
- Build databases through `.github/db_helpers.py`. Use
  `MultiDatabases/<slug>` as the ID. Choose the `db_url` when the entry is
  first added: the uncompressed `db/<slug>/db.json` by default, or the
  compressed `db/<slug>/db.json.zip` when that entry is expected to generate a
  database of 10 KB or more. `write_bundle` emits both files either way; only
  `db_url` decides which one users fetch.
- A published `db_url` must never change. Judge the size threshold from what
  the entry is expected to produce, never from a measurement taken during a
  run: the workflow must not move an entry between the two URLs, and neither an
  incremental change nor an entry later growing past 10 KB reopens the choice.
- Prefer the latest published release/version, but validate its expected files
  and layout before accepting it. Install only files intended for MiSTer.
- Emitted payload URLs must be immutable: use a concrete GitHub release tag or
  a raw GitHub URL pinned to a full 40-character commit. Never emit branch,
  `latest`, query-string, or other ephemeral URLs. Moving APIs may be used for
  discovery only.
- Use the shared path, hash, archive, URL, and database validation. Supply
  standard `filter_terms` and only the tag aliases needed by the entry.
- Add focused generator tests under `.github/test_entry_generators.py`.

## README requirements

- Add a compact row to the main README. Link the database name to its folder,
  and provide DB Inspector and proper upstream links.
- The entry README must include its inspector-linked ID, upstream and database
  URL, a short description, and installation instructions.
- Installation uses the generated drop-in ZIP: extract it to `/media/fat` and
  run the MiSTer updaters. Do not instruct users to edit `downloader.ini`.
- State every required `MiSTer.ini` change and user-supplied BIOS/game file, or
  explicitly say none are required. Identify hybrid FPGA/ARM software where
  applicable.

## Publication invariants

- Always publish with `write_bundle`. It compares database content without the
  timestamp and preserves an unchanged entry byte-for-byte, independently of
  changes to other entries.
- Keep generated bundles out of the source branch. The orphan `db` branch must
  contain only generated entry folders.
- The workflow must run unit tests, generate every entry, validate every
  bundle, and pass the official MiSTer Downloader integration test before
  pushing the `db` branch.
- A failing generator must not hold back the other databases:
  `generate_all.py` restores that entry's previously published bundle, lists it
  in `.build/failures.txt`, and keeps going. Entries with no bundle at all are
  skipped by the later steps instead of failing them.
- The last workflow step reads `.build/failures.txt` and fails the run, so a
  broken entry leaves the build red after the healthy databases were pushed.
