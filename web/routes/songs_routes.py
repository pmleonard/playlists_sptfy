from file_utils import read_json
from flask import Blueprint, jsonify

bp = Blueprint("songs", __name__, url_prefix="/api/songs")


@bp.get("/")
def get_songs():
    return jsonify(read_json("song_lists/songs.json"))
