from __future__ import annotations

SPOTIFY_SUFFIX = " | Spotify"


def strip_spotify_suffix(value: str) -> str:
    """Remove the literal " | Spotify" suffix some scraped page titles carry."""
    return value.replace(SPOTIFY_SUFFIX, "")


def strip_pipe_chars(value: str) -> str:
    """Remove any remaining "|" characters, collapsing the whitespace left behind."""
    if "|" not in value:
        return value
    return " ".join(value.replace("|", " ").split())


def clean_scraped_text(value: str) -> str:
    """Apply both pipe-related cleanups, in order, to a scraped title/album value."""
    return strip_pipe_chars(strip_spotify_suffix(value))
