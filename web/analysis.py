from __future__ import annotations

import re

ERA_TAGS = {"50s", "60s", "70s", "80s", "90s", "2000s", "2010s"}

ERA_DECADE_RANGES = {
    "50s": (1950, 1959),
    "60s": (1960, 1969),
    "70s": (1970, 1979),
    "80s": (1980, 1989),
    "90s": (1990, 1999),
    "2000s": (2000, 2009),
    "2010s": (2010, 2019),
}

REISSUE_KEYWORDS = (
    "remaster",
    "deluxe",
    "anniversary",
    "greatest hits",
    "best of",
    "live",
    "compilation",
    "anthology",
)

REISSUE_QUALIFIER = re.compile(
    r"[\(\[][^)\]]*\b("
    r"remaster(ed)?|deluxe|anniversary|expanded|bonus track|"
    r"special edition|reissue"
    r")\b[^)\]]*[\)\]]",
    re.IGNORECASE,
)

_YEAR_RE = re.compile(r"(\d{4})")


def tags_to_set(tags) -> set[str]:
    parts = [part.strip().lower() for part in str(tags).split(",")]
    return {part for part in parts if part}


def parse_year(released) -> int | None:
    if not released:
        return None
    match = _YEAR_RE.search(str(released))
    if not match:
        return None
    return int(match.group(1))


def decade_for_year(year: int | None) -> str | None:
    if year is None:
        return None
    for tag, (lo, hi) in ERA_DECADE_RANGES.items():
        if lo <= year <= hi:
            return tag
    return None


def classify_song(song: dict) -> str | None:
    """Returns one of 'mismatch' / 'missing' / 'multiple', or None if no anomaly."""
    present = tags_to_set(song.get("tags", "")) & ERA_TAGS
    expected = decade_for_year(parse_year(song.get("released")))

    if len(present) >= 2:
        return "multiple"
    if len(present) == 1:
        (only,) = present
        return "mismatch" if expected is not None and only != expected else None
    return "missing" if expected is not None else None


def is_likely_reissue(album: str) -> bool:
    a = str(album or "").lower()
    return any(kw in a for kw in REISSUE_KEYWORDS)


def _song_key(record: dict) -> tuple[str, str]:
    return (
        str(record.get("artist", "")).strip().lower(),
        str(record.get("title", "")).strip().lower(),
    )


def candidate_year(song, all_songs, dup_data, ignore_data) -> int | None:
    key = _song_key(song)
    years = []
    for other in all_songs:
        if _song_key(other) == key:
            y = parse_year(other.get("released"))
            if y is not None:
                years.append(y)
    for dup_source in (dup_data, ignore_data):
        if not dup_source:
            continue
        for entries in dup_source.values():
            for entry in entries:
                if _song_key(entry) == key:
                    y = parse_year(entry.get("released"))
                    if y is not None:
                        years.append(y)
    return min(years) if years else None


def normalize_album(album: str) -> str:
    stripped = REISSUE_QUALIFIER.sub("", str(album or ""))
    return " ".join(stripped.split()).strip().lower()


def find_gaps(track_numbers: list[int]) -> list[int]:
    present = set(track_numbers)
    if len(present) < 2:
        return []
    lo, hi = min(present), max(present)
    return [n for n in range(lo, hi + 1) if n not in present]


def parse_track(track) -> int | None:
    """Coerce a song's track field to int; some records store it as a numeric
    string (or blank string) rather than an int, which would otherwise make
    that track silently vanish from gap detection."""
    if isinstance(track, bool):
        return None
    if isinstance(track, int):
        return track
    if isinstance(track, str) and track.strip().isdigit():
        return int(track.strip())
    return None


def find_album_clusters(songs: list[dict]) -> list[dict]:
    clusters: dict[tuple[str, str], dict] = {}

    for song in songs:
        album = str(song.get("album") or "").strip()
        if not album:
            continue
        artist = str(song.get("artist", "")).strip()
        key = (artist.lower(), normalize_album(album))
        cluster = clusters.setdefault(
            key, {"artist": artist, "normalized_key": key[1], "variants": {}}
        )
        variant = cluster["variants"].setdefault(album, {"album": album, "tracks": set()})
        track = parse_track(song.get("track"))
        if track is not None:
            variant["tracks"].add(track)

    result = []
    for cluster in clusters.values():
        variants = list(cluster["variants"].values())
        union_tracks = set()
        for variant in variants:
            union_tracks |= variant["tracks"]
        gaps = find_gaps(sorted(union_tracks))

        if len(variants) <= 1 and not gaps:
            continue

        result.append(
            {
                "artist": cluster["artist"],
                "normalized_key": cluster["normalized_key"],
                "variants": [
                    {
                        "album": variant["album"],
                        "track_count": len(variant["tracks"]),
                        "tracks": sorted(variant["tracks"]),
                    }
                    for variant in variants
                ],
                "gaps": gaps,
            }
        )

    return result
