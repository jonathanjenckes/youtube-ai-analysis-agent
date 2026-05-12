"""YouTube transcript extraction."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from time import sleep
from typing import Any

from requests import RequestException
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    CouldNotRetrieveTranscript,
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
    YouTubeTranscriptApiException,
)

from yt_agent.transcripts.chunker import TranscriptChunk, chunk_transcript_text
from yt_agent.transcripts.cleaner import clean_transcript_text


class TranscriptExtractionError(RuntimeError):
    """Raised when a transcript cannot be extracted for a video."""


@dataclass(frozen=True)
class TranscriptSegment:
    """One transcript line from YouTube captions."""

    text: str
    start: float
    duration: float


@dataclass(frozen=True)
class TranscriptExtractionResult:
    """Clean transcript extraction output."""

    video_id: str
    language: str
    language_code: str
    source: str
    segments: list[TranscriptSegment]
    text: str
    chunks: list[TranscriptChunk]


def extract_transcript(
    video_id: str,
    *,
    max_chars_per_chunk: int,
    max_chunks: int,
    languages: Iterable[str] = ("en",),
    transcript_api: Any | None = None,
    retry_attempts: int = 3,
    retry_delay_seconds: float = 0.5,
) -> TranscriptExtractionResult:
    """Fetch, clean, and chunk the best available transcript for a YouTube video."""

    requested_languages = tuple(languages) or ("en",)
    api = transcript_api or YouTubeTranscriptApi()

    transcript, fetched = _fetch_transcript_with_retries(
        api=api,
        video_id=video_id,
        languages=requested_languages,
        retry_attempts=retry_attempts,
        retry_delay_seconds=retry_delay_seconds,
    )

    segments = [_coerce_segment(snippet) for snippet in fetched]
    raw_text = "\n".join(segment.text for segment in segments)
    cleaned_text = clean_transcript_text(raw_text)
    chunks = chunk_transcript_text(
        cleaned_text,
        max_chars_per_chunk=max_chars_per_chunk,
        max_chunks=max_chunks,
    )

    return TranscriptExtractionResult(
        video_id=video_id,
        language=getattr(fetched, "language", getattr(transcript, "language", "")),
        language_code=getattr(fetched, "language_code", getattr(transcript, "language_code", "")),
        source="auto-generated"
        if getattr(fetched, "is_generated", getattr(transcript, "is_generated", False))
        else "captions",
        segments=segments,
        text=cleaned_text,
        chunks=chunks,
    )


def _fetch_transcript_with_retries(
    *,
    api: Any,
    video_id: str,
    languages: tuple[str, ...],
    retry_attempts: int,
    retry_delay_seconds: float,
) -> tuple[Any, Any]:
    attempts = max(1, retry_attempts)
    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            transcript_list = api.list(video_id)
            transcript = _select_transcript(transcript_list, languages)
            return transcript, transcript.fetch(preserve_formatting=False)
        except (
            NoTranscriptFound,
            TranscriptsDisabled,
            VideoUnavailable,
            CouldNotRetrieveTranscript,
            YouTubeTranscriptApiException,
            RequestException,
        ) as exc:
            last_error = exc
            if attempt < attempts and retry_delay_seconds > 0:
                sleep(retry_delay_seconds)

    raise TranscriptExtractionError(
        f"No usable transcript found for video {video_id}."
    ) from last_error


def _select_transcript(transcript_list: Any, languages: tuple[str, ...]) -> Any:
    for finder_name in ("find_manually_created_transcript", "find_generated_transcript"):
        finder = getattr(transcript_list, finder_name, None)
        if finder is None:
            continue
        try:
            return finder(languages)
        except NoTranscriptFound:
            continue

    try:
        return transcript_list.find_transcript(languages)
    except NoTranscriptFound:
        pass

    for transcript in transcript_list:
        return transcript

    raise TranscriptExtractionError("Transcript list was empty.")


def _coerce_segment(snippet: Any) -> TranscriptSegment:
    if isinstance(snippet, dict):
        return TranscriptSegment(
            text=str(snippet.get("text", "")),
            start=float(snippet.get("start", 0.0)),
            duration=float(snippet.get("duration", 0.0)),
        )

    return TranscriptSegment(
        text=str(getattr(snippet, "text", "")),
        start=float(getattr(snippet, "start", 0.0)),
        duration=float(getattr(snippet, "duration", 0.0)),
    )
