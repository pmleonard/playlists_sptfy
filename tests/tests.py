import importlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, cast

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

main_module = importlib.import_module("playlists_sptfy.main")
exporters_module = importlib.import_module("playlists_sptfy.exporters")
cli_module = importlib.import_module("playlists_sptfy.__main__")

find_duplicates = main_module.find_duplicates
get_url_meta = main_module.get_url_meta
group_randomized_songs = main_module.group_randomized_songs
load_grouped_songs = main_module.load_grouped_songs
load_songs_from_tag_files = main_module.load_songs_from_tag_files
merge_tags = main_module.merge_tags
normalize_tags = main_module.normalize_tags
open_json_file = main_module.open_json_file
remove_duplicates = main_module.remove_duplicates
tag_filter_songs = main_module.tag_filter_songs
validate_song_rows = main_module.validate_song_rows
write_duplicates_markdown = main_module.write_duplicates_markdown
write_song_links_txt = main_module.write_song_links_txt
write_songs_csv = main_module.write_songs_csv


def _song(link, artist, title, tags):
    return {
        "link": link,
        "artist": artist,
        "title": title,
        "released": "",
        "duration": 0,
        "album": "",
        "track": 0,
        "tags": tags,
    }


def test_merge_tags_combines_unique_tags() -> None:
    assert merge_tags("pop, rock", "rock, jazz") == "jazz, pop, rock"


def test_merge_tags_sorts_result() -> None:
    assert merge_tags("z-tag, a-tag", "m-tag") == "a-tag, m-tag, z-tag"


def test_normalize_tags_lowercases_and_deduplicates() -> None:
    assert normalize_tags("Rock, rock,  POP ,pop") == "pop, rock"


def test_tag_filter_songs_include_and_exclude_logic() -> None:
    songs = [
        _song("url1", "Artist A", "Song A", "featured"),
        _song("url2", "Artist B", "Song B", "FEATURED, blocked"),
        _song("url3", "Artist C", "Song C", "featured, rock"),
        _song("url4", "Artist D", "Song D", "blocked"),
        _song("url5", "Artist E", "Song E", "pop"),
        _song("url6", "Artist F", "Song F", "featured, blockedf"),
    ]

    filtered = tag_filter_songs(
        songs,
        {
            "include": ["featured"],
            "exclude": ["blocked", "blockeda", "blockedb", "blockedm", "blockedp", "blockedf"],
        },
    )

    assert [song["link"] for song in filtered] == ["url1", "url3"]


def test_tag_filter_songs_without_include_only_excludes_matches() -> None:
    songs = [
        _song("url1", "Artist A", "Song A", "rock"),
        _song("url2", "Artist B", "Song B", "pop, blocked"),
        _song("url3", "Artist C", "Song C", "jazz"),
    ]

    filtered = tag_filter_songs(songs, {"exclude": "blocked"})

    assert [song["link"] for song in filtered] == ["url1", "url3"]


def test_tag_filter_songs_exclude_exact_tag_does_not_remove_variant_tags() -> None:
    songs = [
        _song("url1", "Artist A", "Song A", "featured, blockedf"),
        _song("url2", "Artist B", "Song B", "featured, rock"),
    ]

    filtered = tag_filter_songs(songs, {"include": ["featured"], "exclude": ["blocked"]})

    assert [song["link"] for song in filtered] == ["url1", "url2"]


def test_find_duplicates_detects_similar_titles() -> None:
    songs = [
        _song("url1", "Artist A", "Same Song Title", "pop"),
        _song("url2", "Artist B", "Same Song Title", "rock"),
        _song("url3", "Artist C", "Unique Title", "jazz"),
    ]
    dups = find_duplicates(songs, 25)
    assert "Same Song Title" in dups
    assert "Unique Title" not in dups


def test_remove_duplicates_merges_tags() -> None:
    songs = [
        _song("url1", "Artist", "Title", "Pop, rock"),
        _song("url1", "Artist", "Title", "ROCK, Jazz"),
    ]
    result = remove_duplicates(songs)
    assert len(result) == 1
    assert result[0]["tags"] == "jazz, pop, rock"


def test_remove_duplicates_keeps_distinct_variant_tags() -> None:
    songs = [
        _song("url1", "Artist", "Title", "variantf"),
        _song("url1", "Artist", "Title", "varianta"),
    ]
    result = remove_duplicates(songs)
    assert len(result) == 1
    assert result[0]["tags"] == "varianta, variantf"


