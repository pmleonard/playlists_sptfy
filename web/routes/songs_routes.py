from file_utils import read_json, write_json
from flask import Blueprint, jsonify, request

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
