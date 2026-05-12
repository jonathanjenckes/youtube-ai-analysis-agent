from __future__ import annotations

import httpx
import pytest

from yt_agent.youtube import metadata
from yt_agent.youtube.metadata import YouTubeMetadataError, fetch_youtube_metadata


class FakeResponse:
    def __init__(self, payload, *, status_error: Exception | None = None) -> None:
        self.payload = payload
        self.status_error = status_error

    def raise_for_status(self) -> None:
        if self.status_error:
            raise self.status_error

    def json(self):
        return self.payload


def test_fetch_youtube_metadata_uses_oembed_payload(monkeypatch) -> None:
    calls = []

    def fake_get(url, *, params, timeout):
        calls.append((url, params, timeout))
        return FakeResponse(
            {
                "title": "Official Video Title",
                "author_name": "Official Channel",
            }
        )

    monkeypatch.setattr(metadata.httpx, "get", fake_get)

    result = fetch_youtube_metadata("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    assert result.title == "Official Video Title"
    assert result.channel == "Official Channel"
    assert calls == [
        (
            "https://www.youtube.com/oembed",
            {
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "format": "json",
            },
            10,
        )
    ]


def test_fetch_youtube_metadata_wraps_http_errors(monkeypatch) -> None:
    def fake_get(url, *, params, timeout):
        request = httpx.Request("GET", url)
        response = httpx.Response(404, request=request)
        return FakeResponse(
            {},
            status_error=httpx.HTTPStatusError(
                "not found",
                request=request,
                response=response,
            ),
        )

    monkeypatch.setattr(metadata.httpx, "get", fake_get)

    with pytest.raises(YouTubeMetadataError, match="Could not fetch"):
        fetch_youtube_metadata("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
