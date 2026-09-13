from analysis import ERA_TAGS, tags_to_set
from file_utils import read_json, write_json
from flask import Blueprint, jsonify, request
from genre_analysis import GENRE_TAGS

bp = Blueprint("songs", __name__, url_prefix="/api/songs")

FILE = "song_lists/songs.json"


@bp.get("/")
def get_songs():
    return jsonify(read_json(FILE))


@bp.put("/<int:idx>")
def update_song(idx):
    body = request.get_json(silent=True)
    if not body:
        return jsonify({"error": "Body required"}), 400
    data = read_json(FILE)
    if idx < 0 or idx >= len(data):
        return jsonify({"error": "Index out of range"}), 404
    data[idx] = body
    write_json(FILE, data)
    return jsonify({"ok": True})


@bp.delete("/<int:idx>")
def delete_song(idx):
    data = read_json(FILE)
    if idx < 0 or idx >= len(data):
        return jsonify({"error": "Index out of range"}), 404
    data.pop(idx)
    write_json(FILE, data)
    return jsonify({"ok": True})


@bp.patch("/<int:idx>/tags")
def add_tag(idx):
    body = request.get_json(silent=True)
    tag = body.get("tag") if isinstance(body, dict) else None
    if not tag or not isinstance(tag, str):
        return jsonify({"error": "tag required"}), 400
    tag = tag.strip().lower()
    if tag in GENRE_TAGS or tag in ERA_TAGS:
        return jsonify({"error": "Genre/Era tags must be assigned via their review tabs"}), 400

    songs = read_json(FILE)
    if idx < 0 or idx >= len(songs):
        return jsonify({"error": "Index out of range"}), 404

    current = tags_to_set(songs[idx].get("tags", ""))
    current.add(tag)
    songs[idx]["tags"] = ", ".join(sorted(current))
    write_json(FILE, songs)
    return jsonify({"ok": True})
