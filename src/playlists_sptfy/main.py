import json
import logging
import random
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from .config import load_settings as load_settings_from_paths
from .exporters import (
    write_duplicates_markdown,
    write_json_file,
    write_song_links_txt,
    write_songs_csv,
)
from .grouping import group_randomized_songs, load_grouped_songs
from .tags import merge_tags, normalize_tags, tag_filter_songs

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SETTINGS_PATH = PROJECT_ROOT / "data" / "settings" / "settings.json"
CONFIG_PATH = PROJECT_ROOT / "data" / "settings" / "config.json"
DEFAULT_SETTINGS_PATH = PROJECT_ROOT / "data" / "settings" / "default_settings.json"
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "data" / "settings" / "default_config.json"
SONGS_IMPORT_DIR = PROJECT_ROOT / "data" / "songs_import"
REQUEST_TIMEOUT_SECONDS = 10
REQUEST_MAX_ATTEMPTS = 3
REQUEST_RETRY_BACKOFF_SECONDS = 1
REQUEST_RETRY_JITTER_SECONDS = 0.5
PROGRESS_LOG_INTERVAL = 100
_HTTP_SESSION = requests.Session()
_HTTP_CONFIG = {
    "timeout_seconds": REQUEST_TIMEOUT_SECONDS,
    "max_attempts": REQUEST_MAX_ATTEMPTS,
    "retry_backoff_seconds": REQUEST_RETRY_BACKOFF_SECONDS,
    "retry_jitter_seconds": REQUEST_RETRY_JITTER_SECONDS,
}
_META_CACHE: dict[str, list] = {}
_RETRY_METRICS = {"retries": 0, "failed_urls": 0, "http_errors": 0}
logger = logging.getLogger(__name__)
REQUIRED_SONG_FIELDS = [
    "link",
    "artist",
    "title",
    "released",
    "duration",
    "album",
    "track",
    "tags",
]


def load_settings() -> dict:
    return load_settings_from_paths(
        SETTINGS_PATH,
        DEFAULT_SETTINGS_PATH,
        CONFIG_PATH,
        DEFAULT_CONFIG_PATH,
    )


def reset_runtime_state() -> None:
    _META_CACHE.clear()
    _RETRY_METRICS["retries"] = 0
    _RETRY_METRICS["failed_urls"] = 0
    _RETRY_METRICS["http_errors"] = 0


def configure_http_from_settings(settings: dict) -> None:
    _HTTP_CONFIG["timeout_seconds"] = settings.get("http_timeout_seconds", REQUEST_TIMEOUT_SECONDS)
    _HTTP_CONFIG["max_attempts"] = settings.get("http_max_attempts", REQUEST_MAX_ATTEMPTS)
    _HTTP_CONFIG["retry_backoff_seconds"] = settings.get(
        "http_retry_backoff_seconds",
        REQUEST_RETRY_BACKOFF_SECONDS,
    )
    _HTTP_CONFIG["retry_jitter_seconds"] = settings.get(
        "http_retry_jitter_seconds",
        REQUEST_RETRY_JITTER_SECONDS,
    )


