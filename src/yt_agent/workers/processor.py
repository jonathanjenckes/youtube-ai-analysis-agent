"""Synchronous job processing pipeline."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import date

from yt_agent.ai.analyzer import AnalysisClient, StructuredReportContent, analyze_transcript
from yt_agent.ai.anthropic_client import AnthropicAnalysisClient, AnthropicConfig
from yt_agent.config import Settings
from yt_agent.core.jobs import get_job, update_job_status
from yt_agent.core.models import Job, JobStatus
from yt_agent.storage.db import connect
from yt_agent.storage.files import save_transcript_text
from yt_agent.storage.markdown import ReportMetadata, save_markdown_report
from yt_agent.transcripts.extractor import TranscriptExtractionResult, extract_transcript
from yt_agent.youtube.metadata import (
    YouTubeVideoMetadata,
    fetch_youtube_metadata,
)

TranscriptExtractor = Callable[..., TranscriptExtractionResult]
TranscriptAnalyzer = Callable[..., StructuredReportContent]
MetadataFetcher = Callable[[str], YouTubeVideoMetadata]
logger = logging.getLogger(__name__)


class JobProcessingError(RuntimeError):
    """Raised when a job cannot be processed."""


@dataclass(frozen=True)
class ProcessedJobResult:
    """Final output for one processed job."""

    job: Job
    transcript: TranscriptExtractionResult
    report: StructuredReportContent


def process_job(
    job_id: int,
    *,
    settings: Settings,
    transcript_extractor: TranscriptExtractor = extract_transcript,
    transcript_analyzer: TranscriptAnalyzer = analyze_transcript,
    metadata_fetcher: MetadataFetcher = fetch_youtube_metadata,
    analysis_client: AnalysisClient | None = None,
    processed_date: date | None = None,
) -> ProcessedJobResult:
    """Process one queued job through transcript extraction, analysis, and report output."""

    output_date = processed_date or date.today()
    with connect(settings.sqlite_path) as connection:
        job = get_job(connection, job_id)
        if job is None:
            raise JobProcessingError(f"Job {job_id} does not exist.")
        if job.status != JobStatus.QUEUED:
            raise JobProcessingError(f"Job {job_id} is {job.status}, not queued.")
        update_job_status(connection, job.id, JobStatus.PROCESSING)

    try:
        metadata = _fetch_metadata_safely(metadata_fetcher, job.source_url)
        video_title = metadata.title

        transcript = transcript_extractor(
            job.video_id,
            max_chars_per_chunk=settings.max_transcript_chars_per_chunk,
            max_chunks=settings.max_chunks_per_video,
        )

        client = analysis_client or _build_analysis_client(settings)
        report = transcript_analyzer(transcript, client=client)
        if video_title:
            report = replace(report, title=video_title)
        output_title = report.title or job.video_id
        transcript_path = save_transcript_text(
            transcripts_dir=settings.transcripts_dir,
            video_id=job.video_id,
            text=transcript.text,
            video_title=output_title,
            processed_date=output_date,
        )
        report_path = save_markdown_report(
            reports_dir=settings.reports_dir,
            content=report,
            metadata=ReportMetadata(
                source_url=job.source_url,
                raw_transcript=transcript.text,
                processed_date=output_date,
                channel=metadata.channel,
                status=JobStatus.COMPLETED,
            ),
        )
    except Exception as exc:
        with connect(settings.sqlite_path) as connection:
            update_job_status(
                connection,
                job.id,
                JobStatus.FAILED,
                error_message=str(exc),
            )
        raise

    with connect(settings.sqlite_path) as connection:
        completed = update_job_status(
            connection,
            job.id,
            JobStatus.COMPLETED,
            report_path=report_path,
            transcript_path=transcript_path,
        )

    return ProcessedJobResult(job=completed, transcript=transcript, report=report)


def _build_analysis_client(settings: Settings) -> AnthropicAnalysisClient:
    return AnthropicAnalysisClient(
        AnthropicConfig(
            api_key=settings.anthropic_api_key,
            model=settings.anthropic_model,
            max_tokens=settings.anthropic_max_tokens,
        )
    )


def _fetch_metadata_safely(
    metadata_fetcher: MetadataFetcher,
    source_url: str,
) -> YouTubeVideoMetadata:
    try:
        return metadata_fetcher(source_url)
    except Exception:
        logger.exception(
            "Falling back to video ID labels after metadata fetch failed for %s",
            source_url,
        )
        return YouTubeVideoMetadata()
