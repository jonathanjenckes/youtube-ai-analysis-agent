import sqlite3

from yt_agent.core.jobs import create_job, get_job, update_job_status
from yt_agent.core.models import JobStatus
from yt_agent.storage.db import connect, initialize_database


def test_initialize_database_creates_jobs_table(tmp_path) -> None:
    db_path = tmp_path / "jobs" / "app.sqlite3"

    initialize_database(db_path)

    with sqlite3.connect(db_path) as connection:
        table = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'jobs'"
        ).fetchone()

    assert table == ("jobs",)


def test_job_helpers_create_load_and_update_job(tmp_path) -> None:
    db_path = tmp_path / "jobs" / "app.sqlite3"
    initialize_database(db_path)

    with connect(db_path) as connection:
        job = create_job(
            connection,
            video_id="dQw4w9WgXcQ",
            source_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        )
        loaded = get_job(connection, job.id)
        updated = update_job_status(
            connection,
            job.id,
            JobStatus.COMPLETED,
            report_path=tmp_path / "report.md",
            transcript_path=tmp_path / "transcript.txt",
        )

    assert loaded == job
    assert job.status == JobStatus.QUEUED
    assert updated.status == JobStatus.COMPLETED
    assert updated.report_path == tmp_path / "report.md"
    assert updated.transcript_path == tmp_path / "transcript.txt"
