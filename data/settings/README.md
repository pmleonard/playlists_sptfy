# Settings Configuration

This directory contains:

- `settings.json`: runtime flags and processing behavior
- `config.json`: file paths and tag filtering behavior

## Example Configuration

`settings.json` example:

```json
{
    "settings_version": 1,
    "metadata_enabled": true,
    "strict_mode": false,
    "dry_run": false,
    "log_level": "INFO",
    "max_ctr": 500,
    "http_timeout_seconds": 10,
    "http_max_attempts": 3,
    "http_retry_backoff_seconds": 1,
    "http_retry_jitter_seconds": 0
}
```

`config.json` example:

```json
{
    "song_list_path": "data/song_lists/songs.json",
    "duplicates_path": "data/song_lists/duplicates.json",
    "duplicates_report_path": "data/song_lists/duplicates.md",
    "songs_csv_path": "data/song_lists/songs.csv",
    "run_summary_path": "data/song_lists/run_summary.json",
    "playlist_export_path": "data/playlist_export/songs.txt",
    "grouped_songs_path": "data/song_lists/grouped_songs.json",
    "tags_filter": {
        "include": [],
        "exclude": []
    }
}
```

## Configuration Keys

### Paths and filters (`config.json`)

All paths are relative to the project root.

- **`song_list_path`**: Input/output path for the canonical song list JSON file
  - Used to load songs at startup and save processed results

- **`duplicates_path`**: Output path for grouped duplicate songs JSON file
  - Contains songs grouped by matching title prefixes

- **`duplicates_report_path`**: Output path for human-readable duplicate report
  - Markdown format with artist, title, and album columns

- **`songs_csv_path`**: Output path for CSV export of song list
  - Contains all song fields: link, artist, title, released, duration, album, track, tags

- **`run_summary_path`**: Output path for run metrics summary JSON
  - Contains counts for loaded/imported/deduped/filtered/grouped songs, retry metrics, and effective HTTP settings

- **`playlist_export_path`**: Output path for randomized playlist links
  - One Spotify link per line, shuffled for variety

- **`grouped_songs_path`**: Input path for grouped song definitions
  - Used to keep grouped songs adjacent after randomization

- **`tags_filter`**: Include/exclude tag logic for playlist text export
  - `include` (list): Keep only songs with at least one of these tags. Empty = include all.
  - `exclude` (list): Remove any song with any of these tags. Empty = exclude none.

### Runtime settings (`settings.json`)

- **`settings_version`**: Settings schema version
  - Current supported version: `1`

- **`metadata_enabled`**: Metadata enrichment toggle
  - If `false`, skip network metadata extraction in `process_songs`

- **`strict_mode`**: Validation behavior toggle
  - If `true`, fail fast when invalid song rows are detected

- **`dry_run`**: Pipeline mode toggle
  - If `true`, skip writing outputs and only log intended write actions

- **`log_level`**: Runtime logging verbosity
  - Allowed values: `CRITICAL`, `ERROR`, `WARNING`, `INFO`, `DEBUG`

Example:

```json
{
  "tags_filter": {
    "include": ["featured"],
    "exclude": ["blocked"]
  }
}
```

This keeps songs tagged `featured`, but removes any song that also has the `blocked` tag.
To exclude multiple tag variants, list each one separately:

```json
{
  "tags_filter": {
    "include": ["preferred"],
    "exclude": ["skip", "skipa", "skipb", "skipc"]
  }
}
```

Note: Tag matching is exact and case-insensitive after normalization. Use separate tag names for variants.
`songs_csv_path` remains an unfiltered canonical catalog export.

### Processing

- **`max_ctr`**: Maximum number of songs to fetch metadata for per run
  - Default: `500`
  - Limits API calls when enriching song data from Spotify

- **`http_timeout_seconds`**: HTTP timeout per metadata request
  - Default: `10`
  - Must be `>= 1`

- **`http_max_attempts`**: Total metadata request attempts per URL
  - Default: `3`
  - Must be `>= 1`

- **`http_retry_backoff_seconds`**: Exponential backoff base for retries
  - Default: `1`
  - Must be `>= 1`

- **`http_retry_jitter_seconds`**: Random jitter cap added to retry backoff
  - Default: `0`
  - Must be `>= 0`

## Notes

- All paths are relative to the project root
- Empty `include` list means all songs are eligible (unless excluded)
- Empty `exclude` list means no filtering on exclusion
- Tag matching happens after normalization (lowercase, deduplicated, sorted)
- Settings and config files are normalized automatically during app startup.
