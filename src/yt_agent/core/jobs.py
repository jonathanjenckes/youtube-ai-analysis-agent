"""Job database helpers."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from yt_agent.core.models import Job, JobStatus


def create_job(connection: sqlite3.Connection, *, video_id: str, source_url: str) -> Job:
    """Insert a queued job and return it."""

    cursor = connection.execute(
        """
        INSERT INTO jobs (video_id, source_url, status)
        VALUES (?, ?, ?)
        """,
        (video_id, source_url, JobStatus.QUEUED.value),
    )
    connection.commit()
    job = get_job(connection, cursor.lastrowid)
    if job is None:
        raise RuntimeError("Created job could not be loaded.")
    return job


def get_job(connection: sqlite3.Connection, job_id: int) -> Job | None:
    """Load one job by ID."""

    row = connection.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    return _row_to_job(row) if row else None


def update_job_status(
    connection: sqlite3.Connection,
    job_id: int,
    status: JobStatus,
    *,
    report_path: str | Path | None = None,
    transcript_path: str | Path | None = None,
    error_message: str | None = None,
) -> Job:
    """Update a job lifecycle status and optional output metadata."""

    connection.execute(
        """
        UPDATE jobs
        SET status = ?,
            report_path = COALESCE(?, report_path),
            transcript_path = COALESCE(?, transcript_path),
            error_message = ?,
            updated_at = datetime('now')
        WHERE id = ?
        """,
        (
            status.value,
            str(report_path) if report_path is not None else None,
            str(transcript_path) if transcript_path is not None else None,
            error_message,
            job_id,
        ),
    )
    connection.commit()
    job = get_job(connection, job_id)
    if job is None:
        raise ValueError(f"Job {job_id} does not exist.")
    return job


def _row_to_job(row: sqlite3.Row) -> Job:
    return Job(
        id=row["id"],
        video_id=row["video_id"],
        source_url=row["source_url"],
        status=JobStatus(row["status"]),
        report_path=Path(row["report_path"]) if row["report_path"] else None,
        transcript_path=Path(row["transcript_path"]) if row["transcript_path"] else None,
        error_message=row["error_message"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
