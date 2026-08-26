from file_utils import read_json, write_json
from flask import Blueprint, jsonify, request

bp = Blueprint("settings", __name__, url_prefix="/api/settings")
FILE = "settings/settings.json"


@bp.get("/")
def get_settings():
    return jsonify(read_json(FILE))


@bp.put("/")
def save_settings():
    body = request.get_json()
    if not isinstance(body, dict):
        return jsonify({"error": "Body must be a JSON object"}), 400
    write_json(FILE, body)
    return jsonify({"ok": True})
