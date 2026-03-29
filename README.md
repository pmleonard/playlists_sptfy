# playlists_sptfy

Process Spotify songs from JSON + tag import files, enrich metadata, and produce duplicate reports.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
make setup-dev
pytest -q
python -m playlists_sptfy
playlists-sptfy
```

If you use JetBrains IDEs, set the project interpreter to `.venv/bin/python` (for this repo: `/home/philipmleonard/StudioProjects/playlists_sptfy/.venv/bin/python`) to avoid false missing-package warnings in `pyproject.toml`.

`make` targets auto-prepend `.venv/bin` to `PATH` when `.venv` exists, so commands like `make ci-local` work without manual PATH overrides.

Common shortcuts:

```bash
make bootstrap
make bootstrap-force
make setup-dev
make ci-local
make test
make run
make lint
make precommit
```

## What the app does

1. Loads songs from the path specified in `song_list_path`
2. Imports additional song links from `data/songs_import/{tag}.txt` where `{tag}` is the filename
3. Uses the file name as tag (example: `rock.txt` -> `rock`)
4. Normalizes tags to lowercase and removes per-song duplicate tags
5. Merges duplicate songs by `link`
6. Validates song rows and drops invalid entries before export
7. Writes outputs:
   - `song_list_path`
   - `songs_csv_path`
   - `run_summary_path`
   - `duplicates_path`
   - `duplicates_report_path`
   - `playlist_export_path`
8. Applies optional tag filtering to playlist text export

## Settings

`data/settings/settings.json` (runtime flags):

- `settings_version`: settings schema version (currently `1`)
- `metadata_enabled`: if `false`, skip network metadata enrichment in `process_songs`
- `strict_mode`: if `true`, fail fast on invalid song rows instead of dropping them
- `dry_run`: if `true`, runs the pipeline without writing output files
- `log_level`: runtime logging level (`CRITICAL`, `ERROR`, `WARNING`, `INFO`, `DEBUG`)
- `max_ctr`: max number of songs to metadata-enrich per run
- `http_timeout_seconds`: per-request timeout for metadata HTTP calls
- `http_max_attempts`: max HTTP attempts per metadata URL (initial + retries)
- `http_retry_backoff_seconds`: exponential backoff base seconds between retries
- `http_retry_jitter_seconds`: max random jitter seconds added to each retry delay

`data/settings/config.json` (paths and filtering):

- `song_list_path`: input/output song list JSON path
- `duplicates_path`: duplicate groups JSON output path
- `duplicates_report_path`: duplicate groups markdown output path
- `songs_csv_path`: songs CSV output path
- `run_summary_path`: run summary JSON output path
  - Includes per-run counts, retry metrics, and effective HTTP timeout/retry settings
- `playlist_export_path`: plain-text song link export path
- `grouped_songs_path`: grouped song definitions used to keep grouped songs adjacent after randomization
- `tags_filter`: include/exclude tag filter for playlist text export

Example filter:

```json
{
  "tags_filter": {
    "include": ["preferred"],
    "exclude": ["skip", "skipa", "skipb"]
  }
}
```

This keeps songs tagged `preferred`, but removes any song that also has one of the excluded tags.
Tag matching is exact after normalization, so if you need to exclude tag variants, list each one explicitly.

Note: `songs_csv_path` remains the canonical unfiltered catalog export.

When `dry_run` is enabled, no files are written; intended output paths and counts are logged instead.

## Input files

Input files are gitignored and must be created manually.

Quick setup helper:

```bash
make bootstrap
```

This creates `data/settings/settings.json` from `data/settings/default_settings.json`,
`data/settings/config.json` from `data/settings/default_config.json`, and
`data/song_lists/songs.json` from `data/song_lists/songs.template.json` when they are missing.

To force-refresh both files from defaults/templates (overwriting local changes):

```bash
make bootstrap-force
```

### Song list JSON

Create `data/song_lists/songs.json` as a JSON array of song objects.
Required keys per song object: `link`, `artist`, `title`, `released`, `duration`, `album`, `track`, `tags`.

Quick start from template:

```bash
cp data/song_lists/songs.template.json data/song_lists/songs.json
```

### Tag import files

Create one `.txt` file per tag in `data/songs_import/`.
Each non-empty line is a song link. Lines starting with `#` are ignored.

Example `data/songs_import/roadtrip.txt`:

```text
https://open.spotify.com/track/abc123
https://open.spotify.com/track/def456
# comment
https://open.spotify.com/track/ghi789
```

The playlist export text file uses this same one-link-per-line format.

## Troubleshooting

- If `data/settings/settings.json` or `data/settings/config.json` is missing, they are auto-created from
  `data/settings/default_settings.json` and `data/settings/default_config.json`.
- Older `settings.json` and `config.json` files are auto-migrated during startup when possible.
- If running `src/playlists_sptfy/main.py` directly fails in your environment, use package mode:

```bash
python -m playlists_sptfy
```

- If playlist output is unexpectedly empty, check `tags_filter` in `data/settings/config.json`.
- To validate `settings.json` and `config.json` without running the pipeline:

```bash
python -m playlists_sptfy --validate-config
```

## Development tooling

- Lint locally with:

```bash
make lint
```

- Run pre-commit hooks locally:

```bash
make precommit
```

- CI runs lint + tests on push and pull requests via `.github/workflows/ci.yml`.

## Directory structure

```text
playlists_sptfy/
|-- .github/
|   `-- workflows/
|       `-- ci.yml
|-- data/
|   |-- playlist_export/
|   |-- settings/
|   |   |-- config.json
|   |   |-- default_config.json
|   |   |-- default_settings.json
|   |   `-- settings.json
|   |-- song_lists/
|   |   |-- grouped_songs.json
|   |   |-- run_summary.json
|   |   |-- songs.csv
|   |   |-- songs.json
|   |   `-- songs.template.json
|   `-- songs_import/
|-- src/
|   `-- playlists_sptfy/
|       |-- __init__.py
|       |-- __main__.py
|       |-- config.py
|       |-- exporters.py
|       |-- grouping.py
|       |-- main.py
|       `-- tags.py
|-- tests/
|   `-- tests.py
|-- CONTRIBUTING.md
|-- Makefile
|-- pyproject.toml
`-- README.md
```

See `CONTRIBUTING.md` for contributor workflow and PR checklist.
