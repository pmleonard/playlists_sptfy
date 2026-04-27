# Data storage

JSON files are organized by purpose:

- `song_lists/`: primary song data and duplicate reports
- `songs_import/`: tag-based import text files (`{tag}.txt`)
- `playlist_export/`: exported playlist text outputs
- `settings/`: app settings JSON files

## `song_lists/`

- `songs.json`: canonical list of song objects
- `songs.template.json`: starter template to copy into `songs.json`
- `songs.csv`: CSV export of the canonical song list
- `run_summary.json`: run metrics summary for the latest execution, including effective HTTP timeout/retry settings
- `ignore_duplicates.json`: known duplicate groups to suppress in duplicate outputs
- `possible_duplicates.json`: duplicate groups keyed by title prefix
- `possible_duplicates.md`: markdown summary of duplicates

## `playlist_export/`

- `playlist.txt`: one song link per line, matching the `songs_import/*.txt` format

## `songs_import/`

Each file name becomes a tag.

- `rock.txt` -> tag `rock`
- `xmas.txt` -> tag `xmas`

Each non-empty line is a song link. Lines starting with `#` are ignored.

Tag filters match explicit normalized tags, so seasonal variants like `xmasa`, `xmase`, `xmasf`, and similar should be listed individually when excluding them.

## `settings/`

`settings.json` currently includes:

- `settings_version`
- `metadata_enabled`
- `strict_mode`
- `dry_run`
- `log_level`
- `max_ctr`
- `http_timeout_seconds`
- `http_max_attempts`
- `http_retry_backoff_seconds`
- `http_retry_jitter_seconds`

`config.json` currently includes:

- `song_list_path`
- `duplicates_path`
- `duplicates_report_path`
- `ignore_duplicates_path`
- `songs_csv_path`
- `run_summary_path`
- `playlist_export_path`
- `grouped_songs_path`
- `tags_filter`