def main():
    settings = load_settings()
    logging.basicConfig(level=getattr(logging, settings["log_level"]))
    reset_runtime_state()
    configure_http_from_settings(settings)

    song_list_path = PROJECT_ROOT / settings["song_list_path"]
    duplicates_path = PROJECT_ROOT / settings["duplicates_path"]
    duplicates_report_path = PROJECT_ROOT / settings["duplicates_report_path"]
    songs_csv_path = PROJECT_ROOT / settings["songs_csv_path"]
    playlist_export_path = PROJECT_ROOT / settings["playlist_export_path"]
    grouped_songs_path = PROJECT_ROOT / settings["grouped_songs_path"]
    run_summary_path = PROJECT_ROOT / settings["run_summary_path"]
    metadata_enabled = settings["metadata_enabled"]
    strict_mode = settings["strict_mode"]
    dry_run = settings["dry_run"]
    tags_filter = settings["tags_filter"]
    max_ctr = int(settings["max_ctr"])

    ensure_json_list_file(song_list_path)
    ensure_json_list_file(grouped_songs_path)

    songs = open_json_file(song_list_path)
    loaded_song_count = len(songs)
    imported_songs = load_songs_from_tag_files(SONGS_IMPORT_DIR)
    imported_song_count = len(imported_songs)
    songs.extend(imported_songs)
    songs = remove_duplicates(songs)
    deduped_song_count = len(songs)
    if metadata_enabled:
        songs = process_songs(songs, max_ctr)
    else:
        logger.info("Metadata enrichment disabled; skipping process_songs.")

    songs, invalid_song_count = validate_song_rows(songs, strict_mode=strict_mode)
    if invalid_song_count:
        logger.warning("Dropped %d invalid songs during validation", invalid_song_count)

    possible_duplicates = find_duplicates(songs, 25)
    filtered_songs = tag_filter_songs(songs, tags_filter)
    filtered_song_count = len(filtered_songs)

    # Playlist export is randomized, then re-grouped to keep linked tracks adjacent.
    random.shuffle(filtered_songs)
    grouped_songs = load_grouped_songs(grouped_songs_path)
    filtered_songs = group_randomized_songs(filtered_songs, grouped_songs)
    grouped_filtered_song_count = len(filtered_songs)

    run_summary = {
        "loaded": loaded_song_count,
        "imported": imported_song_count,
        "deduped": deduped_song_count,
        "filtered": filtered_song_count,
        "grouped": grouped_filtered_song_count,
        "duplicate_groups": len(possible_duplicates),
        "invalid": invalid_song_count,
        "retries": _RETRY_METRICS["retries"],
        "failed_urls": _RETRY_METRICS["failed_urls"],
        "http_errors": _RETRY_METRICS["http_errors"],
        "http_timeout_seconds": int(_HTTP_CONFIG["timeout_seconds"]),
        "http_max_attempts": int(_HTTP_CONFIG["max_attempts"]),
        "http_retry_backoff_seconds": int(_HTTP_CONFIG["retry_backoff_seconds"]),
        "http_retry_jitter_seconds": int(_HTTP_CONFIG["retry_jitter_seconds"]),
        "metadata_enabled": metadata_enabled,
        "dry_run": dry_run,
    }

    if dry_run:
        logger.info("Dry-run enabled; skipping file writes.")
        logger.info("Would write %d songs JSON to %s", len(songs), song_list_path)
        logger.info("Would write %d songs CSV rows to %s", len(songs), songs_csv_path)
        logger.info(
            "Would write %d duplicate groups JSON to %s",
            len(possible_duplicates),
            duplicates_path,
        )
        logger.info(
            "Would write %d duplicate groups markdown to %s",
            len(possible_duplicates),
            duplicates_report_path,
        )
        logger.info(
            "Would write %d playlist links to %s",
            len(filtered_songs),
            playlist_export_path,
        )
        logger.info("Would write run summary JSON to %s", run_summary_path)
    else:
        write_json_file(songs, song_list_path)
        # CSV is the canonical catalog export (unfiltered).
        write_songs_csv(songs, songs_csv_path)
        write_json_file(possible_duplicates, duplicates_path)
        write_duplicates_markdown(possible_duplicates, duplicates_report_path)
        write_song_links_txt(filtered_songs, playlist_export_path)
        write_json_file(run_summary, run_summary_path)

    logger.info(
        (
            "Run summary: loaded=%d imported=%d deduped=%d "
            "filtered=%d grouped=%d duplicate_groups=%d invalid=%d retries=%d failed_urls=%d "
            "http_errors=%d metadata_enabled=%s strict_mode=%s dry_run=%s"
        ),
        loaded_song_count,
        imported_song_count,
        deduped_song_count,
        filtered_song_count,
        grouped_filtered_song_count,
        len(possible_duplicates),
        invalid_song_count,
        _RETRY_METRICS["retries"],
        _RETRY_METRICS["failed_urls"],
        _RETRY_METRICS["http_errors"],
        metadata_enabled,
        strict_mode,
        dry_run,
    )


def validate_song_rows(songs: list[dict], strict_mode: bool = False) -> tuple[list[dict], int]:
    valid = []
    invalid_count = 0
    for song in songs:
        if not isinstance(song, dict):
            if strict_mode:
                raise ValueError("Invalid song row: expected object")
            invalid_count += 1
            continue
        missing_fields = [field for field in REQUIRED_SONG_FIELDS if field not in song]
        if missing_fields:
            if strict_mode:
                raise ValueError(f"Invalid song row: missing fields {missing_fields}")
            invalid_count += 1
            logger.debug("Skipping song missing fields %s: %s", missing_fields, song)
            continue

        link = str(song.get("link", "")).strip()
        if not link:
            if strict_mode:
                raise ValueError("Invalid song row: blank link")
            invalid_count += 1
            logger.debug("Skipping song with blank link: %s", song)
            continue

        # Keep tags canonical before export.
        song["tags"] = normalize_tags(song.get("tags", ""))
        valid.append(song)
    return valid, invalid_count


def open_json_file(file):
    with open(file, encoding="utf-8") as f:
        songs = json.load(f)
    # Keep tags canonical at load-time so downstream filtering/merging is consistent.
    for song in songs:
        song["tags"] = normalize_tags(song.get("tags", ""))
    return songs


def ensure_json_list_file(path: Path) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        file.write("[]\n")


def build_song_entry(link: str, tag: str) -> dict:
    return {
        "link": link,
        "artist": "",
        "title": "",
        "released": "",
        "duration": "",
        "album": "",
        "track": "",
        "tags": normalize_tags(tag),
    }


def load_songs_from_tag_files(import_dir: Path) -> list[dict]:
    imported_songs: list[dict] = []
    if not import_dir.exists():
        return imported_songs

    for txt_file in sorted(import_dir.glob("*.txt")):
        tag = txt_file.stem.strip()
        if not tag:
            continue
        with open(txt_file, encoding="utf-8") as file:
            for line in file:
                link = line.strip()
                if not link or link.startswith("#"):
                    continue
                imported_songs.append(build_song_entry(link, tag))
    return imported_songs


