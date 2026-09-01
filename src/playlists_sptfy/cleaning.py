from __future__ import annotations

import re

SPOTIFY_SUFFIX = " | Spotify"

# Spotify album-page og:title values look like "<Album> - Album by <Artist>"
# (also seen: Compilation / Single / EP). This is scraper noise, not part of
# the album's actual name, and its presence is inconsistent across scrapes of
# the same album — causing the same underlying album to fragment into
# multiple raw variant strings in the Albums review tab.
_ALBUM_TYPE_SUFFIX = re.compile(
    r"\s*-\s*(?:album|compilation|single|ep)\s+by\s+.+$",
    re.IGNORECASE,
)


def strip_spotify_suffix(value: str) -> str:
    """Remove the literal " | Spotify" suffix some scraped page titles carry."""
    return value.replace(SPOTIFY_SUFFIX, "")


def strip_pipe_chars(value: str) -> str:
    """Remove any remaining "|" characters, collapsing the whitespace left behind."""
    if "|" not in value:
        return value
    return " ".join(value.replace("|", " ").split())


def strip_album_type_suffix(value: str) -> str:
    """Remove a scraped "- Album by <Artist>"-style suffix from an album title."""
    return _ALBUM_TYPE_SUFFIX.sub("", value)


def clean_scraped_text(value: str) -> str:
    """Apply the pipe-related cleanups, in order, to a scraped title/album value."""
    return strip_pipe_chars(strip_spotify_suffix(value))


def clean_scraped_album_text(value: str) -> str:
    """Apply all scraper-noise cleanups, in order, to a scraped album value."""
    return strip_pipe_chars(strip_album_type_suffix(strip_spotify_suffix(value)))
