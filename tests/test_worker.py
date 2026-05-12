from __future__ import annotations

from datetime import date

import pytest

from yt_agent.ai.analyzer import StructuredReportContent
from yt_agent.ai.prompts import REPORT_SECTION_KEYS
from yt_agent.config import Settings
from yt_agent.core.jobs import create_job, get_job
from yt_agent.core.models import JobStatus
from yt_agent.storage.db import connect, initialize_database
from yt_agent.transcripts.chunker import TranscriptChunk
from yt_agent.transcripts.extractor import TranscriptExtractionResult
from yt_agent.workers.processor import JobProcessingError, process_job
from yt_agent.youtube.metadata import YouTubeVideoMetadata


class FakeAnalysisClient:
    model = "unit-test-model"

    def complete(self, *, system_prompt: str, user_prompt: str) -> str:
        raise AssertionError("Worker tests should not call Anthropic.")


def make_settings(tmp_path) -> Settings:
    return Settings(
        _env_file=None,
        app_env="test",
        app_secret_token="unit-test-secret",
        data_dir=tmp_path,
        anthropic_api_key="",
        anthropic_model="unit-test-model",
    )


def make_transcript(video_id: str) -> TranscriptExtractionResult:
    text = "First useful idea.\nSecond useful idea."
    return TranscriptExtractionResult(
        video_id=video_id,
        language="English",
        language_code="en",
        source="captions",
        segments=[],
        text=text,
        chunks=[
            TranscriptChunk(
                index=1,
                total=1,
                text=text,
                start_char=0,
                end_char=len(text),
            )
        ],
    )


def make_report(video_id: str) -> StructuredReportContent:
    return StructuredReportContent(
        video_id=video_id,
        model="unit-test-model",
        prompt_version="unit-test-prompt",
        transcript_source="captions",
        transcript_language_code="en",
        title="Useful Video",
        tags=["research", "systems"],
        sections={key: f"{key} content" for key in REPORT_SECTION_KEYS},
        chunk_analyses=[],
    )


def create_queued_job(settings: Settings):
    initialize_database(settings.sqlite_path)
    with connect(settings.sqlite_path) as connection:
        return create_job(
            connection,
            video_id="dQw4w9WgXcQ",
            source_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        )


def test_process_job_completes_lifecycle_with_mocked_external_steps(tmp_path) -> None:
    settings = make_settings(tmp_path)
    job = create_queued_job(settings)
    extractor_calls = []
    analyzer_calls = []

    def fake_extract_transcript(video_id: str, *, max_chars_per_chunk: int, max_chunks: int):
        extractor_calls.append((video_id, max_chars_per_chunk, max_chunks))
        return make_transcript(video_id)

    def fake_analyze_transcript(transcript, *, client):
        analyzer_calls.append((transcript, client))
        return make_report(transcript.video_id)

    def fake_fetch_metadata(source_url: str):
        assert source_url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        return YouTubeVideoMetadata(title="Official Video Title", channel="Official Channel")

    result = process_job(
        job.id,
        settings=settings,
        transcript_extractor=fake_extract_transcript,
        transcript_analyzer=fake_analyze_transcript,
        metadata_fetcher=fake_fetch_metadata,
        analysis_client=FakeAnalysisClient(),
        processed_date=date(2026, 5, 5),
    )

    with connect(settings.sqlite_path) as connection:
        loaded = get_job(connection, job.id)

    assert result.job.status == JobStatus.COMPLETED
    assert loaded is not None
    assert loaded.status == JobStatus.COMPLETED
    assert loaded.error_message is None
    assert loaded.transcript_path is not None
    assert loaded.report_path is not None
    assert loaded.transcript_path.exists()
    assert loaded.report_path.exists()
    assert "official-video-title" in loaded.transcript_path.name
    assert "official-video-title" in loaded.report_path.name
    assert loaded.transcript_path.read_text(encoding="utf-8") == (
        "First useful idea.\nSecond useful idea."
    )
    report_text = loaded.report_path.read_text(encoding="utf-8")
    assert "# Official Video Title" in report_text
    assert "Channel: Official Channel" in report_text
    assert extractor_calls == [("dQw4w9WgXcQ", 18_000, 20)]
    assert analyzer_calls[0][0].video_id == "dQw4w9WgXcQ"
    assert isinstance(analyzer_calls[0][1], FakeAnalysisClient)


def test_process_job_falls_back_when_metadata_fetch_fails(tmp_path) -> None:
    settings = make_settings(tmp_path)
    job = create_queued_job(settings)

    def fake_extract_transcript(video_id: str, *, max_chars_per_chunk: int, max_chunks: int):
        return make_transcript(video_id)

    def fake_analyze_transcript(transcript, *, client):
        return make_report(transcript.video_id)

    def failing_fetch_metadata(source_url: str):
        raise RuntimeError("metadata unavailable")

    result = process_job(
        job.id,
        settings=settings,
        transcript_extractor=fake_extract_transcript,
        transcript_analyzer=fake_analyze_transcript,
        metadata_fetcher=failing_fetch_metadata,
        analysis_client=FakeAnalysisClient(),
        processed_date=date(2026, 5, 5),
    )

    assert result.job.status == JobStatus.COMPLETED
    assert result.job.transcript_path is not None
    assert result.job.report_path is not None
    assert "useful-video__dQw4w9WgXcQ" in result.job.transcript_path.name
    assert "useful-video__dQw4w9WgXcQ" in result.job.report_path.name


def test_process_job_marks_failed_when_extraction_raises(tmp_path) -> None:
    settings = make_settings(tmp_path)
    job = create_queued_job(settings)

    def failing_extract_transcript(video_id: str, *, max_chars_per_chunk: int, max_chunks: int):
        raise RuntimeError(f"No transcript for {video_id}.")

    with pytest.raises(RuntimeError, match="No transcript"):
        process_job(
            job.id,
            settings=settings,
            transcript_extractor=failing_extract_transcript,
            analysis_client=FakeAnalysisClient(),
        )

    with connect(settings.sqlite_path) as connection:
        loaded = get_job(connection, job.id)

    assert loaded is not None
    assert loaded.status == JobStatus.FAILED
    assert loaded.error_message == "No transcript for dQw4w9WgXcQ."
    assert loaded.report_path is None
    assert loaded.transcript_path is None


def test_process_job_rejects_missing_job(tmp_path) -> None:
    settings = make_settings(tmp_path)
    initialize_database(settings.sqlite_path)

    with pytest.raises(JobProcessingError, match="does not exist"):
        process_job(999, settings=settings, analysis_client=FakeAnalysisClient())
