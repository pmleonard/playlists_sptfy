from file_utils import read_json, write_json
from flask import Blueprint, jsonify, request

bp = Blueprint("grouped_songs", __name__, url_prefix="/api/grouped-songs")
FILE = "song_lists/grouped_songs.json"


@bp.get("/")
def get_all():
    return jsonify(read_json(FILE))


@bp.post("/")
def create():
    entry = request.get_json()
    if not entry:
        return jsonify({"error": "Body required"}), 400
    data = read_json(FILE)
    data.append(entry)
    write_json(FILE, data)
    return jsonify({"ok": True, "index": len(data) - 1}), 201


@bp.put("/<int:index>")
def update(index):
    entry = request.get_json()
    if not entry:
        return jsonify({"error": "Body required"}), 400
    data = read_json(FILE)
    if index < 0 or index >= len(data):
        return jsonify({"error": "Index out of range"}), 404
    data[index] = entry
    write_json(FILE, data)
    return jsonify({"ok": True})


@bp.delete("/<int:index>")
def delete(index):
    data = read_json(FILE)
    if index < 0 or index >= len(data):
        return jsonify({"error": "Index out of range"}), 404
    data.pop(index)
    write_json(FILE, data)
    return jsonify({"ok": True})
