import importlib
import json
import sys
from pathlib import Path

import pytest

WEB_DIR = Path(__file__).resolve().parents[1] / "web"


def _reset_web_modules():
    """Drop cached web-app modules so a fresh DATA_ROOT env var takes effect
    on the next import (file_utils.DATA_ROOT is resolved once at import
    time, and route modules bind file_utils.read_json/write_json by
    reference at their own import time)."""
    for name in list(sys.modules):
        if name == "file_utils" or name == "app" or name.startswith("routes."):
            del sys.modules[name]


def _write(data_root: Path, rel_path: str, data) -> None:
    path = data_root / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _read(data_root: Path, rel_path: str):
    return json.loads((data_root / rel_path).read_text(encoding="utf-8"))


@pytest.fixture
def data_root(tmp_path, monkeypatch):
    (tmp_path / "song_lists").mkdir()
    monkeypatch.setenv("DATA_ROOT", str(tmp_path))
    return tmp_path


@pytest.fixture
def client(data_root):
    if str(WEB_DIR) not in sys.path:
        sys.path.insert(0, str(WEB_DIR))
    _reset_web_modules()
    app_module = importlib.import_module("app")
    app_module.app.testing = True
    with app_module.app.test_client() as c:
        yield c
    _reset_web_modules()


def _song(link, artist="Artist", title="Title", tags="", **overrides):
    song = {
        "link": link,
        "artist": artist,
        "title": title,
        "album": "Album",
        "track": 1,
        "duration": 200,
        "released": "2000-01-01",
        "tags": tags,
    }
    song.update(overrides)
    return song


def test_songs_route_smoke(client, data_root):
    _write(data_root, "song_lists/songs.json", [_song("l1", title="One")])
    resp = client.get("/api/songs/")
    assert resp.status_code == 200
    assert resp.get_json()[0]["title"] == "One"


def test_songs_route_update_roundtrips_ranking(client, data_root):
    _write(data_root, "song_lists/songs.json", [_song("l1", title="One")])
    resp = client.get("/api/songs/")
    song = resp.get_json()[0]
    song["ranking"] = "4"

    resp = client.put("/api/songs/0", json=song)
    assert resp.status_code == 200

    stored = _read(data_root, "song_lists/songs.json")
    assert stored[0]["ranking"] == "4"


def test_albums_route_returns_avg_ranking(client, data_root):
    _write(
        data_root,
        "song_lists/songs.json",
        [
            _song("l1", title="One", track=1, ranking="3"),
            _song("l2", title="Two", track=2, ranking="4"),
            _song("l3", title="Three", track=3, ranking=""),
        ],
    )
    resp = client.get("/api/albums/")
    assert resp.status_code == 200
    row = resp.get_json()[0]
    assert row["avg_ranking"] == 3.5


def test_albums_route_tracks_include_per_song_ranking(client, data_root):
    _write(
        data_root,
        "song_lists/songs.json",
        [
            _song("l1", title="One", track=1, ranking="3"),
            _song("l2", title="Two", track=2, ranking=""),
        ],
    )
    resp = client.get("/api/albums/")
    assert resp.status_code == 200
    tracks = {t["title"]: t["ranking"] for t in resp.get_json()[0]["tracks"]}
    assert tracks == {"One": "3", "Two": ""}


def test_albums_route_avg_ranking_is_null_when_all_tracks_unrated(client, data_root):
    _write(
        data_root,
        "song_lists/songs.json",
        [_song("l1", title="One", ranking="")],
    )
    resp = client.get("/api/albums/")
    assert resp.status_code == 200
    assert resp.get_json()[0]["avg_ranking"] is None


def test_tag_groups_returns_genre_and_era_lists(client, data_root):
    _write(data_root, "song_lists/songs.json", [])
    resp = client.get("/api/tag-groups/")
    assert resp.status_code == 200
    body = resp.get_json()
    assert "rock" in body["genre_tags"]
    assert "80s" in body["era_tags"]


# --- Possible Duplicates: merge-tags (US-3) --------------------------------


def test_merge_tags_unions_and_writes_songs_json(client, data_root):
    _write(
        data_root,
        "song_lists/songs.json",
        [
            _song("l1", tags="rock, 70s"),
            _song("l2", tags="rock, singles"),
            _song("l3", tags="unrelated"),
        ],
    )
    _write(
        data_root,
        "song_lists/possible_duplicates.json",
        {"Some Song": [_song("l1", tags="rock, 70s"), _song("l2", tags="rock, singles")]},
    )

    resp = client.post("/api/possible-duplicates/Some Song/merge-tags")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    assert body["changed"] == 2

    songs = _read(data_root, "song_lists/songs.json")
    by_link = {s["link"]: s for s in songs}
    assert by_link["l1"]["tags"] == "70s, rock, singles"
    assert by_link["l2"]["tags"] == "70s, rock, singles"
    assert by_link["l3"]["tags"] == "unrelated"  # untouched — not in the group


