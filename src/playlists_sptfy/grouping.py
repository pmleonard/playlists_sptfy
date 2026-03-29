from __future__ import annotations

import json
from pathlib import Path


def load_grouped_songs(file_path: Path) -> list[list[str]]:
    if not file_path.exists():
        return []
    with open(file_path, encoding="utf-8") as file:
        groups = json.load(file)

    normalized_groups: list[list[str]] = []
    for item in groups:
        # Accept only object entries with a songs list and drop empty/blank links.
        songs = item.get("songs", []) if isinstance(item, dict) else []
        if isinstance(songs, list):
            links = [str(link).strip() for link in songs if str(link).strip()]
            if links:
                normalized_groups.append(links)
    return normalized_groups


def group_randomized_songs(songs: list[dict], grouped_songs: list[list[str]]) -> list[dict]:
    if not songs or not grouped_songs:
        return songs

    link_to_song = {}
    for song in songs:
        link = str(song.get("link", "")).strip()
        if link and link not in link_to_song:
            link_to_song[link] = song

    link_to_group = {}
    for group_id, group_links in enumerate(grouped_songs):
        for order, link in enumerate(group_links):
            # If a link appears in multiple groups, keep its first declared group.
            if link not in link_to_group:
                link_to_group[link] = (group_id, order)

    output = []
    emitted_groups = set()
    emitted_links = set()

    for song in songs:
        link = str(song.get("link", "")).strip()
        if not link or link in emitted_links:
            continue

        group_info = link_to_group.get(link)
        if group_info is None:
            output.append(song)
            emitted_links.add(link)
            continue

        group_id = group_info[0]
        if group_id in emitted_groups:
            continue

        # Emit the full group together to preserve adjacency in output order.
        for group_link in grouped_songs[group_id]:
            grouped_song = link_to_song.get(group_link)
            if grouped_song is not None and group_link not in emitted_links:
                output.append(grouped_song)
                emitted_links.add(group_link)

        emitted_groups.add(group_id)

    return output
