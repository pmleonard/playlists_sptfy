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
