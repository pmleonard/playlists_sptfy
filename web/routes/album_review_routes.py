from analysis import find_album_clusters
from file_utils import read_json, write_json
from flask import Blueprint, jsonify, request

bp = Blueprint("album_review", __name__, url_prefix="/api/album-review")

FILE = "song_lists/songs.json"


@bp.get("/")
def get_clusters():
    songs = read_json(FILE)
    return jsonify(find_album_clusters(songs))


@bp.post("/merge")
def merge():
    body = request.get_json(silent=True) or {}
    artist = str(body.get("artist", "")).strip()
    to_album = str(body.get("to_album", "")).strip()
    from_albums = body.get("from_albums") or []

    if not to_album or not from_albums:
        return jsonify({"error": "to_album and from_albums required"}), 400

    from_albums_str = {str(a) for a in from_albums}

    songs = read_json(FILE)
    artist_lower = artist.lower()
    changed = 0
    for song in songs:
        if (
            str(song.get("artist", "")).strip().lower() == artist_lower
            and str(song.get("album") or "") in from_albums_str
        ):
            song["album"] = to_album
            changed += 1

    write_json(FILE, songs)
    return jsonify({"ok": True, "changed": changed})
