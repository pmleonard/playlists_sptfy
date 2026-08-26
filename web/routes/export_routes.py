from file_utils import list_txt_files, read_txt
from flask import Blueprint, jsonify

bp = Blueprint("export", __name__, url_prefix="/api/export")
DIR = "playlist_export"


@bp.get("/")
def list_files():
    return jsonify(list_txt_files(DIR))


@bp.get("/<name>")
def get_file(name):
    try:
        return jsonify({"content": read_txt(f"{DIR}/{name}.txt")})
    except FileNotFoundError:
        return jsonify({"error": "Not found"}), 404
