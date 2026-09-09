from analysis import build_album_catalog
from file_utils import read_json
from flask import Blueprint, jsonify

bp = Blueprint("albums", __name__, url_prefix="/api/albums")

FILE = "song_lists/songs.json"


@bp.get("/")
def get_catalog():
    songs = read_json(FILE)
    rows = build_album_catalog(songs)
    rows.sort(key=lambda r: (r["is_various_artists"], r["artist"].lower(), r["album"].lower()))
    return jsonify(rows)