def test_write_duplicates_markdown_structure() -> None:
    dups = {
        "Same Song Title": [
            _song("url1", "Artist A", "Same Song Title", "pop"),
            _song("url2", "Artist B", "Same Song Title", "rock"),
        ]
    }
    with tempfile.NamedTemporaryFile(suffix=".md", mode="r", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    write_duplicates_markdown(dups, tmp_path)
    content = tmp_path.read_text(encoding="utf-8")
    assert "# Possible Duplicate Songs" in content
    assert "1 duplicate groups" in content
    assert "2 songs" in content
    assert "## Same Song Title (2 matches)" in content
    assert "| Artist | Title | Album |" in content
    assert "| Artist A | Same Song Title |" in content
    assert "| Artist B | Same Song Title |" in content
    tmp_path.unlink()


def test_load_songs_from_tag_files_uses_filename_as_tag(tmp_path: Path) -> None:
    rock_file = tmp_path / "rock.txt"
    rock_file.write_text(
        "https://open.spotify.com/track/a\n\n# comment\nhttps://open.spotify.com/track/b\n",
        encoding="utf-8",
    )
    chill_file = tmp_path / "chill.txt"
    chill_file.write_text("https://open.spotify.com/track/c\n", encoding="utf-8")

    songs = load_songs_from_tag_files(tmp_path)

    assert len(songs) == 3
    assert songs[0]["tags"] == "chill"
    assert songs[0]["link"] == "https://open.spotify.com/track/c"
    assert songs[1]["tags"] == "rock"
    assert songs[1]["link"] == "https://open.spotify.com/track/a"
    assert songs[2]["tags"] == "rock"
    assert songs[2]["link"] == "https://open.spotify.com/track/b"


def test_write_songs_csv_outputs_expected_columns(tmp_path: Path) -> None:
    songs = [
        _song("url1", "Artist A", "Title A", "pop"),
        _song("url2", "Artist B", "Title B", "rock"),
    ]
    out = tmp_path / "songs.csv"

    write_songs_csv(songs, out)

    content = out.read_text(encoding="utf-8")
    assert content.splitlines()[0] == "link,artist,title,released,duration,album,track,tags"
    assert "url1,Artist A,Title A,,0,,0,pop" in content
    assert "url2,Artist B,Title B,,0,,0,rock" in content


def test_write_song_links_txt_outputs_one_link_per_line(tmp_path: Path) -> None:
    songs = [
        _song("url1", "Artist A", "Title A", "pop"),
        _song("url2", "Artist B", "Title B", "rock"),
        _song("", "Artist C", "Title C", "jazz"),
    ]
    out = tmp_path / "playlist.txt"

    write_song_links_txt(songs, out)

    assert out.read_text(encoding="utf-8") == "url1\nurl2\n"


def test_group_randomized_songs_keeps_group_members_adjacent() -> None:
    songs = [
        _song("url-x", "Artist", "X", "tag"),
        _song("url-a2", "Artist", "A2", "tag"),
        _song("url-y", "Artist", "Y", "tag"),
        _song("url-a1", "Artist", "A1", "tag"),
        _song("url-z", "Artist", "Z", "tag"),
    ]
    grouped = [["url-a1", "url-a2"]]

    result = group_randomized_songs(songs, grouped)
    links = [song["link"] for song in result]

    assert links == ["url-x", "url-a1", "url-a2", "url-y", "url-z"]


def test_group_randomized_songs_only_emits_present_group_members() -> None:
    songs = [
        _song("url-b2", "Artist", "B2", "tag"),
        _song("url-u", "Artist", "U", "tag"),
    ]
    grouped = [["url-b1", "url-b2"]]

    result = group_randomized_songs(songs, grouped)
    links = [song["link"] for song in result]

    assert links == ["url-b2", "url-u"]


def test_group_randomized_songs_prefers_first_group_for_overlapping_links() -> None:
    songs = [
        _song("url-a", "Artist", "A", "tag"),
        _song("url-b", "Artist", "B", "tag"),
        _song("url-c", "Artist", "C", "tag"),
    ]
    grouped = [
        ["url-a", "url-b"],
        ["url-b", "url-c"],
    ]

    result = group_randomized_songs(songs, grouped)

    # url-b belongs to both groups; algorithm keeps first declared group ownership.
    assert [song["link"] for song in result] == ["url-a", "url-b", "url-c"]


def test_load_grouped_songs_skips_malformed_entries(tmp_path: Path) -> None:
    grouped_path = tmp_path / "grouped.json"
    grouped_path.write_text(
        json.dumps(
            [
                {"songs": ["url1", " ", "url2"]},
                {"songs": "not-a-list"},
                ["not-a-dict"],
                {"no_songs": []},
                {"songs": ["url3"]},
            ]
        ),
        encoding="utf-8",
    )

    # Only dict rows with a list-valued "songs" field should survive normalization.
    assert load_grouped_songs(grouped_path) == [["url1", "url2"], ["url3"]]


def test_load_grouped_songs_returns_empty_for_missing_file(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing_grouped.json"

    assert load_grouped_songs(missing_path) == []


def test_load_grouped_songs_raises_for_invalid_json(tmp_path: Path) -> None:
    grouped_path = tmp_path / "grouped_invalid.json"
    grouped_path.write_text("{not-valid-json}", encoding="utf-8")

    with pytest.raises(json.JSONDecodeError):
        load_grouped_songs(grouped_path)


def test_find_duplicates_handles_non_string_titles() -> None:
    songs = [
        _song("url1", "Artist", 12345, "tag"),
        _song("url2", "Artist", 12345, "tag"),
        _song("url3", "Artist", 67890, "tag"),
    ]

    dups = find_duplicates(songs, 3)

    assert "123" in dups
    assert len(dups["123"]) == 2
    assert "678" not in dups


def test_tag_filter_songs_with_empty_filter_returns_all_songs() -> None:
    songs = [
        _song("url1", "Artist", "One", "a"),
        _song("url2", "Artist", "Two", "b"),
    ]

    result = tag_filter_songs(songs, {})

    assert [song["link"] for song in result] == ["url1", "url2"]


def test_open_json_file_normalizes_tags_on_load(tmp_path: Path) -> None:
    songs_path = tmp_path / "songs.json"
    songs_path.write_text(
        json.dumps(
            [
                {"link": "url1", "tags": "Rock,  rock, POP"},
                {"link": "url2"},
            ]
        ),
        encoding="utf-8",
    )

    songs = open_json_file(songs_path)

    assert songs[0]["tags"] == "pop, rock"
    assert songs[1]["tags"] == ""


def test_validate_song_rows_strict_mode_raises_on_invalid_row() -> None:
    songs = [{"link": "url1", "tags": "a"}]

    with pytest.raises(ValueError, match="missing fields"):
        validate_song_rows(songs, strict_mode=True)


def test_load_settings_bootstraps_from_default_when_missing(tmp_path: Path, monkeypatch) -> None:
    settings_path = tmp_path / "settings.json"
    config_path = tmp_path / "config.json"
    default_settings_path = tmp_path / "default_settings.json"
    default_config_path = tmp_path / "default_config.json"
    default_settings = {
        "settings_version": 1,
        "metadata_enabled": True,
        "strict_mode": False,
        "dry_run": False,
        "log_level": "INFO",
        "max_ctr": 500,
        "http_timeout_seconds": 10,
        "http_max_attempts": 3,
        "http_retry_backoff_seconds": 1,
        "http_retry_jitter_seconds": 0,
    }
    default_config = {
        "song_list_path": "data/song_lists/songs.json",
        "duplicates_path": "data/song_lists/duplicates.json",
        "duplicates_report_path": "data/song_lists/duplicates.md",
        "songs_csv_path": "data/song_lists/songs.csv",
        "run_summary_path": "data/song_lists/run_summary.json",
        "playlist_export_path": "data/playlist_export/songs.txt",
        "grouped_songs_path": "data/song_lists/grouped_songs.json",
        "tags_filter": {"include": [], "exclude": []},
    }
    default_settings_path.write_text(json.dumps(default_settings), encoding="utf-8")
    default_config_path.write_text(json.dumps(default_config), encoding="utf-8")

    monkeypatch.setattr(main_module, "SETTINGS_PATH", settings_path)
    monkeypatch.setattr(main_module, "CONFIG_PATH", config_path)
    monkeypatch.setattr(main_module, "DEFAULT_SETTINGS_PATH", default_settings_path)
    monkeypatch.setattr(main_module, "DEFAULT_CONFIG_PATH", default_config_path)

    loaded = main_module.load_settings()

    assert settings_path.exists()
    assert config_path.exists()
    assert loaded == {**default_config, **default_settings}


def test_load_settings_raises_when_settings_and_default_missing(
    tmp_path: Path, monkeypatch
) -> None:
    settings_path = tmp_path / "settings.json"
    config_path = tmp_path / "config.json"
    default_settings_path = tmp_path / "default_settings.json"
    default_config_path = tmp_path / "default_config.json"

    monkeypatch.setattr(main_module, "SETTINGS_PATH", settings_path)
    monkeypatch.setattr(main_module, "CONFIG_PATH", config_path)
    monkeypatch.setattr(main_module, "DEFAULT_SETTINGS_PATH", default_settings_path)
    monkeypatch.setattr(main_module, "DEFAULT_CONFIG_PATH", default_config_path)

    with pytest.raises(FileNotFoundError):
        main_module.load_settings()


def test_load_settings_raises_for_invalid_json(tmp_path: Path, monkeypatch) -> None:
    settings_path = tmp_path / "settings.json"
    config_path = tmp_path / "config.json"
    default_settings_path = tmp_path / "default_settings.json"
    default_config_path = tmp_path / "default_config.json"
    settings_path.write_text("{not-valid-json}", encoding="utf-8")
    default_config_path.write_text(
        json.dumps(
            {
                "song_list_path": "data/song_lists/songs.json",
                "duplicates_path": "data/song_lists/duplicates.json",
                "duplicates_report_path": "data/song_lists/duplicates.md",
                "songs_csv_path": "data/song_lists/songs.csv",
                "run_summary_path": "data/song_lists/run_summary.json",
                "playlist_export_path": "data/playlist_export/songs.txt",
                "grouped_songs_path": "data/song_lists/grouped_songs.json",
                "tags_filter": {"include": [], "exclude": []},
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(main_module, "SETTINGS_PATH", settings_path)
    monkeypatch.setattr(main_module, "CONFIG_PATH", config_path)
    monkeypatch.setattr(main_module, "DEFAULT_SETTINGS_PATH", default_settings_path)
    monkeypatch.setattr(main_module, "DEFAULT_CONFIG_PATH", default_config_path)

    with pytest.raises(json.JSONDecodeError):
        main_module.load_settings()


def test_load_settings_raises_for_invalid_dry_run_type(tmp_path: Path, monkeypatch) -> None:
    settings_path = tmp_path / "settings.json"
    config_path = tmp_path / "config.json"
    default_config_path = tmp_path / "default_config.json"
    settings_path.write_text(
        json.dumps(
            {
                "settings_version": 1,
                "metadata_enabled": True,
                "strict_mode": False,
                "dry_run": "false",
                "log_level": "INFO",
                "max_ctr": 0,
            }
        ),
        encoding="utf-8",
    )
    default_config_path.write_text(
        json.dumps(
            {
                "song_list_path": "data/song_lists/songs.json",
                "duplicates_path": "data/song_lists/duplicates.json",
                "duplicates_report_path": "data/song_lists/duplicates.md",
                "songs_csv_path": "data/song_lists/songs.csv",
                "run_summary_path": "data/song_lists/run_summary.json",
                "playlist_export_path": "data/playlist_export/songs.txt",
                "grouped_songs_path": "data/song_lists/grouped_songs.json",
                "tags_filter": {"include": [], "exclude": []},
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(main_module, "SETTINGS_PATH", settings_path)
    monkeypatch.setattr(main_module, "CONFIG_PATH", config_path)
    monkeypatch.setattr(main_module, "DEFAULT_SETTINGS_PATH", tmp_path / "default_settings.json")
    monkeypatch.setattr(main_module, "DEFAULT_CONFIG_PATH", default_config_path)

    with pytest.raises(ValueError, match="dry_run"):
        main_module.load_settings()


def test_load_settings_raises_for_unsupported_settings_version(tmp_path: Path, monkeypatch) -> None:
    settings_path = tmp_path / "settings.json"
    config_path = tmp_path / "config.json"
    default_config_path = tmp_path / "default_config.json"
    settings_path.write_text(
        json.dumps(
            {
                "settings_version": 999,
                "metadata_enabled": True,
                "strict_mode": False,
                "dry_run": False,
                "log_level": "INFO",
                "max_ctr": 0,
            }
        ),
        encoding="utf-8",
    )
    default_config_path.write_text(
        json.dumps(
            {
                "song_list_path": "data/song_lists/songs.json",
                "duplicates_path": "data/song_lists/duplicates.json",
                "duplicates_report_path": "data/song_lists/duplicates.md",
                "songs_csv_path": "data/song_lists/songs.csv",
                "run_summary_path": "data/song_lists/run_summary.json",
                "playlist_export_path": "data/playlist_export/songs.txt",
                "grouped_songs_path": "data/song_lists/grouped_songs.json",
                "tags_filter": {"include": [], "exclude": []},
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(main_module, "SETTINGS_PATH", settings_path)
    monkeypatch.setattr(main_module, "CONFIG_PATH", config_path)
    monkeypatch.setattr(main_module, "DEFAULT_SETTINGS_PATH", tmp_path / "default_settings.json")
    monkeypatch.setattr(main_module, "DEFAULT_CONFIG_PATH", default_config_path)

    with pytest.raises(ValueError, match="settings_version"):
        main_module.load_settings()


def test_main_orchestration_uses_filtered_grouped_songs_for_playlist_export(monkeypatch) -> None:
    songs = [
        _song("url-a", "Artist", "A", "featured"),
        _song("url-b", "", "B", "featured"),
        _song("url-c", "Artist", "C", "blocked"),
    ]
    captured: dict[str, Any] = {"csv": None, "playlist": None, "dups": None}

    monkeypatch.setattr(
        main_module,
        "load_settings",
        lambda: {
            "song_list_path": "data/song_lists/songs.json",
            "duplicates_path": "data/song_lists/possible_duplicates.json",
            "duplicates_report_path": "data/song_lists/possible_duplicates.md",
            "songs_csv_path": "data/song_lists/songs.csv",
            "run_summary_path": "data/song_lists/run_summary.json",
            "playlist_export_path": "data/playlist_export/playlist.txt",
            "grouped_songs_path": "data/song_lists/grouped_songs.json",
            "metadata_enabled": True,
            "strict_mode": False,
            "dry_run": False,
            "log_level": "INFO",
            "tags_filter": {"include": ["featured"], "exclude": ["blocked"]},
            "max_ctr": 0,
        },
    )
    # Use copy-per-song so main() mutations do not leak back into test fixtures.
    monkeypatch.setattr(main_module, "open_json_file", lambda _path: [dict(song) for song in songs])
    monkeypatch.setattr(main_module, "load_songs_from_tag_files", lambda _path: [])
    monkeypatch.setattr(main_module, "process_songs", lambda in_songs, _max: in_songs)
    monkeypatch.setattr(main_module, "load_grouped_songs", lambda _path: [["url-b", "url-a"]])
    monkeypatch.setattr(
        main_module,
        "write_json_file",
        lambda data, path: captured.__setitem__("dups", data)
        if "possible_duplicates" in str(path)
        else None,
    )
    monkeypatch.setattr(main_module, "write_duplicates_markdown", lambda _dups, _path: None)
    # Freeze shuffle for deterministic assertions.
    monkeypatch.setattr(main_module.random, "shuffle", lambda _songs: None)

    def _capture_csv(data, _path):
        captured["csv"] = [song["link"] for song in data]

    def _capture_playlist(data, _path):
        captured["playlist"] = [song["link"] for song in data]

    monkeypatch.setattr(main_module, "write_songs_csv", _capture_csv)
    monkeypatch.setattr(main_module, "write_song_links_txt", _capture_playlist)

    main_module.main()

    # CSV export remains the full catalog; playlist export uses filtered + grouped order.
    assert captured["csv"] == ["url-a", "url-b", "url-c"]
    assert captured["playlist"] == ["url-b", "url-a"]
    assert isinstance(captured["dups"], dict)


def test_get_url_meta_passes_timeout_to_requests(monkeypatch) -> None:
    captured = {"url": None, "timeout": None}

    class _Response:
        text = "<html></html>"

        def raise_for_status(self):
            return None

    class _Soup:
        def __init__(self, _text, _parser):
            pass

        def find_all(self, _tag):
            return []

    def _fake_get(url, timeout=None):
        captured["url"] = url
        captured["timeout"] = timeout
        return _Response()

    monkeypatch.setattr(main_module._HTTP_SESSION, "get", _fake_get)
    monkeypatch.setattr(main_module, "BeautifulSoup", _Soup)

    retry_url = "https://example-retry.com"
    main_module._META_CACHE.pop(retry_url, None)
    result = get_url_meta(retry_url)

    assert result == []
    assert captured["url"] == retry_url
    assert captured["timeout"] == main_module.REQUEST_TIMEOUT_SECONDS


def test_get_url_meta_retries_then_succeeds(monkeypatch) -> None:
    attempts = {"count": 0}
    waits = []

    class _Response:
        text = "<html></html>"

        def raise_for_status(self):
            return None

    class _Soup:
        def __init__(self, _text, _parser):
            pass

        def find_all(self, _tag):
            return ["meta"]

    def _fake_get(_url, timeout=None):
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise main_module.requests.RequestException("temporary")
        return _Response()

    monkeypatch.setattr(main_module._HTTP_SESSION, "get", _fake_get)
    monkeypatch.setattr(main_module, "BeautifulSoup", _Soup)
    monkeypatch.setattr(main_module.random, "uniform", lambda _a, _b: 0.25)
    monkeypatch.setattr(main_module.time, "sleep", lambda s: waits.append(s))

    result = get_url_meta("https://example.com")

    assert result == ["meta"]
    assert attempts["count"] == 3
    assert waits == [1.25, 2.25]


def test_main_integration_writes_outputs_with_fixture(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    settings_dir = data_dir / "settings"
    song_lists_dir = data_dir / "song_lists"
    songs_import_dir = data_dir / "songs_import"
    playlist_export_dir = data_dir / "playlist_export"

    settings_dir.mkdir(parents=True)
    song_lists_dir.mkdir(parents=True)
    songs_import_dir.mkdir(parents=True)
    playlist_export_dir.mkdir(parents=True)

    (song_lists_dir / "songs.json").write_text(
        json.dumps(
            [
                {
                    "link": "url-a",
                    "artist": "Artist A",
                    "title": "Song A",
                    "released": "",
                    "duration": 100,
                    "album": "Album A",
                    "track": 1,
                    "tags": "Featured",
                }
            ]
        ),
        encoding="utf-8",
    )
    (songs_import_dir / "featured.txt").write_text("url-b\n", encoding="utf-8")
    (song_lists_dir / "grouped_songs.json").write_text(
        json.dumps([{"songs": ["url-b", "url-a"]}]),
        encoding="utf-8",
    )
    (settings_dir / "settings.json").write_text(
        json.dumps(
            {
                "settings_version": 1,
                "metadata_enabled": True,
                "strict_mode": False,
                "dry_run": False,
                "log_level": "INFO",
                "max_ctr": 0,
            }
        ),
        encoding="utf-8",
    )
    (settings_dir / "config.json").write_text(
        json.dumps(
            {
                "song_list_path": "data/song_lists/songs.json",
                "duplicates_path": "data/song_lists/possible_duplicates.json",
                "duplicates_report_path": "data/song_lists/possible_duplicates.md",
                "songs_csv_path": "data/song_lists/songs.csv",
                "run_summary_path": "data/song_lists/run_summary.json",
                "playlist_export_path": "data/playlist_export/playlist.txt",
                "grouped_songs_path": "data/song_lists/grouped_songs.json",
                "tags_filter": {"include": [], "exclude": []},
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(main_module, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(main_module, "SETTINGS_PATH", settings_dir / "settings.json")
    monkeypatch.setattr(main_module, "CONFIG_PATH", settings_dir / "config.json")
    monkeypatch.setattr(
        main_module,
        "DEFAULT_SETTINGS_PATH",
        settings_dir / "default_settings.json",
    )
    monkeypatch.setattr(main_module, "DEFAULT_CONFIG_PATH", settings_dir / "default_config.json")
    monkeypatch.setattr(main_module, "SONGS_IMPORT_DIR", songs_import_dir)
    monkeypatch.setattr(main_module.random, "shuffle", lambda _songs: None)

    main_module.main()

    songs_csv = (song_lists_dir / "songs.csv").read_text(encoding="utf-8")
    playlist_txt = (playlist_export_dir / "playlist.txt").read_text(encoding="utf-8")
    duplicates_json = json.loads(
        (song_lists_dir / "possible_duplicates.json").read_text(encoding="utf-8")
    )
    duplicates_md = (song_lists_dir / "possible_duplicates.md").read_text(encoding="utf-8")

    assert "link,artist,title,released,duration,album,track,tags" in songs_csv
    assert "url-a" in songs_csv
    assert "url-b" in songs_csv
    assert playlist_txt == "url-b\nurl-a\n"
    assert isinstance(duplicates_json, dict)
    assert "# Possible Duplicate Songs" in duplicates_md


def test_main_creates_missing_song_and_grouped_list_files(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    settings_dir = data_dir / "settings"
    song_lists_dir = data_dir / "song_lists"
    playlist_export_dir = data_dir / "playlist_export"

    settings_dir.mkdir(parents=True)
    song_lists_dir.mkdir(parents=True)
    playlist_export_dir.mkdir(parents=True)

    (settings_dir / "settings.json").write_text(
        json.dumps(
            {
                "settings_version": 1,
                "metadata_enabled": False,
                "strict_mode": False,
                "dry_run": True,
                "log_level": "INFO",
                "max_ctr": 0,
                "http_timeout_seconds": 10,
                "http_max_attempts": 3,
                "http_retry_backoff_seconds": 1,
                "http_retry_jitter_seconds": 0,
            }
        ),
        encoding="utf-8",
    )
    (settings_dir / "config.json").write_text(
        json.dumps(
            {
                "song_list_path": "data/song_lists/songs.json",
                "duplicates_path": "data/song_lists/possible_duplicates.json",
                "duplicates_report_path": "data/song_lists/possible_duplicates.md",
                "songs_csv_path": "data/song_lists/songs.csv",
                "run_summary_path": "data/song_lists/run_summary.json",
                "playlist_export_path": "data/playlist_export/playlist.txt",
                "grouped_songs_path": "data/song_lists/grouped_songs.json",
                "tags_filter": {"include": [], "exclude": []},
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(main_module, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(main_module, "SETTINGS_PATH", settings_dir / "settings.json")
    monkeypatch.setattr(main_module, "CONFIG_PATH", settings_dir / "config.json")
    monkeypatch.setattr(
        main_module, "DEFAULT_SETTINGS_PATH", settings_dir / "default_settings.json"
    )
    monkeypatch.setattr(main_module, "DEFAULT_CONFIG_PATH", settings_dir / "default_config.json")
    monkeypatch.setattr(main_module, "SONGS_IMPORT_DIR", data_dir / "songs_import")
    monkeypatch.setattr(main_module.random, "shuffle", lambda _songs: None)

    main_module.main()

    assert (song_lists_dir / "songs.json").read_text(encoding="utf-8") == "[]\n"
    assert (song_lists_dir / "grouped_songs.json").read_text(encoding="utf-8") == "[]\n"


def test_main_golden_snapshot_tiny_fixture_outputs_exact_artifacts(
    tmp_path: Path, monkeypatch
) -> None:
    from datetime import date as _date

    data_dir = tmp_path / "data"
    settings_dir = data_dir / "settings"
    song_lists_dir = data_dir / "song_lists"
    songs_import_dir = data_dir / "songs_import"
    playlist_export_dir = data_dir / "playlist_export"

    settings_dir.mkdir(parents=True)
    song_lists_dir.mkdir(parents=True)
    songs_import_dir.mkdir(parents=True)
    playlist_export_dir.mkdir(parents=True)

    (song_lists_dir / "songs.json").write_text(
        json.dumps(
            [
                {
                    "link": "url-a",
                    "artist": "Artist A",
                    "title": "Same Song",
                    "released": "",
                    "duration": 100,
                    "album": "Album A",
                    "track": 1,
                    "tags": "featured",
                },
                {
                    "link": "url-b",
                    "artist": "Artist B",
                    "title": "Same Song",
                    "released": "",
                    "duration": 110,
                    "album": "Album B",
                    "track": 2,
                    "tags": "featured",
                },
            ]
        ),
        encoding="utf-8",
    )
    (song_lists_dir / "grouped_songs.json").write_text(
        json.dumps([{"songs": ["url-b", "url-a"]}]),
        encoding="utf-8",
    )

    (settings_dir / "settings.json").write_text(
        json.dumps(
            {
                "settings_version": 1,
                "metadata_enabled": False,
                "strict_mode": False,
                "dry_run": False,
                "log_level": "INFO",
                "max_ctr": 0,
                "http_timeout_seconds": 10,
                "http_max_attempts": 3,
                "http_retry_backoff_seconds": 1,
                "http_retry_jitter_seconds": 0,
            }
        ),
        encoding="utf-8",
    )
    (settings_dir / "config.json").write_text(
        json.dumps(
            {
                "song_list_path": "data/song_lists/songs.json",
                "duplicates_path": "data/song_lists/possible_duplicates.json",
                "duplicates_report_path": "data/song_lists/possible_duplicates.md",
                "songs_csv_path": "data/song_lists/songs.csv",
                "run_summary_path": "data/song_lists/run_summary.json",
                "playlist_export_path": "data/playlist_export/playlist.txt",
                "grouped_songs_path": "data/song_lists/grouped_songs.json",
                "tags_filter": {"include": ["featured"], "exclude": []},
            }
        ),
        encoding="utf-8",
    )

    class _FixedDate:
        @classmethod
        def today(cls):
            return _date(2099, 12, 31)

    monkeypatch.setattr(main_module, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(main_module, "SETTINGS_PATH", settings_dir / "settings.json")
    monkeypatch.setattr(main_module, "CONFIG_PATH", settings_dir / "config.json")
    monkeypatch.setattr(
        main_module, "DEFAULT_SETTINGS_PATH", settings_dir / "default_settings.json"
    )
    monkeypatch.setattr(main_module, "DEFAULT_CONFIG_PATH", settings_dir / "default_config.json")
    monkeypatch.setattr(main_module, "SONGS_IMPORT_DIR", songs_import_dir)
    monkeypatch.setattr(main_module.random, "shuffle", lambda _songs: None)
    monkeypatch.setattr(exporters_module, "date", _FixedDate)

    main_module.main()

    songs_csv = (song_lists_dir / "songs.csv").read_text(encoding="utf-8")
    playlist_txt = (playlist_export_dir / "playlist.txt").read_text(encoding="utf-8")
    duplicates_md = (song_lists_dir / "possible_duplicates.md").read_text(encoding="utf-8")

    assert songs_csv == (
        "link,artist,title,released,duration,album,track,tags\n"
        "url-a,Artist A,Same Song,,100,Album A,1,featured\n"
        "url-b,Artist B,Same Song,,110,Album B,2,featured\n"
    )
    assert playlist_txt == "url-b\nurl-a\n"
    assert duplicates_md == "\n".join(
        [
            "# Possible Duplicate Songs",
            "",
            "Generated: 2099-12-31  ",
            "**1 duplicate groups** across **2 songs**",
            "",
            "## Same Song (2 matches)",
            "",
            "| Artist | Title | Album |",
            "|--------|-------|-------|",
            "| Artist A | Same Song | Album A |",
            "| Artist B | Same Song | Album B |",
            "",
        ]
    )


def test_main_dry_run_skips_all_writes(monkeypatch, caplog) -> None:
    songs = [
        _song("url-a", "Artist", "A", "featured"),
        _song("url-b", "Artist", "B", "featured"),
    ]
    calls = {"json": 0, "csv": 0, "md": 0, "txt": 0, "process": 0}
    caplog.set_level("INFO")

    monkeypatch.setattr(
        main_module,
        "load_settings",
        lambda: {
            "song_list_path": "data/song_lists/songs.json",
            "duplicates_path": "data/song_lists/possible_duplicates.json",
            "duplicates_report_path": "data/song_lists/possible_duplicates.md",
            "songs_csv_path": "data/song_lists/songs.csv",
            "run_summary_path": "data/song_lists/run_summary.json",
            "playlist_export_path": "data/playlist_export/playlist.txt",
            "grouped_songs_path": "data/song_lists/grouped_songs.json",
            "metadata_enabled": False,
            "strict_mode": False,
            "dry_run": True,
            "log_level": "INFO",
            "tags_filter": {"include": [], "exclude": []},
            "max_ctr": 0,
        },
    )
    monkeypatch.setattr(main_module, "open_json_file", lambda _path: [dict(song) for song in songs])
    monkeypatch.setattr(main_module, "load_songs_from_tag_files", lambda _path: [])
    monkeypatch.setattr(
        main_module,
        "process_songs",
        lambda in_songs, _max: calls.__setitem__("process", calls["process"] + 1) or in_songs,
    )
    monkeypatch.setattr(main_module, "load_grouped_songs", lambda _path: [["url-a", "url-b"]])
    monkeypatch.setattr(main_module.random, "shuffle", lambda _songs: None)

    monkeypatch.setattr(
        main_module,
        "write_json_file",
        lambda *_args, **_kwargs: calls.__setitem__("json", calls["json"] + 1),
    )
    monkeypatch.setattr(
        main_module,
        "write_songs_csv",
        lambda *_args, **_kwargs: calls.__setitem__("csv", calls["csv"] + 1),
    )
    monkeypatch.setattr(
        main_module,
        "write_duplicates_markdown",
        lambda *_args, **_kwargs: calls.__setitem__("md", calls["md"] + 1),
    )
    monkeypatch.setattr(
        main_module,
        "write_song_links_txt",
        lambda *_args, **_kwargs: calls.__setitem__("txt", calls["txt"] + 1),
    )

    main_module.main()

    assert calls == {"json": 0, "csv": 0, "md": 0, "txt": 0, "process": 0}
    assert "Dry-run enabled; skipping file writes." in caplog.text
    assert "Would write" in caplog.text
    assert "Run summary:" in caplog.text


def test_load_settings_migrates_legacy_missing_version(tmp_path: Path, monkeypatch) -> None:
    settings_path = tmp_path / "settings.json"
    config_path = tmp_path / "config.json"
    default_settings_path = tmp_path / "default_settings.json"
    default_config_path = tmp_path / "default_config.json"
    legacy_settings = {
        "max_ctr": 100,
    }
    default_settings = {
        "settings_version": 1,
        "metadata_enabled": True,
        "strict_mode": False,
        "dry_run": False,
        "log_level": "INFO",
        "max_ctr": 500,
    }
    default_config = {
        "song_list_path": "data/song_lists/songs.json",
        "duplicates_path": "data/song_lists/duplicates.json",
        "duplicates_report_path": "data/song_lists/duplicates.md",
        "songs_csv_path": "data/song_lists/songs.csv",
        "run_summary_path": "data/song_lists/run_summary.json",
        "playlist_export_path": "data/playlist_export/songs.txt",
        "grouped_songs_path": "data/song_lists/grouped_songs.json",
        "tags_filter": {"include": [], "exclude": []},
    }
    settings_path.write_text(json.dumps(legacy_settings), encoding="utf-8")
    default_settings_path.write_text(json.dumps(default_settings), encoding="utf-8")
    default_config_path.write_text(json.dumps(default_config), encoding="utf-8")

    monkeypatch.setattr(main_module, "SETTINGS_PATH", settings_path)
    monkeypatch.setattr(main_module, "CONFIG_PATH", config_path)
    monkeypatch.setattr(main_module, "DEFAULT_SETTINGS_PATH", default_settings_path)
    monkeypatch.setattr(main_module, "DEFAULT_CONFIG_PATH", default_config_path)

    loaded = main_module.load_settings()

    assert loaded["settings_version"] == 1
    assert loaded["run_summary_path"] == "data/song_lists/run_summary.json"
    assert loaded["metadata_enabled"] is True
    persisted = json.loads(settings_path.read_text(encoding="utf-8"))
    assert persisted["settings_version"] == 1


def test_main_resets_runtime_state_between_runs(monkeypatch) -> None:
    songs = [_song("url-a", "Artist", "A", "featured")]

    monkeypatch.setattr(
        main_module,
        "load_settings",
        lambda: {
            "song_list_path": "data/song_lists/songs.json",
            "duplicates_path": "data/song_lists/possible_duplicates.json",
            "duplicates_report_path": "data/song_lists/possible_duplicates.md",
            "songs_csv_path": "data/song_lists/songs.csv",
            "run_summary_path": "data/song_lists/run_summary.json",
            "playlist_export_path": "data/playlist_export/playlist.txt",
            "grouped_songs_path": "data/song_lists/grouped_songs.json",
            "metadata_enabled": False,
            "strict_mode": False,
            "dry_run": True,
            "log_level": "INFO",
            "tags_filter": {"include": [], "exclude": []},
            "max_ctr": 0,
        },
    )
    monkeypatch.setattr(main_module, "open_json_file", lambda _path: [dict(song) for song in songs])
    monkeypatch.setattr(main_module, "load_songs_from_tag_files", lambda _path: [])
    monkeypatch.setattr(main_module, "load_grouped_songs", lambda _path: [])
    monkeypatch.setattr(main_module.random, "shuffle", lambda _songs: None)

    main_module._META_CACHE["https://example.com/stale"] = ["meta"]
    main_module._RETRY_METRICS["retries"] = 7
    main_module._RETRY_METRICS["failed_urls"] = 3
    main_module._RETRY_METRICS["http_errors"] = 2

    main_module.main()

    assert main_module._META_CACHE == {}
    assert main_module._RETRY_METRICS == {"retries": 0, "failed_urls": 0, "http_errors": 0}


def test_main_writes_run_summary_with_stable_schema(monkeypatch) -> None:
    songs = [
        _song("url-a", "Artist", "A", "featured"),
        _song("url-b", "Artist", "B", "featured"),
    ]
    captured: dict[str, Any] = {"run_summary": None}

    monkeypatch.setattr(
        main_module,
        "load_settings",
        lambda: {
            "song_list_path": "data/song_lists/songs.json",
            "duplicates_path": "data/song_lists/possible_duplicates.json",
            "duplicates_report_path": "data/song_lists/possible_duplicates.md",
            "songs_csv_path": "data/song_lists/songs.csv",
            "run_summary_path": "data/song_lists/run_summary.json",
            "playlist_export_path": "data/playlist_export/playlist.txt",
            "grouped_songs_path": "data/song_lists/grouped_songs.json",
            "metadata_enabled": False,
            "strict_mode": False,
            "dry_run": False,
            "log_level": "INFO",
            "tags_filter": {"include": [], "exclude": []},
            "max_ctr": 0,
            "http_timeout_seconds": 17,
            "http_max_attempts": 4,
            "http_retry_backoff_seconds": 2,
            "http_retry_jitter_seconds": 0,
        },
    )
    monkeypatch.setattr(main_module, "open_json_file", lambda _path: [dict(song) for song in songs])
    monkeypatch.setattr(main_module, "load_songs_from_tag_files", lambda _path: [])
    monkeypatch.setattr(main_module, "load_grouped_songs", lambda _path: [])
    monkeypatch.setattr(main_module.random, "shuffle", lambda _songs: None)
    monkeypatch.setattr(main_module, "write_songs_csv", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(main_module, "write_duplicates_markdown", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(main_module, "write_song_links_txt", lambda *_args, **_kwargs: None)

    def _capture_json(data, path):
        if "run_summary" in str(path):
            captured["run_summary"] = data

    monkeypatch.setattr(main_module, "write_json_file", _capture_json)

    main_module.main()

    summary = captured["run_summary"]
    assert summary is not None
    summary = cast(dict[str, Any], summary)
    assert set(summary.keys()) == {
        "loaded",
        "imported",
        "deduped",
        "filtered",
        "grouped",
        "duplicate_groups",
        "invalid",
        "retries",
        "failed_urls",
        "http_errors",
        "http_timeout_seconds",
        "http_max_attempts",
        "http_retry_backoff_seconds",
        "http_retry_jitter_seconds",
        "metadata_enabled",
        "dry_run",
    }
    for key in (
        "loaded",
        "imported",
        "deduped",
        "filtered",
        "grouped",
        "duplicate_groups",
        "invalid",
        "retries",
        "failed_urls",
        "http_errors",
        "http_timeout_seconds",
        "http_max_attempts",
        "http_retry_backoff_seconds",
        "http_retry_jitter_seconds",
    ):
        assert isinstance(summary[key], int)
    assert summary["http_timeout_seconds"] == 17
    assert summary["http_max_attempts"] == 4
    assert summary["http_retry_backoff_seconds"] == 2
    assert summary["http_retry_jitter_seconds"] == 0
    assert isinstance(summary["metadata_enabled"], bool)
    assert isinstance(summary["dry_run"], bool)


def test_load_settings_backfills_http_settings_from_defaults(tmp_path: Path, monkeypatch) -> None:
    settings_path = tmp_path / "settings.json"
    config_path = tmp_path / "config.json"
    default_settings_path = tmp_path / "default_settings.json"
    default_config_path = tmp_path / "default_config.json"

    settings_path.write_text(
        json.dumps(
            {
                "settings_version": 1,
                "metadata_enabled": True,
                "strict_mode": False,
                "dry_run": False,
                "log_level": "INFO",
                "max_ctr": 500,
            }
        ),
        encoding="utf-8",
    )
    default_settings_path.write_text(
        json.dumps(
            {
                "settings_version": 1,
                "metadata_enabled": True,
                "strict_mode": False,
                "dry_run": False,
                "log_level": "INFO",
                "max_ctr": 500,
                "http_timeout_seconds": 11,
                "http_max_attempts": 4,
                "http_retry_backoff_seconds": 2,
                "http_retry_jitter_seconds": 0,
            }
        ),
        encoding="utf-8",
    )
    default_config_path.write_text(
        json.dumps(
            {
                "song_list_path": "data/song_lists/songs.json",
                "duplicates_path": "data/song_lists/duplicates.json",
                "duplicates_report_path": "data/song_lists/duplicates.md",
                "songs_csv_path": "data/song_lists/songs.csv",
                "run_summary_path": "data/song_lists/run_summary.json",
                "playlist_export_path": "data/playlist_export/songs.txt",
                "grouped_songs_path": "data/song_lists/grouped_songs.json",
                "tags_filter": {"include": [], "exclude": []},
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(main_module, "SETTINGS_PATH", settings_path)
    monkeypatch.setattr(main_module, "CONFIG_PATH", config_path)
    monkeypatch.setattr(main_module, "DEFAULT_SETTINGS_PATH", default_settings_path)
    monkeypatch.setattr(main_module, "DEFAULT_CONFIG_PATH", default_config_path)

    loaded = main_module.load_settings()

    assert loaded["http_timeout_seconds"] == 11
    assert loaded["http_max_attempts"] == 4
    assert loaded["http_retry_backoff_seconds"] == 2
    assert loaded["http_retry_jitter_seconds"] == 0


def test_load_settings_raises_for_invalid_http_max_attempts_value(
    tmp_path: Path, monkeypatch
) -> None:
    settings_path = tmp_path / "settings.json"
    config_path = tmp_path / "config.json"
    default_config_path = tmp_path / "default_config.json"
    settings_path.write_text(
        json.dumps(
            {
                "settings_version": 1,
                "metadata_enabled": True,
                "strict_mode": False,
                "dry_run": False,
                "log_level": "INFO",
                "max_ctr": 500,
                "http_max_attempts": 0,
            }
        ),
        encoding="utf-8",
    )
    default_config_path.write_text(
        json.dumps(
            {
                "song_list_path": "data/song_lists/songs.json",
                "duplicates_path": "data/song_lists/duplicates.json",
                "duplicates_report_path": "data/song_lists/duplicates.md",
                "songs_csv_path": "data/song_lists/songs.csv",
                "run_summary_path": "data/song_lists/run_summary.json",
                "playlist_export_path": "data/playlist_export/songs.txt",
                "grouped_songs_path": "data/song_lists/grouped_songs.json",
                "tags_filter": {"include": [], "exclude": []},
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(main_module, "SETTINGS_PATH", settings_path)
    monkeypatch.setattr(main_module, "CONFIG_PATH", config_path)
    monkeypatch.setattr(main_module, "DEFAULT_SETTINGS_PATH", tmp_path / "default_settings.json")
    monkeypatch.setattr(main_module, "DEFAULT_CONFIG_PATH", default_config_path)

    with pytest.raises(ValueError, match="http_max_attempts"):
        main_module.load_settings()


def test_get_url_meta_uses_configured_timeout(monkeypatch) -> None:
    captured = {"timeout": None}

    class _Response:
        text = "<html></html>"

        def raise_for_status(self):
            return None

    class _Soup:
        def __init__(self, _text, _parser):
            pass

        def find_all(self, _tag):
            return []

    def _fake_get(_url, timeout=None):
        captured["timeout"] = timeout
        return _Response()

    monkeypatch.setattr(main_module._HTTP_SESSION, "get", _fake_get)
    monkeypatch.setattr(main_module, "BeautifulSoup", _Soup)

    prev_timeout = main_module._HTTP_CONFIG["timeout_seconds"]
    test_url = "https://example-timeout.com"
    main_module._META_CACHE.pop(test_url, None)
    main_module._HTTP_CONFIG["timeout_seconds"] = 17
    try:
        get_url_meta(test_url)
    finally:
        main_module._HTTP_CONFIG["timeout_seconds"] = prev_timeout

    assert captured["timeout"] == 17


def test_cli_validate_config_mode_loads_config_and_skips_pipeline(monkeypatch, capsys) -> None:
    calls = {"load": 0, "run": 0}

    monkeypatch.setattr(
        cli_module,
        "load_settings",
        lambda: calls.__setitem__("load", calls["load"] + 1) or {},
    )
    monkeypatch.setattr(
        cli_module,
        "run_pipeline",
        lambda: calls.__setitem__("run", calls["run"] + 1),
    )

    assert cli_module.cli(["--validate-config"]) == 0
    assert calls == {"load": 1, "run": 0}
    assert "Configuration is valid." in capsys.readouterr().out


def test_cli_default_mode_runs_pipeline(monkeypatch) -> None:
    calls = {"load": 0, "run": 0}

    monkeypatch.setattr(
        cli_module,
        "load_settings",
        lambda: calls.__setitem__("load", calls["load"] + 1) or {},
    )
    monkeypatch.setattr(
        cli_module,
        "run_pipeline",
        lambda: calls.__setitem__("run", calls["run"] + 1),
    )

    assert cli_module.cli([]) == 0
    assert calls == {"load": 0, "run": 1}


def test_cli_validate_config_mode_propagates_load_errors(monkeypatch) -> None:
    calls = {"run": 0}

    monkeypatch.setattr(
        cli_module,
        "load_settings",
        lambda: (_ for _ in ()).throw(ValueError("bad config")),
    )
    monkeypatch.setattr(
        cli_module,
        "run_pipeline",
        lambda: calls.__setitem__("run", calls["run"] + 1),
    )

    with pytest.raises(ValueError, match="bad config"):
        cli_module.cli(["--validate-config"])

    assert calls == {"run": 0}


def test_cli_validate_config_subprocess_smoke() -> None:
    project_root = Path(__file__).resolve().parents[1]
    env = dict(os.environ)
    existing_pythonpath = env.get("PYTHONPATH", "")
    src_path = str(project_root / "src")
    env["PYTHONPATH"] = src_path if not existing_pythonpath else f"{src_path}:{existing_pythonpath}"

    result = subprocess.run(
        [sys.executable, "-m", "playlists_sptfy", "--validate-config"],
        cwd=project_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Configuration is valid." in result.stdout