def test_merge_tags_updates_possible_duplicates_cache(client, data_root):
    _write(
        data_root,
        "song_lists/songs.json",
        [_song("l1", tags="rock"), _song("l2", tags="70s")],
    )
    _write(
        data_root,
        "song_lists/possible_duplicates.json",
        {"Some Song": [_song("l1", tags="rock"), _song("l2", tags="70s")]},
    )

    client.post("/api/possible-duplicates/Some Song/merge-tags")

    dup_data = _read(data_root, "song_lists/possible_duplicates.json")
    assert all(s["tags"] == "70s, rock" for s in dup_data["Some Song"])


def test_merge_tags_404_on_unknown_key(client, data_root):
    _write(data_root, "song_lists/songs.json", [])
    _write(data_root, "song_lists/possible_duplicates.json", {})
    resp = client.post("/api/possible-duplicates/Nope/merge-tags")
    assert resp.status_code == 404


# --- Ignored Duplicates: delete-song fix + group-delete guard (US-4) -------


def test_ignore_duplicates_delete_song_also_deletes_from_songs_json(client, data_root):
    _write(
        data_root,
        "song_lists/songs.json",
        [_song("l1"), _song("l2"), _song("l3")],
    )
    _write(
        data_root,
        "song_lists/ignore_duplicates.json",
        {"Some Song": [_song("l1"), _song("l2"), _song("l3")]},
    )

    resp = client.delete("/api/ignore-duplicates/Some Song/songs/0")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body == {"ok": True, "entry_deleted": False}

    songs = _read(data_root, "song_lists/songs.json")
    assert {s["link"] for s in songs} == {"l2", "l3"}

    entry = _read(data_root, "song_lists/ignore_duplicates.json")["Some Song"]
    assert {s["link"] for s in entry} == {"l2", "l3"}


def test_ignore_duplicates_delete_song_removes_group_when_one_left(client, data_root):
    _write(data_root, "song_lists/songs.json", [_song("l1"), _song("l2")])
    _write(
        data_root,
        "song_lists/ignore_duplicates.json",
        {"Some Song": [_song("l1"), _song("l2")]},
    )

    resp = client.delete("/api/ignore-duplicates/Some Song/songs/0")
    assert resp.get_json() == {"ok": True, "entry_deleted": True}

    entries = _read(data_root, "song_lists/ignore_duplicates.json")
    assert "Some Song" not in entries

    songs = _read(data_root, "song_lists/songs.json")
    assert {s["link"] for s in songs} == {"l2"}


def test_ignore_duplicates_group_delete_does_not_touch_songs_json(client, data_root):
    _write(data_root, "song_lists/songs.json", [_song("l1"), _song("l2")])
    _write(
        data_root,
        "song_lists/ignore_duplicates.json",
        {"Some Song": [_song("l1"), _song("l2")]},
    )

    resp = client.delete("/api/ignore-duplicates/Some Song")
    assert resp.status_code == 200

    entries = _read(data_root, "song_lists/ignore_duplicates.json")
    assert "Some Song" not in entries

    songs = _read(data_root, "song_lists/songs.json")
    assert {s["link"] for s in songs} == {"l1", "l2"}  # untouched


# --- Ignored Duplicates: cleanup (US-4) ------------------------------------


def test_cleanup_removes_stale_links(client, data_root):
    _write(data_root, "song_lists/songs.json", [_song("l1"), _song("l2")])
    _write(
        data_root,
        "song_lists/ignore_duplicates.json",
        {"Some Song": [_song("l1"), _song("l2"), _song("stale")]},
    )

    resp = client.post("/api/ignore-duplicates/cleanup")
    assert resp.status_code == 200
    assert resp.get_json() == {"ok": True, "removed_links": 1, "removed_groups": 0}

    entries = _read(data_root, "song_lists/ignore_duplicates.json")
    assert {s["link"] for s in entries["Some Song"]} == {"l1", "l2"}


def test_cleanup_removes_single_song_groups(client, data_root):
    _write(data_root, "song_lists/songs.json", [_song("l1")])
    _write(
        data_root,
        "song_lists/ignore_duplicates.json",
        {"Some Song": [_song("l1"), _song("stale")]},
    )

    resp = client.post("/api/ignore-duplicates/cleanup")
    assert resp.get_json() == {"ok": True, "removed_links": 1, "removed_groups": 1}

    entries = _read(data_root, "song_lists/ignore_duplicates.json")
    assert entries == {}


