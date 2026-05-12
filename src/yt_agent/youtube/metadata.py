"""Fetch public YouTube video metadata."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


class YouTubeMetadataError(RuntimeError):
    """Raised when public YouTube metadata cannot be fetched."""


@dataclass(frozen=True)
class YouTubeVideoMetadata:
    """Public metadata used for report labeling."""

    title: str | None = None
    channel: str | None = None


def fetch_youtube_metadata(source_url: str) -> YouTubeVideoMetadata:
    """Fetch public title/channel metadata for a YouTube URL using oEmbed."""

    try:
        response = httpx.get(
            "https://www.youtube.com/oembed",
            params={"url": source_url, "format": "json"},
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise YouTubeMetadataError("Could not fetch YouTube video metadata.") from exc

    if not isinstance(payload, dict):
        raise YouTubeMetadataError("YouTube metadata response was not an object.")

    return YouTubeVideoMetadata(
        title=_coerce_optional_text(payload.get("title")),
        channel=_coerce_optional_text(payload.get("author_name")),
    )


def _coerce_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
