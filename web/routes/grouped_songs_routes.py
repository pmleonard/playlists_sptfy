from analysis import tags_to_set
from file_utils import read_json, write_json
from flask import Blueprint, jsonify, request

bp = Blueprint("grouped_songs", __name__, url_prefix="/api/grouped-songs")
FILE = "song_lists/grouped_songs.json"
SONGS_FILE = "song_lists/songs.json"


def _tag_grouped_songs(song_links) -> None:
    """Add the "grouped" tag to every song in songs.json whose link appears
    in song_links, matching the tags_to_set/sorted-join convention used by
    the /api/songs/<idx>/tags endpoint."""
    links = {link for link in (song_links or []) if link}
    if not links:
        return
    songs = read_json(SONGS_FILE)
    changed = False
    for song in songs:
        if song.get("link") not in links:
            continue
        current = tags_to_set(song.get("tags", ""))
        if "grouped" not in current:
            current.add("grouped")
            song["tags"] = ", ".join(sorted(current))
            changed = True
    if changed:
        write_json(SONGS_FILE, songs)


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
    _tag_grouped_songs(entry.get("songs"))
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
    _tag_grouped_songs(entry.get("songs"))
    return jsonify({"ok": True})


@bp.delete("/<int:index>")
def delete(index):
    data = read_json(FILE)
    if index < 0 or index >= len(data):
        return jsonify({"error": "Index out of range"}), 404
    data.pop(index)
    write_json(FILE, data)
    return jsonify({"ok": True})