def test_cleanup_no_op_on_clean_data(client, data_root):
    _write(data_root, "song_lists/songs.json", [_song("l1"), _song("l2")])
    _write(
        data_root,
        "song_lists/ignore_duplicates.json",
        {"Some Song": [_song("l1"), _song("l2")]},
    )

    resp = client.post("/api/ignore-duplicates/cleanup")
    assert resp.get_json() == {"ok": True, "removed_links": 0, "removed_groups": 0}

    entries = _read(data_root, "song_lists/ignore_duplicates.json")
    assert {s["link"] for s in entries["Some Song"]} == {"l1", "l2"}


# --- Songs: add-tag (spec 008, US-4) ---------------------------------------


def test_add_tag_preserves_existing_tags(client, data_root):
    _write(data_root, "song_lists/songs.json", [_song("l1", tags="rock, 70s")])

    resp = client.patch("/api/songs/0/tags", json={"tag": "roadtrip"})
    assert resp.status_code == 200
    assert resp.get_json() == {"ok": True}

    songs = _read(data_root, "song_lists/songs.json")
    assert songs[0]["tags"] == "70s, roadtrip, rock"


def test_add_tag_rejects_genre_tag(client, data_root):
    _write(data_root, "song_lists/songs.json", [_song("l1", tags="")])

    resp = client.patch("/api/songs/0/tags", json={"tag": "rock"})
    assert resp.status_code == 400

    songs = _read(data_root, "song_lists/songs.json")
    assert songs[0]["tags"] == ""


def test_add_tag_rejects_era_tag(client, data_root):
    _write(data_root, "song_lists/songs.json", [_song("l1", tags="")])

    resp = client.patch("/api/songs/0/tags", json={"tag": "80s"})
    assert resp.status_code == 400

    songs = _read(data_root, "song_lists/songs.json")
    assert songs[0]["tags"] == ""


def test_add_tag_404_on_out_of_range_index(client, data_root):
    _write(data_root, "song_lists/songs.json", [_song("l1")])

    resp = client.patch("/api/songs/5/tags", json={"tag": "roadtrip"})
    assert resp.status_code == 404


def test_add_tag_requires_tag_in_body(client, data_root):
    _write(data_root, "song_lists/songs.json", [_song("l1")])

    resp = client.patch("/api/songs/0/tags", json={})
    assert resp.status_code == 400


# --- Import / Export: per-file row counts ----------------------------------


def _write_txt(data_root: Path, rel_path: str, content: str) -> None:
    path = data_root / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_import_list_includes_line_counts(client, data_root):
    _write_txt(data_root, "songs_import/one.txt", "url-a\nurl-b\n\nurl-c\n")
    _write_txt(data_root, "songs_import/empty.txt", "")

    resp = client.get("/api/import/")
    assert resp.status_code == 200
    by_name = {row["name"]: row["count"] for row in resp.get_json()}
    assert by_name == {"one": 3, "empty": 0}


def test_export_list_includes_line_counts(client, data_root):
    _write_txt(data_root, "playlist_export/playlist.txt", "url-a\nurl-b\n")

    resp = client.get("/api/export/")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body == [{"name": "playlist", "count": 2}]


# --- Grouped songs: "grouped" tag applied on save ---------------------------


def test_create_group_tags_its_songs_as_grouped(client, data_root):
    _write(data_root, "song_lists/grouped_songs.json", [])
    _write(
        data_root,
        "song_lists/songs.json",
        [_song("l1", tags="70s, rock"), _song("l2", tags="")],
    )

    resp = client.post(
        "/api/grouped-songs/",
        json={"artist": "Artist", "group_name": "Group", "songs": ["l1", "l2"]},
    )
    assert resp.status_code == 201

    songs = _read(data_root, "song_lists/songs.json")
    assert songs[0]["tags"] == "70s, grouped, rock"
    assert songs[1]["tags"] == "grouped"


def test_create_group_does_not_tag_unrelated_songs(client, data_root):
    _write(data_root, "song_lists/grouped_songs.json", [])
    _write(data_root, "song_lists/songs.json", [_song("l1", tags="")])

    resp = client.post(
        "/api/grouped-songs/",
        json={"artist": "Artist", "group_name": "Group", "songs": ["other-link"]},
    )
    assert resp.status_code == 201

    songs = _read(data_root, "song_lists/songs.json")
    assert songs[0]["tags"] == ""


def test_update_group_tags_newly_added_song(client, data_root):
    group = {"artist": "Artist", "group_name": "Group", "songs": ["l1"]}
    _write(data_root, "song_lists/grouped_songs.json", [group])
    _write(
        data_root,
        "song_lists/songs.json",
        [_song("l1", tags="grouped"), _song("l2", tags="")],
    )

    resp = client.put(
        "/api/grouped-songs/0",
        json={"artist": "Artist", "group_name": "Group", "songs": ["l1", "l2"]},
    )
    assert resp.status_code == 200

    songs = _read(data_root, "song_lists/songs.json")
    assert songs[0]["tags"] == "grouped"
    assert songs[1]["tags"] == "grouped"
