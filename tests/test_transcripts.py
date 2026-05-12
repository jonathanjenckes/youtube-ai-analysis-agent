from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pytest
from requests import ConnectionError
from youtube_transcript_api._errors import TranscriptsDisabled

from yt_agent.storage.files import build_transcript_path, save_transcript_text
from yt_agent.transcripts.chunker import TranscriptChunkingError, chunk_transcript_text
from yt_agent.transcripts.cleaner import clean_transcript_text
from yt_agent.transcripts.extractor import TranscriptExtractionError, extract_transcript


@dataclass(frozen=True)
class FakeSnippet:
    text: str
    start: float
    duration: float


class FakeFetchedTranscript(list):
    language = "English"
    language_code = "en"
    is_generated = False


class FakeTranscript:
    language = "English"
    language_code = "en"
    is_generated = False

    def __init__(self, snippets):
        self.snippets = snippets

    def fetch(self, preserve_formatting: bool = False):
        assert preserve_formatting is False
        fetched = FakeFetchedTranscript(self.snippets)
        fetched.language = self.language
        fetched.language_code = self.language_code
        fetched.is_generated = self.is_generated
        return fetched


class FakeTranscriptList:
    def __init__(self, transcript):
        self.transcript = transcript

    def find_manually_created_transcript(self, languages):
        assert languages == ("en",)
        return self.transcript

    def find_generated_transcript(self, languages):
        raise AssertionError("manual transcript should be preferred")

    def find_transcript(self, languages):
        return self.transcript

    def __iter__(self):
        yield self.transcript


class FakeTranscriptApi:
    def __init__(self, transcript_list):
        self.transcript_list = transcript_list

    def list(self, video_id):
        assert video_id == "dQw4w9WgXcQ"
        return self.transcript_list


class FailingTranscriptApi:
    def list(self, video_id):
        raise TranscriptsDisabled(video_id)


class NetworkFailingTranscriptApi:
    def list(self, video_id):
        raise ConnectionError("DNS failed")


class FlakyTranscriptApi:
    def __init__(self, transcript_list):
        self.transcript_list = transcript_list
        self.calls = 0

    def list(self, video_id):
        self.calls += 1
        if self.calls == 1:
            raise ConnectionError("temporary failure")
        return self.transcript_list


def test_extract_transcript_success_with_mocked_api() -> None:
    transcript = FakeTranscript(
        [
            FakeSnippet("Hello&nbsp;world.", 0.0, 1.2),
            FakeSnippet("[Music]", 1.2, 1.0),
            FakeSnippet("This is a useful line.", 2.2, 2.5),
        ]
    )

    result = extract_transcript(
        "dQw4w9WgXcQ",
        max_chars_per_chunk=80,
        max_chunks=5,
        transcript_api=FakeTranscriptApi(FakeTranscriptList(transcript)),
    )

    assert result.video_id == "dQw4w9WgXcQ"
    assert result.language_code == "en"
    assert result.source == "captions"
    assert result.text == "Hello world.\nThis is a useful line."
    assert [chunk.text for chunk in result.chunks] == ["Hello world.\nThis is a useful line."]
    assert len(result.segments) == 3


def test_extract_transcript_retries_transient_failures() -> None:
    transcript = FakeTranscript([FakeSnippet("Recovered line.", 0.0, 1.0)])
    api = FlakyTranscriptApi(FakeTranscriptList(transcript))

    result = extract_transcript(
        "dQw4w9WgXcQ",
        max_chars_per_chunk=80,
        max_chunks=5,
        transcript_api=api,
        retry_delay_seconds=0,
    )

    assert api.calls == 2
    assert result.text == "Recovered line."


def test_extract_transcript_wraps_no_transcript_errors() -> None:
    with pytest.raises(TranscriptExtractionError, match="No usable transcript"):
        extract_transcript(
            "dQw4w9WgXcQ",
            max_chars_per_chunk=80,
            max_chunks=5,
            transcript_api=FailingTranscriptApi(),
        )


def test_extract_transcript_wraps_network_errors() -> None:
    with pytest.raises(TranscriptExtractionError, match="No usable transcript"):
        extract_transcript(
            "dQw4w9WgXcQ",
            max_chars_per_chunk=80,
            max_chunks=5,
            transcript_api=NetworkFailingTranscriptApi(),
        )


def test_clean_transcript_text_normalizes_noise_and_spacing() -> None:
    raw = "  Hello&nbsp;&nbsp;there \r\n[Music]\n\n\nＡ fullwidth line\twith space.  "

    assert clean_transcript_text(raw) == "Hello there\n\nA fullwidth line with space."


def test_chunk_transcript_text_respects_configured_limits() -> None:
    text = "First sentence. Second sentence. Third sentence."

    chunks = chunk_transcript_text(text, max_chars_per_chunk=24, max_chunks=3)

    assert [chunk.text for chunk in chunks] == [
        "First sentence.",
        "Second sentence.",
        "Third sentence.",
    ]
    assert [chunk.index for chunk in chunks] == [1, 2, 3]
    assert all(chunk.total == 3 for chunk in chunks)


def test_chunk_transcript_text_raises_when_chunk_limit_is_exceeded() -> None:
    with pytest.raises(TranscriptChunkingError):
        chunk_transcript_text(
            "First sentence. Second sentence. Third sentence.",
            max_chars_per_chunk=24,
            max_chunks=2,
        )


def test_transcript_file_persistence(tmp_path) -> None:
    transcript_path = save_transcript_text(
        transcripts_dir=tmp_path / "transcripts",
        video_id="dQw4w9WgXcQ",
        video_title="Useful Video: Part 1",
        text="Clean transcript text.",
        processed_date=date(2026, 5, 5),
    )

    assert transcript_path == (
        tmp_path
        / "transcripts"
        / "2026-05"
        / "2026-05-05__useful-video-part-1__dQw4w9WgXcQ.txt"
    )
    assert transcript_path.read_text(encoding="utf-8") == "Clean transcript text."


def test_build_transcript_path_uses_video_id_when_title_is_unknown(tmp_path) -> None:
    path = build_transcript_path(
        transcripts_dir=tmp_path / "transcripts",
        video_id="dQw4w9WgXcQ",
        processed_date=date(2026, 5, 5),
    )

    assert path.name == "2026-05-05__dQw4w9WgXcQ__dQw4w9WgXcQ.txt"
