import os
import subprocess
from pathlib import Path

from file_utils import read_json
from flask import Blueprint, jsonify

bp = Blueprint("update", __name__, url_prefix="/api/update")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_TIMEOUT = int(os.environ.get("UPDATE_TIMEOUT_SECONDS", 300))


@bp.post("/run")
def run():
    try:
        result = subprocess.run(
            ["make", "run"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return jsonify({"ok": False, "returncode": -1, "stderr": "Timed out"}), 200
    return jsonify(
        {
            "ok": result.returncode == 0,
            "returncode": result.returncode,
            "stderr": result.stderr[-4000:],
        }
    )


@bp.get("/summary")
def summary():
    return jsonify(read_json("song_lists/run_summary.json"))
