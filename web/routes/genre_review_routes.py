from analysis import tags_to_set
from file_utils import read_json, write_json
from flask import Blueprint, jsonify, request
from genre_analysis import GENRE_TAGS, classify_genre, compute_dominant_genres

bp = Blueprint("genre_review", __name__, url_prefix="/api/genre-review")

FILE = "song_lists/songs.json"
DISMISSED_MISMATCH_FILE = "song_lists/dismissed_genre_mismatches.json"


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
    dominant = compute_dominant_genres(songs)
    dismissed_mismatches = _read_dismissed_mismatches()

    rows = []
    for idx, song in enumerate(songs):
        category = classify_genre(song, dominant)
        if category is None:
            continue
        if category == "mismatch" and str(song.get("link") or "") in dismissed_mismatches:
            continue

        artist = str(song.get("artist") or "").strip()
        rows.append(
            {
                "idx": idx,
                "category": category,
                "artist": artist,
                "title": str(song.get("title") or ""),
                "album": str(song.get("album") or ""),
                "released": song.get("released"),
                "current_tags": sorted(tags_to_set(song.get("tags", "")) & GENRE_TAGS),
                "proposed_genre": dominant.get(artist),
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
    if tag is not None and tag not in GENRE_TAGS:
        return jsonify({"error": "Invalid tag"}), 400

    songs = read_json(FILE)
    if idx < 0 or idx >= len(songs):
        return jsonify({"error": "Index out of range"}), 404

    remaining = tags_to_set(songs[idx].get("tags", "")) - GENRE_TAGS
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


@bp.post("/apply-proposed-bulk")
def apply_proposed_bulk():
    """Set each given song's genre tag to its artist's proposed (dominant)
    genre, for the "Apply Proposed Tag to All Filtered" bulk action on
    Missing rows. The dominant-genre snapshot is computed once up front so
    the whole batch applies against what the user actually saw."""
    body = request.get_json(silent=True) or {}
    songs = read_json(FILE)
    idxs = _valid_idxs(body, len(songs))
    if idxs is None:
        return jsonify({"error": "idxs required"}), 400

    dominant = compute_dominant_genres(songs)

    changed = 0
    for idx in idxs:
        song = songs[idx]
        artist = str(song.get("artist") or "").strip()
        proposed = dominant.get(artist)
        if proposed is None:
            continue
        remaining = tags_to_set(song.get("tags", "")) - GENRE_TAGS
        remaining.add(proposed)
        song["tags"] = ", ".join(sorted(remaining))
        changed += 1

    write_json(FILE, songs)
    return jsonify({"ok": True, "changed": changed})
