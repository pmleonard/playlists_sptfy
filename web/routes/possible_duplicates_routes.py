from file_utils import read_json, write_json
from flask import Blueprint, jsonify, request

bp = Blueprint("possible_duplicates", __name__, url_prefix="/api/possible-duplicates")
FILE = "song_lists/possible_duplicates.json"


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


IGNORE_FILE = "song_lists/ignore_duplicates.json"


@bp.post("/<path:key>/move-to-ignored")
def move_to_ignored(key):
    dup_data = read_json(FILE)
    if key not in dup_data:
        return jsonify({"error": "Key not found"}), 404
    songs = dup_data.pop(key)
    ignore_data = read_json(IGNORE_FILE)
    if key in ignore_data:
        ignore_data[key].extend(songs)
    else:
        ignore_data[key] = songs
    write_json(IGNORE_FILE, ignore_data)
    write_json(FILE, dup_data)
    return jsonify({"ok": True})


@bp.delete("/<path:key>/songs/<int:song_idx>")
def delete_song(key, song_idx):
    dup_data = read_json(FILE)
    if key not in dup_data:
        return jsonify({"error": "Key not found"}), 404
    songs = dup_data[key]
    if song_idx < 0 or song_idx >= len(songs):
        return jsonify({"error": "Song index out of range"}), 404

    removed_link = songs[song_idx].get("link")
    songs.pop(song_idx)

    entry_deleted = len(songs) <= 1
    if entry_deleted:
        del dup_data[key]
    write_json(FILE, dup_data)

    if removed_link:
        song_data = read_json("song_lists/songs.json")
        song_data = [s for s in song_data if s.get("link") != removed_link]
        write_json("song_lists/songs.json", song_data)

    return jsonify({"ok": True, "entry_deleted": entry_deleted})


@bp.delete("/<path:key>")
def delete(key):
    data = read_json(FILE)
    if key not in data:
        return jsonify({"error": "Key not found"}), 404
    del data[key]
    write_json(FILE, data)
    return jsonify({"ok": True})
