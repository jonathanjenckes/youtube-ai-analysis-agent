"""iOS Shortcut ingest routes."""

from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

from yt_agent.core.jobs import create_job
from yt_agent.core.models import Job, JobStatus
from yt_agent.core.security import SecurityValidationError, require_matching_token
from yt_agent.core.url_parser import YouTubeURLParseError, parse_youtube_url
from yt_agent.storage.db import connect

router = APIRouter(prefix="/ingest", tags=["ingest"])


class ShortcutIngestRequest(BaseModel):
    """Payload sent by the iOS Shortcut."""

    url: str = Field(..., min_length=1)


class JobResponse(BaseModel):
    """Serializable job metadata returned by ingest endpoints."""

    id: int
    video_id: str
    source_url: str
    status: JobStatus
    report_path: str | None
    transcript_path: str | None
    error_message: str | None
    created_at: str
    updated_at: str


@router.post("/shortcut", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def ingest_shortcut(
    payload: ShortcutIngestRequest,
    request: Request,
    x_app_secret: str | None = Header(default=None),
) -> JobResponse:
    """Validate a Shortcut request and enqueue a YouTube analysis job."""

    settings = request.app.state.settings
    try:
        require_matching_token(x_app_secret, settings.app_secret_token)
        video_ref = parse_youtube_url(payload.url)
    except SecurityValidationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except YouTubeURLParseError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    with connect(settings.sqlite_path) as connection:
        job = create_job(
            connection,
            video_id=video_ref.video_id,
            source_url=video_ref.normalized_url,
        )

    return job_to_response(job)


def job_to_response(job: Job) -> JobResponse:
    """Convert a domain job to an API response."""

    return JobResponse(
        id=job.id,
        video_id=job.video_id,
        source_url=job.source_url,
        status=job.status,
        report_path=str(job.report_path) if job.report_path else None,
        transcript_path=str(job.transcript_path) if job.transcript_path else None,
        error_message=job.error_message,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )
