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


def _artist_components(artist: str) -> frozenset[str]:
    return frozenset(part.strip().lower() for part in artist.split(",") if part.strip())


def _same_artist_family(a: frozenset[str], b: frozenset[str]) -> bool:
    """True when one artist credit is a subset of the other's comma-separated
    components, e.g. {'yes'} vs {'yes', 'steve lipson'} — a featured/secondary
    artist credited alongside the album's main artist on just some tracks."""
    return bool(a) and bool(b) and (a <= b or b <= a)


def find_album_clusters(songs: list[dict]) -> list[dict]:
    # Group by normalized album first, deferring artist grouping to a second
    # pass — some tracks on an album are credited to "Main Artist, Guest"
    # rather than plain "Main Artist", which would otherwise split one album
    # into two clusters and make it look like tracks were missing.
    by_album: dict[str, dict[str, dict]] = {}

    for song in songs:
        album = str(song.get("album") or "").strip()
        if not album:
            continue
        artist = str(song.get("artist", "")).strip()
        if not artist:
            continue
        norm = normalize_album(album)
        artist_bucket = by_album.setdefault(norm, {})
        entry = artist_bucket.setdefault(artist, {"variants": {}})
        variant = entry["variants"].setdefault(album, {"album": album, "tracks": set()})
        track = parse_track(song.get("track"))
        if track is not None:
            variant["tracks"].add(track)

    result = []
    for norm, artist_bucket in by_album.items():
        artists = list(artist_bucket.keys())
        components = {a: _artist_components(a) for a in artists}

        parent = {a: a for a in artists}

        def find(x: str) -> str:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(x: str, y: str) -> None:
            rx, ry = find(x), find(y)
            if rx != ry:
                parent[rx] = ry

        for i in range(len(artists)):
            for j in range(i + 1, len(artists)):
                a, b = artists[i], artists[j]
                if _same_artist_family(components[a], components[b]):
                    union(a, b)

        groups: dict[str, list[str]] = {}
        for a in artists:
            groups.setdefault(find(a), []).append(a)

        for members in groups.values():
            merged_variants: dict[str, dict] = {}
            track_totals = {
                m: sum(len(v["tracks"]) for v in artist_bucket[m]["variants"].values())
                for m in members
            }
            for m in members:
                for album_name, v in artist_bucket[m]["variants"].items():
                    mv = merged_variants.setdefault(
                        album_name, {"album": album_name, "tracks": set()}
                    )
                    mv["tracks"] |= v["tracks"]

            canonical_artist = max(members, key=lambda m: (track_totals[m], -len(components[m])))

            variants = list(merged_variants.values())
            union_tracks = set()
            for variant in variants:
                union_tracks |= variant["tracks"]
            gaps = find_gaps(sorted(union_tracks))

            if len(variants) <= 1 and not gaps:
                continue

            result.append(
                {
                    "artist": canonical_artist,
                    "normalized_key": norm,
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


def resolve_album_artist(songs_for_album: list[dict]) -> tuple[str, bool]:
    """Returns (display_artist, is_various_artists) for one raw `album` string's songs.

    Reuses the same artist-family union-find as find_album_clusters, but requires the
    winning family to hold a strict majority of tracks (not just a plurality) — a two-way
    50/50 split falls to "Various Artists" rather than an arbitrary pick.
    """
    by_artist: dict[str, int] = {}
    for song in songs_for_album:
        artist = str(song.get("artist", "")).strip()
        if artist:
            by_artist[artist] = by_artist.get(artist, 0) + 1

    artists = list(by_artist)
    components = {a: _artist_components(a) for a in artists}
    parent = {a: a for a in artists}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: str, y: str) -> None:
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[rx] = ry

    for i in range(len(artists)):
        for j in range(i + 1, len(artists)):
            a, b = artists[i], artists[j]
            if _same_artist_family(components[a], components[b]):
                union(a, b)

    families: dict[str, list[str]] = {}
    for a in artists:
        families.setdefault(find(a), []).append(a)

    total = sum(by_artist.values())
    best_root, best_count = None, -1
    for root, members in families.items():
        count = sum(by_artist[m] for m in members)
        if count > best_count:
            best_root, best_count = root, count

    if total == 0 or best_count * 2 <= total:
        return "Various Artists", True

    members = families[best_root]
    canonical = max(members, key=lambda m: (by_artist[m], -len(components[m])))
    return canonical, False


def _split_by_year_and_tracks(album_songs: list[dict]) -> list[list[dict]]:
    """Partitions one raw `album` string's songs into one or more groups.

    A song only starts a new group when it overlaps neither released-year (within 1
    year) nor track-number (within 1 track, and only once a group already has 2+ known
    tracks) against every existing group. The 2+-tracks gate on the track check matters:
    without it, two unrelated songs that happen to share a coincidental track number
    (e.g. both tagged track 1, or both track 3) would count as "overlapping" and block
    a split even when their years are decades apart — exactly the reused-generic-title
    case (a "Crash" from 1986 vs. an unrelated "Crash" from 1996) this function exists
    to catch per US-05 AC2. Once a group is an established multi-track album, track
    adjacency alone still lets it absorb a track whose year is a genuine outlier
    (e.g. a reissue-dated bonus track), which is the ordinary-sparse-metadata case this
    stays conservative about.
    """
    groups: list[dict] = []
    for song in album_songs:
        year = parse_year(song.get("released"))
        track = parse_track(song.get("track"))
        match = None
        for group in groups:
            year_overlaps = (
                year is None
                or not group["years"]
                or any(abs(year - y) <= 1 for y in group["years"])
            )
            track_overlaps = (
                track is None
                or not group["tracks"]
                or (
                    len(group["tracks"]) >= 2
                    and min(group["tracks"]) - 1 <= track <= max(group["tracks"]) + 1
                )
            )
            if year_overlaps or track_overlaps:
                match = group
                break
        if match is None:
            match = {"songs": [], "years": set(), "tracks": set()}
            groups.append(match)
        match["songs"].append(song)
        if year is not None:
            match["years"].add(year)
        if track is not None:
            match["tracks"].add(track)
    return [group["songs"] for group in groups]


def _build_row(artist: str, album: str, songs_group: list[dict], is_various_artists: bool) -> dict:
    tracks = sorted(
        songs_group,
        key=lambda s: (parse_track(s.get("track")) is None, parse_track(s.get("track")) or 0),
    )
    years = [y for y in (parse_year(s.get("released")) for s in songs_group) if y is not None]
    return {
        "artist": artist,
        "album": album,
        "track_count": len(songs_group),
        "year_min": min(years) if years else None,
        "year_max": max(years) if years else None,
        "is_various_artists": is_various_artists,
        "tracks": [
            {
                "track": parse_track(s.get("track")),
                "title": s.get("title", ""),
                "artist": s.get("artist", ""),
                "duration": s.get("duration"),
                "released": s.get("released"),
                "tags": s.get("tags", ""),
                "link": s.get("link", ""),
            }
            for s in tracks
        ],
    }


def build_album_catalog(songs: list[dict]) -> list[dict]:
    by_album: dict[str, list[dict]] = {}
    for song in songs:
        album = str(song.get("album") or "").strip()
        if not album:
            continue
        by_album.setdefault(album, []).append(song)

    rows = []
    for album, album_songs in by_album.items():
        for group in _split_by_year_and_tracks(album_songs):
            artist, is_va = resolve_album_artist(group)
            rows.append(_build_row(artist, album, group, is_va))
    return rows
