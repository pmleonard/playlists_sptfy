from __future__ import annotations


def normalize_tags(tags) -> str:
    parts = [part.strip().lower() for part in str(tags).split(",")]
    clean = [part for part in parts if part]
    return ", ".join(sorted(set(clean)))


def tags_to_set(tags) -> set[str]:
    normalized = normalize_tags(tags)
    if not normalized:
        return set()
    return set(normalized.split(", "))


def filter_values_to_set(values) -> set[str]:
    if values is None:
        return set()
    # Accept either comma-delimited strings or iterable values from settings.
    if isinstance(values, str):
        return tags_to_set(values)
    return tags_to_set(", ".join(str(value) for value in values))


def merge_tags(tags, new_tags):
    return normalize_tags(f"{tags}, {new_tags}")


def tag_filter_songs(songs: list[dict], tags_filter: dict | None = None) -> list[dict]:
    if not tags_filter:
        return songs

    include_tags = filter_values_to_set(tags_filter.get("include"))
    exclude_tags = filter_values_to_set(tags_filter.get("exclude"))
    filtered_songs = []

    for song in songs:
        song_tags = tags_to_set(song.get("tags", ""))

        # Include logic: song must match at least one include tag (if provided).
        if include_tags and song_tags.isdisjoint(include_tags):
            continue

        # Exclude logic: any overlap with exclude tags removes the song.
        if exclude_tags and not song_tags.isdisjoint(exclude_tags):
            continue

        filtered_songs.append(song)

    return filtered_songs
