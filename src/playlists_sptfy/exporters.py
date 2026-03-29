from __future__ import annotations

import csv
import json
import tempfile
from datetime import date
from pathlib import Path


def _atomic_write(path: Path, write_fn) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="",
        delete=False,
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    ) as tmp:
        tmp_path = Path(tmp.name)
    try:
        write_fn(tmp_path)
        tmp_path.replace(path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


def write_json_file(data, file):
    output_path = Path(file)

    def _write(tmp_path: Path) -> None:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    _atomic_write(output_path, _write)


def write_songs_csv(songs: list[dict], output_path: Path) -> None:
    fieldnames = ["link", "artist", "title", "released", "duration", "album", "track", "tags"]

    def _write(tmp_path: Path) -> None:
        with open(tmp_path, "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            for song in songs:
                writer.writerow({field: song.get(field, "") for field in fieldnames})

    _atomic_write(output_path, _write)


def write_song_links_txt(songs: list[dict], output_path: Path) -> None:
    links = []
    for song in songs:
        link = str(song.get("link", "")).strip()
        if link:
            links.append(link)
    content = "\n".join(links)
    # Match import-file style: one URL per line with trailing newline when non-empty.
    if content:
        content += "\n"

    def _write(tmp_path: Path) -> None:
        with open(tmp_path, "w", encoding="utf-8") as file:
            file.write(content)

    _atomic_write(output_path, _write)


def write_duplicates_markdown(dups: dict, path) -> None:
    total_groups = len(dups)
    total_songs = sum(len(entries) for entries in dups.values())
    lines = [
        "# Possible Duplicate Songs",
        "",
        f"Generated: {date.today()}  ",
        f"**{total_groups} duplicate groups** across **{total_songs} songs**",
        "",
    ]
    for title_key, entries in sorted(dups.items()):
        lines.append(f"## {title_key} ({len(entries)} matches)")
        lines.append("")
        lines.append("| Artist | Title | Album |")
        lines.append("|--------|-------|-------|")
        for song in entries:
            artist = str(song.get("artist", "")).replace("|", "\\|")
            title = str(song.get("title", "")).replace("|", "\\|")
            album = str(song.get("album", "")).replace("|", "\\|")
            lines.append(f"| {artist} | {title} | {album} |")
        lines.append("")
    output_path = Path(path)

    def _write(tmp_path: Path) -> None:
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    _atomic_write(output_path, _write)
