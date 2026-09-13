from file_utils import delete_file, list_txt_files, read_txt, write_txt
from flask import Blueprint, jsonify, request

bp = Blueprint("import", __name__, url_prefix="/api/import")
DIR = "songs_import"


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


@bp.post("/<name>")
def create_file(name):
    try:
        read_txt(f"{DIR}/{name}.txt")
        return jsonify({"error": "File already exists"}), 409
    except FileNotFoundError:
        pass
    content = (request.get_json() or {}).get("content", "")
    write_txt(f"{DIR}/{name}.txt", content)
    return jsonify({"ok": True}), 201


@bp.put("/<name>")
def update_file(name):
    try:
        read_txt(f"{DIR}/{name}.txt")
    except FileNotFoundError:
        return jsonify({"error": "Not found"}), 404
    content = (request.get_json() or {}).get("content", "")
    write_txt(f"{DIR}/{name}.txt", content)
    return jsonify({"ok": True})


@bp.delete("/<name>")
def delete(name):
    try:
        delete_file(f"{DIR}/{name}.txt")
        return jsonify({"ok": True})
    except FileNotFoundError:
        return jsonify({"error": "Not found"}), 404
