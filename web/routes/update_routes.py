import io
import logging

from file_utils import read_json
from flask import Blueprint, jsonify

from playlists_sptfy.main import main as run_pipeline

bp = Blueprint("update", __name__, url_prefix="/api/update")


@bp.post("/run")
def run():
    log_stream = io.StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setFormatter(logging.Formatter("%(levelname)s:%(name)s:%(message)s"))
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    try:
        run_pipeline()
        ok = True
    except Exception:
        logging.getLogger(__name__).exception("Update pipeline failed")
        ok = False
    finally:
        root_logger.removeHandler(handler)

    return jsonify(
        {
            "ok": ok,
            "returncode": 0 if ok else 1,
            "stderr": log_stream.getvalue()[-4000:],
        }
    )


@bp.get("/summary")
def summary():
    return jsonify(read_json("song_lists/run_summary.json"))
