from file_utils import list_txt_files, read_txt
from flask import Blueprint, jsonify

bp = Blueprint("export", __name__, url_prefix="/api/export")
DIR = "playlist_export"


@bp.get("/")
def list_files():
    names = list_txt_files(DIR)
    return jsonify([{"name": name, "count": _line_count(f"{DIR}/{name}.txt")} for name in names])


def _line_count(rel_path: str) -> int:
    content = read_txt(rel_path)
    return sum(1 for line in content.splitlines() if line.strip())


@bp.get("/<name>")
def get_file(name):
    try:
        return jsonify({"content": read_txt(f"{DIR}/{name}.txt")})
    except FileNotFoundError:
        return jsonify({"error": "Not found"}), 404
