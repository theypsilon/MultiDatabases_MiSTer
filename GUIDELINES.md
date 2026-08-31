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
- Prefer a loud failure over silently freezing on a stale version. Skipping an
  upstream release stays silent only when upstream marks it a draft or
  prerelease, or when it carries nothing the entry could install. Anything else
  that would leave a database parked on an older version must fail the
  generator: the expected artifact vanishing, being renamed, or becoming
  ambiguous, and a newer release that does carry a payload being passed over.
  Record a deliberate exception as a reviewed constant in the generator instead
  of widening the selection rule.
- Treat release notes and descriptions as human-facing prose, never as a
  machine-readable interface. Do not parse them for filenames, paths,
  configuration values, versions, or selection rules. Use structured release
  metadata and validate immutable artifacts instead; if a required value
  cannot be derived unambiguously, encode the reviewed value in the generator
  and fail closed when upstream changes it.
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
  contain only generated entry folders, and it is pushed only when the bundle
  tree differs from the published one. Unchanged bundles are byte-for-byte
  identical, so a build that changed nothing leaves `db` untouched.
- Derived payloads that have no upstream direct-file or ZIP URL are published
  on the append-only orphan `db-assets` branch under a content-addressed path.
  Never replace or remove a published asset. Database URLs must use the full
  commit that introduced the asset, not the branch name. The asset is pushed
  before Downloader integration testing so its pinned URL is reachable; the
  live `db` branch is still pushed only after every validation and integration
  test passes.
- Every published `db` commit is logged on the orphan `db-releases` branch:
  `.github/track_release.py` appends `<UTC timestamp>: <db commit>` to
  `commits.txt`, and to `<entry>/commits.txt` for every entry whose bundle
  changed in that commit, so each database can be traced in isolation and the
  history that force-pushing `db` drops stays recoverable by commit. The log is
  pushed without force, tracking never touches the build checkout, and a
  tracking failure warns instead of failing a run that already published.
- The workflow must run unit tests, generate every entry, validate every
  bundle, and pass the official MiSTer Downloader integration test before
  pushing the `db` branch.
- A failing generator must not hold back the other databases:
  `generate_all.py` restores that entry's previously published bundle, lists it
  in `.build/failures.txt`, and keeps going. Entries with no bundle at all are
  skipped by the later steps instead of failing them.
- The last workflow step reads `.build/failures.txt` and fails the run, so a
  broken entry leaves the build red after the healthy databases were pushed.
