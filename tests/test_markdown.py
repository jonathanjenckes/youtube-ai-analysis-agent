from __future__ import annotations

from datetime import date

from yt_agent.ai.analyzer import StructuredReportContent
from yt_agent.ai.prompts import REPORT_SECTION_KEYS
from yt_agent.core.jobs import create_job, get_job, update_job_status
from yt_agent.core.models import JobStatus
from yt_agent.storage.db import connect, initialize_database
from yt_agent.storage.markdown import (
    ReportMetadata,
    build_report_path,
    render_markdown_report,
    save_markdown_report,
)


def make_report_content() -> StructuredReportContent:
    return StructuredReportContent(
        video_id="dQw4w9WgXcQ",
        model="unit-test-model",
        prompt_version="unit-test-prompt",
        transcript_source="captions",
        transcript_language_code="en",
        title="Useful Video: Part 1",
        tags=["research", "systems"],
        sections={key: f"{key} content" for key in REPORT_SECTION_KEYS},
        chunk_analyses=[],
    )


def make_metadata() -> ReportMetadata:
    return ReportMetadata(
        source_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        raw_transcript="First useful idea.\nSecond useful idea.",
        processed_date=date(2026, 5, 5),
        channel="Useful Channel",
        status=JobStatus.COMPLETED,
    )


def test_render_markdown_report_uses_required_structure() -> None:
    markdown = render_markdown_report(make_report_content(), metadata=make_metadata())

    assert markdown.startswith("# Useful Video: Part 1\n\nURL: https://www.youtube.com/watch")
    assert "Video ID: dQw4w9WgXcQ" in markdown
    assert "Channel: Useful Channel" in markdown
    assert "Processed Date: 2026-05-05" in markdown
    assert "Model Used: unit-test-model" in markdown
    assert "Transcript Source: captions" in markdown
    assert "Tags: research, systems" in markdown
    assert "Status: completed" in markdown
    assert "## 1. Executive Summary\n\nexecutive_summary content" in markdown
    assert "## 3. Detailed Section-by-Section Breakdown" in markdown
    assert "## 10. Real-World Examples and Scenarios" in markdown
    assert "## 14. Search Tags\n\nsearch_tags content" in markdown
    assert "## 15. Raw Transcript" not in markdown
    assert "First useful idea.\nSecond useful idea." not in markdown


def test_build_report_path_uses_month_folder_and_deterministic_filename(tmp_path) -> None:
    path = build_report_path(
        reports_dir=tmp_path / "reports",
        video_id="dQw4w9WgXcQ",
        video_title="Useful Video: Part 1",
        processed_date=date(2026, 5, 5),
    )

    assert path == (
        tmp_path
        / "reports"
        / "2026-05"
        / "2026-05-05__useful-video-part-1__dQw4w9WgXcQ.md"
    )


def test_save_markdown_report_persists_file_and_job_report_path(tmp_path) -> None:
    db_path = tmp_path / "jobs" / "app.sqlite3"
    initialize_database(db_path)

    report_path = save_markdown_report(
        reports_dir=tmp_path / "reports",
        content=make_report_content(),
        metadata=make_metadata(),
    )

    with connect(db_path) as connection:
        job = create_job(
            connection,
            video_id="dQw4w9WgXcQ",
            source_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        )
        updated = update_job_status(
            connection,
            job.id,
            JobStatus.COMPLETED,
            report_path=report_path,
        )
        loaded = get_job(connection, job.id)

    assert report_path.exists()
    report_text = report_path.read_text(encoding="utf-8")
    assert "## 14. Search Tags" in report_text
    assert "## 15. Raw Transcript" not in report_text
    assert updated.report_path == report_path
    assert loaded is not None
    assert loaded.report_path == report_path
