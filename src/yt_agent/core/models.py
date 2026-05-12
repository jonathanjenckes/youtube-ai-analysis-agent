"""Core domain models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class JobStatus(StrEnum):
    """Known lifecycle states for video analysis jobs."""

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class YouTubeVideoRef:
    """A validated YouTube video reference."""

    video_id: str
    normalized_url: str


@dataclass(frozen=True)
class Job:
    """A database-backed video processing job."""

    id: int
    video_id: str
    source_url: str
    status: JobStatus
    report_path: Path | None
    transcript_path: Path | None
    error_message: str | None
    created_at: str
    updated_at: str
