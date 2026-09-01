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
DISMISSED_MISMATCH_FILE = "song_lists/dismissed_tag_mismatches.json"


def _read_dismissed_mismatches() -> set:
    try:
        data = read_json(DISMISSED_MISMATCH_FILE)
    except Exception:
        return set()
    if not isinstance(data, list):
        return set()
    return {str(link) for link in data if link}


def _write_dismissed_mismatches(links: set) -> None:
    write_json(DISMISSED_MISMATCH_FILE, sorted(links))


def _valid_idxs(body, songs_len: int) -> list[int] | None:
    """Parse+validate body["idxs"] as a non-empty list of in-range ints, or None if invalid."""
    idxs = body.get("idxs") if isinstance(body, dict) else None
    if not isinstance(idxs, list) or not idxs:
        return None
    parsed = []
    for raw in idxs:
        try:
            idx = int(raw)
        except (TypeError, ValueError):
            continue
        if 0 <= idx < songs_len:
            parsed.append(idx)
    return parsed or None


@bp.get("/")
def get_anomalies():
    songs = read_json(FILE)
    dismissed_mismatches = _read_dismissed_mismatches()

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
        if category == "mismatch" and str(song.get("link") or "") in dismissed_mismatches:
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


@bp.post("/dismiss-mismatch")
def dismiss_mismatch():
    """Permanently dismiss one or more mismatch rows (by song link) so they never
    reappear, unlike the session-only client-side dismiss used for other categories."""
    body = request.get_json(silent=True) or {}
    songs = read_json(FILE)
    idxs = _valid_idxs(body, len(songs))
    if idxs is None:
        return jsonify({"error": "idxs required"}), 400

    dismissed = _read_dismissed_mismatches()
    added = 0
    for idx in idxs:
        link = str(songs[idx].get("link") or "").strip()
        if link and link not in dismissed:
            dismissed.add(link)
            added += 1

    _write_dismissed_mismatches(dismissed)
    return jsonify({"ok": True, "dismissed": added})


@bp.post("/apply-expected-bulk")
def apply_expected_bulk():
    """Set each given song's era tag to its own expected decade (derived from
    `released`), for the "Apply Expected Tag to All Filtered" bulk action on
    Missing rows."""
    body = request.get_json(silent=True) or {}
    songs = read_json(FILE)
    idxs = _valid_idxs(body, len(songs))
    if idxs is None:
        return jsonify({"error": "idxs required"}), 400

    changed = 0
    for idx in idxs:
        song = songs[idx]
        expected = decade_for_year(parse_year(song.get("released")))
        if expected is None:
            continue
        remaining = tags_to_set(song.get("tags", "")) - ERA_TAGS
        remaining.add(expected)
        song["tags"] = ", ".join(sorted(remaining))
        changed += 1

    write_json(FILE, songs)
    return jsonify({"ok": True, "changed": changed})
