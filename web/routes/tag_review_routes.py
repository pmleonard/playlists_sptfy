from analysis import (
    ERA_TAGS,
    classify_song,
    decade_for_year,
    is_likely_reissue,
    parse_year,
    tags_to_set,
)
from analysis import candidate_year as compute_candidate_year
from file_utils import read_json, write_json
from flask import Blueprint, jsonify, request

bp = Blueprint("tag_review", __name__, url_prefix="/api/tag-review")

FILE = "song_lists/songs.json"
DUP_FILE = "song_lists/possible_duplicates.json"
IGNORE_FILE = "song_lists/ignore_duplicates.json"


@bp.get("/")
def get_anomalies():
    songs = read_json(FILE)

    try:
        dup_data = read_json(DUP_FILE)
    except Exception:
        dup_data = {}
    try:
        ignore_data = read_json(IGNORE_FILE)
    except Exception:
        ignore_data = {}

    rows = []
    for idx, song in enumerate(songs):
        category = classify_song(song)
        if category is None:
            continue

        released = song.get("released")
        album = str(song.get("album") or "")
        try:
            cand_year = compute_candidate_year(song, songs, dup_data, ignore_data)
        except Exception:
            cand_year = None

        rows.append(
            {
                "idx": idx,
                "category": category,
                "artist": str(song.get("artist") or ""),
                "title": str(song.get("title") or ""),
                "album": album,
                "released": released,
                "current_tags": sorted(tags_to_set(song.get("tags", "")) & ERA_TAGS),
                "expected_decade": decade_for_year(parse_year(released)),
                "likely_reissue": is_likely_reissue(album),
                "candidate_year": cand_year,
            }
        )

    rows.sort(key=lambda r: (r["artist"].lower(), r["title"].lower()))
    return jsonify(rows)


@bp.patch("/<int:idx>")
def update_tag(idx):
    body = request.get_json(silent=True)
    if not isinstance(body, dict) or "tag" not in body:
        return jsonify({"error": "tag required"}), 400

    tag = body["tag"]
    if tag is not None and tag not in ERA_TAGS:
        return jsonify({"error": "Invalid tag"}), 400

    songs = read_json(FILE)
    if idx < 0 or idx >= len(songs):
        return jsonify({"error": "Index out of range"}), 404

    remaining = tags_to_set(songs[idx].get("tags", "")) - ERA_TAGS
    if tag is not None:
        remaining.add(tag)
    songs[idx]["tags"] = ", ".join(sorted(remaining))
    write_json(FILE, songs)
    return jsonify({"ok": True})
