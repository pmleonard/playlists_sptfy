from file_utils import delete_file, list_txt_files, read_txt, write_txt
from flask import Blueprint, jsonify, request

bp = Blueprint("import", __name__, url_prefix="/api/import")
DIR = "songs_import"


@bp.get("/")
def list_files():
    return jsonify(list_txt_files(DIR))


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
