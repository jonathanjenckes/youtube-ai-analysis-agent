"""YouTube URL parsing helpers."""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

from yt_agent.core.models import YouTubeVideoRef

VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
    "www.youtu.be",
}


class YouTubeURLParseError(ValueError):
    """Raised when a URL is not a supported YouTube video URL."""


def parse_youtube_url(url: str) -> YouTubeVideoRef:
    """Parse and normalize a supported YouTube video URL."""

    candidate = url.strip()
    if not candidate:
        raise YouTubeURLParseError("YouTube URL is required.")

    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"}:
        raise YouTubeURLParseError("YouTube URL must use http or https.")

    host = (parsed.hostname or "").lower()
    if host not in YOUTUBE_HOSTS:
        raise YouTubeURLParseError("URL host is not a supported YouTube host.")

    video_id = _extract_video_id(host, parsed.path, parse_qs(parsed.query))
    if not is_valid_video_id(video_id):
        raise YouTubeURLParseError("URL does not contain a valid YouTube video ID.")

    return YouTubeVideoRef(
        video_id=video_id,
        normalized_url=f"https://www.youtube.com/watch?v={video_id}",
    )


def is_valid_video_id(video_id: str | None) -> bool:
    """Return whether a string has the shape of a YouTube video ID."""

    return bool(video_id and VIDEO_ID_RE.fullmatch(video_id))


def _extract_video_id(host: str, path: str, query: dict[str, list[str]]) -> str | None:
    clean_path = path.strip("/")
    path_parts = [part for part in clean_path.split("/") if part]

    if host in {"youtu.be", "www.youtu.be"}:
        return path_parts[0] if path_parts else None

    if path_parts[:1] == ["watch"]:
        return query.get("v", [None])[0]

    if len(path_parts) >= 2 and path_parts[0] in {"embed", "shorts", "live"}:
        return path_parts[1]

    return None