def remove_duplicates(songs):
    songs_obj = {}
    for song in songs:
        song["tags"] = normalize_tags(song.get("tags", ""))
        link = song["link"]
        if link not in songs_obj:
            songs_obj[link] = song
        else:
            songs_obj[link]["tags"] = merge_tags(songs_obj[link]["tags"], song["tags"])
    return list(songs_obj.values())


def find_duplicates(songs, num_chars):
    summary = {}
    dups = {}
    for song in songs:
        ttl = song["title"]
        if not isinstance(ttl, str):
            ttl = str(ttl)
        short = ttl[:num_chars]
        summary.setdefault(short, []).append(song)
    for short, entries in summary.items():
        if len(entries) > 1:
            dups[short] = entries
    return dups


def process_songs(songs, max_ctr):
    ctr = 0
    total = len(songs)
    for i, song in enumerate(songs):
        if song["artist"] == "" and ctr < max_ctr:
            songs[i] = extract_meta(song)
            ctr += 1
        songs[i]["tags"] = normalize_tags(song.get("tags", ""))
        current = i + 1
        logger.debug("Processed song %d/%d", current, total)
        if current % PROGRESS_LOG_INTERVAL == 0 or current == total:
            logger.info("Processed %d/%d songs", current, total)
    return songs


def extract_meta(song):
    try:
        url = song["link"]
        song["tags"] = normalize_tags(song.get("tags", ""))
        meta = get_url_meta(url)
        meta_obj = {}
        for tag in meta:
            if "name" in tag.attrs and tag.attrs["name"].strip().lower() in [
                "music:musician_description",
                "music:release_date",
                "music:duration",
                "music:album:track",
                "music:album",
            ]:
                meta_obj[tag.attrs["name"]] = tag.attrs["content"]
            if "property" in tag.attrs and tag.attrs["property"].strip().lower() in ["og:title"]:
                meta_obj[tag.attrs["property"]] = tag.attrs["content"]
        song["artist"] = meta_obj.get("music:musician_description", "")
        song["title"] = meta_obj.get("og:title", "")
        song["released"] = meta_obj.get("music:release_date", "")
        song["duration"] = meta_obj.get("music:duration", "")
        song["album"] = extract_album(meta_obj.get("music:album", ""))
        song["track"] = meta_obj.get("music:album:track", "")
    except Exception:
        logger.exception("Failed to extract metadata for song link: %s", song.get("link", ""))
    return song


def extract_album(url):
    response = ""
    try:
        meta = get_url_meta(url)
        for tag in meta:
            if "property" in tag.attrs and tag.attrs["property"].strip().lower() == "og:title":
                response = tag.attrs["content"]
    except Exception:
        logger.exception("Failed to extract album metadata from URL: %s", url)
    return response


def get_url_meta(url):
    cached = _META_CACHE.get(url)
    if cached is not None:
        return cached

    last_exception = None
    retryable_http_statuses = {429, 500, 502, 503, 504}

    max_attempts = int(_HTTP_CONFIG["max_attempts"])
    for attempt in range(1, max_attempts + 1):
        try:
            response = _HTTP_SESSION.get(url, timeout=float(_HTTP_CONFIG["timeout_seconds"]))
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            meta = soup.find_all("meta")
            _META_CACHE[url] = meta
            return meta
        except requests.HTTPError as exc:
            last_exception = exc
            status_code = exc.response.status_code if exc.response is not None else None
            _RETRY_METRICS["http_errors"] += 1
            retryable = status_code in retryable_http_statuses
            if not retryable or attempt == max_attempts:
                break
            _RETRY_METRICS["retries"] += 1
            wait_seconds = retry_backoff_with_jitter(attempt)
            logger.warning(
                "Transient HTTP %s for %s (attempt %d/%d), retrying in %.2fs",
                status_code,
                url,
                attempt,
                max_attempts,
                wait_seconds,
            )
            time.sleep(wait_seconds)
        except requests.RequestException as exc:
            last_exception = exc
            if attempt == max_attempts:
                break
            _RETRY_METRICS["retries"] += 1
            wait_seconds = retry_backoff_with_jitter(attempt)
            logger.warning(
                "Request error for %s (attempt %d/%d), retrying in %.2fs",
                url,
                attempt,
                max_attempts,
                wait_seconds,
            )
            time.sleep(wait_seconds)

    if last_exception is not None:
        _RETRY_METRICS["failed_urls"] += 1
        raise last_exception
    return []


def retry_backoff_with_jitter(attempt: int) -> float:
    base = float(_HTTP_CONFIG["retry_backoff_seconds"]) * (2 ** (attempt - 1))
    jitter = random.uniform(0, float(_HTTP_CONFIG["retry_jitter_seconds"]))
    return base + jitter


if __name__ == "__main__":
    main()
