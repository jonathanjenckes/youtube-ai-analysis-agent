import pytest

from yt_agent.core.url_parser import YouTubeURLParseError, parse_youtube_url


@pytest.mark.parametrize(
    ("url", "video_id"),
    [
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://youtu.be/dQw4w9WgXcQ?si=abc123", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://youtube.com/shorts/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://music.youtube.com/watch?v=dQw4w9WgXcQ&list=123", "dQw4w9WgXcQ"),
    ],
)
def test_parse_youtube_url_supported_formats(url: str, video_id: str) -> None:
    parsed = parse_youtube_url(url)

    assert parsed.video_id == video_id
    assert parsed.normalized_url == f"https://www.youtube.com/watch?v={video_id}"


@pytest.mark.parametrize(
    "url",
    [
        "",
        "not-a-url",
        "ftp://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://example.com/watch?v=dQw4w9WgXcQ",
        "https://www.youtube.com/watch?v=too-short",
        "https://www.youtube.com/channel/dQw4w9WgXcQ",
    ],
)
def test_parse_youtube_url_rejects_invalid_urls(url: str) -> None:
    with pytest.raises(YouTubeURLParseError):
        parse_youtube_url(url)
