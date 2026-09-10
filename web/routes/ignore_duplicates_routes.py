from file_utils import read_json, write_json
from flask import Blueprint, jsonify, request

bp = Blueprint("ignore_duplicates", __name__, url_prefix="/api/ignore-duplicates")
FILE = "song_lists/ignore_duplicates.json"
SONGS_FILE = "song_lists/songs.json"


@bp.get("/")
def get_all():
    return jsonify(read_json(FILE))


@bp.post("/")
def create():
    body = request.get_json() or {}
    key = body.get("key")
    songs = body.get("songs", [])
    if not key:
        return jsonify({"error": "key required"}), 400
    data = read_json(FILE)
    if key in data:
        return jsonify({"error": "Key already exists"}), 409
    data[key] = songs
    write_json(FILE, data)
    return jsonify({"ok": True}), 201


@bp.put("/<path:key>")
def update(key):
    body = request.get_json() or {}
    songs = body.get("songs")
    if songs is None:
        return jsonify({"error": "songs required"}), 400
    data = read_json(FILE)
    if key not in data:
        return jsonify({"error": "Key not found"}), 404
    data[key] = songs
    write_json(FILE, data)
    return jsonify({"ok": True})


@bp.delete("/<path:key>/songs/<int:song_idx>")
def delete_song(key, song_idx):
    data = read_json(FILE)
    if key not in data:
        return jsonify({"error": "Key not found"}), 404
    songs = data[key]
    if song_idx < 0 or song_idx >= len(songs):
        return jsonify({"error": "Song index out of range"}), 404

    removed_link = songs[song_idx].get("link")
    songs.pop(song_idx)

    entry_deleted = len(songs) <= 1
    if entry_deleted:
        del data[key]
    write_json(FILE, data)

    if removed_link:
        song_data = read_json(SONGS_FILE)
        song_data = [s for s in song_data if s.get("link") != removed_link]
        write_json(SONGS_FILE, song_data)

    return jsonify({"ok": True, "entry_deleted": entry_deleted})


@bp.delete("/<path:key>")
def delete(key):
    data = read_json(FILE)
    if key not in data:
        return jsonify({"error": "Key not found"}), 404
    del data[key]
    write_json(FILE, data)
    return jsonify({"ok": True})


@bp.post("/cleanup")
def cleanup():
    data = read_json(FILE)
    songs = read_json(SONGS_FILE)
    live_links = {s.get("link") for s in songs if s.get("link")}

    removed_links = 0
    removed_groups = 0
    cleaned = {}
    for key, group_songs in data.items():
        kept = [s for s in group_songs if s.get("link") in live_links]
        removed_links += len(group_songs) - len(kept)
        if len(kept) <= 1:
            removed_groups += 1
            continue
        cleaned[key] = kept

    write_json(FILE, cleaned)
    return jsonify({"ok": True, "removed_links": removed_links, "removed_groups": removed_groups})
