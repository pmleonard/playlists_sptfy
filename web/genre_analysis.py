from __future__ import annotations

from analysis import tags_to_set

GENRE_TAGS = {
    "rock",
    "pop",
    "oldies",
    "reggae",
    "country",
    "hiphop",
    "world",
    "folk",
    "edm",
    "classical",
    "rnb",
    "jazz",
    "soul",
}


def compute_dominant_genres(songs: list[dict]) -> dict[str, str]:
    """For each artist, the genre tag present on the most of their songs.

    Ties are broken alphabetically for determinism. Artists with no
    genre-tagged songs at all are omitted (there is nothing to propose).
    """
    counts: dict[str, dict[str, int]] = {}
    for song in songs:
        artist = str(song.get("artist") or "").strip()
        if not artist:
            continue
        present = tags_to_set(song.get("tags", "")) & GENRE_TAGS
        if not present:
            continue
        bucket = counts.setdefault(artist, {})
        for genre in present:
            bucket[genre] = bucket.get(genre, 0) + 1

    dominant = {}
    for artist, bucket in counts.items():
        genre, _count = min(bucket.items(), key=lambda kv: (-kv[1], kv[0]))
        dominant[artist] = genre
    return dominant


def classify_genre(song: dict, dominant_by_artist: dict[str, str]) -> str | None:
    """Returns one of 'mismatch' / 'missing' / 'multiple', or None if no anomaly."""
    present = tags_to_set(song.get("tags", "")) & GENRE_TAGS
    artist = str(song.get("artist") or "").strip()
    expected = dominant_by_artist.get(artist)

    if len(present) >= 2:
        return "multiple"
    if len(present) == 1:
        (only,) = present
        return "mismatch" if expected is not None and only != expected else None
    return "missing" if expected is not None else None
