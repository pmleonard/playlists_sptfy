from file_utils import read_json, write_json
from flask import Blueprint, jsonify, request

bp = Blueprint("config", __name__, url_prefix="/api/config")
FILE = "settings/config.json"


@bp.get("/")
def get_config():
    return jsonify(read_json(FILE))


@bp.put("/")
def save_config():
    body = request.get_json()
    if not isinstance(body, dict):
        return jsonify({"error": "Body must be a JSON object"}), 400
    write_json(FILE, body)
    return jsonify({"ok": True})
