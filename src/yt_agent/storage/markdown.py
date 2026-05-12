"""Markdown report rendering and local storage."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from yt_agent.ai.analyzer import StructuredReportContent
from yt_agent.core.models import JobStatus
from yt_agent.storage.files import slugify_filename


@dataclass(frozen=True)
class ReportMetadata:
    """Non-AI metadata rendered into the report header."""

    source_url: str
    raw_transcript: str
    processed_date: date | None = None
    channel: str | None = None
    status: JobStatus | str = JobStatus.COMPLETED


REPORT_SECTIONS = (
    ("executive_summary", "1. Executive Summary"),
    ("core_thesis", "2. Core Thesis"),
    ("detailed_breakdown", "3. Detailed Section-by-Section Breakdown"),
    ("key_ideas_and_claims", "4. Key Ideas and Claims"),
    ("tools_methods_frameworks", "5. Tools, Methods, Frameworks, or Processes Mentioned"),
    ("practical_applications", "6. Practical Applications"),
    ("implementation_plan", "7. Step-by-Step Implementation Plan"),
    ("exercises_or_action_items", "8. Exercises or Action Items"),
    ("analogies_and_mental_models", "9. Analogies and Mental Models"),
    ("real_world_examples_and_scenarios", "10. Real-World Examples and Scenarios"),
    ("critical_analysis", "11. Critical Analysis"),
    ("open_questions", "12. Open Questions"),
    ("best_quotes", "13. Best Quotes or Important Lines"),
    ("search_tags", "14. Search Tags"),
)


def render_markdown_report(
    content: StructuredReportContent,
    *,
    metadata: ReportMetadata,
) -> str:
    """Render structured analysis and metadata into the required Markdown report."""

    processed_date = metadata.processed_date or date.today()
    title = _report_title(content)
    status = metadata.status.value if isinstance(metadata.status, JobStatus) else metadata.status
    tags = ", ".join(content.tags)

    lines = [
        f"# {title}",
        "",
        f"URL: {metadata.source_url}",
        f"Video ID: {content.video_id}",
        f"Channel: {metadata.channel or ''}",
        f"Processed Date: {processed_date.isoformat()}",
        f"Model Used: {content.model}",
        f"Transcript Source: {content.transcript_source}",
        f"Tags: {tags}",
        f"Status: {status}",
    ]

    for key, heading in REPORT_SECTIONS:
        lines.extend(["", f"## {heading}", "", content.sections.get(key, "").strip()])

    lines.append("")
    return "\n".join(lines)


def save_markdown_report(
    *,
    reports_dir: Path,
    content: StructuredReportContent,
    metadata: ReportMetadata,
) -> Path:
    """Persist a rendered Markdown report under the configured reports directory."""

    path = build_report_path(
        reports_dir=reports_dir,
        video_id=content.video_id,
        video_title=_report_title(content),
        processed_date=metadata.processed_date,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_markdown_report(content, metadata=metadata), encoding="utf-8")
    return path


def build_report_path(
    *,
    reports_dir: Path,
    video_id: str,
    video_title: str | None = None,
    processed_date: date | None = None,
) -> Path:
    """Build the deterministic Markdown report output path for a video."""

    output_date = processed_date or date.today()
    title_part = slugify_filename(video_title) if video_title else video_id
    filename = f"{output_date.isoformat()}__{title_part}__{video_id}.md"
    return reports_dir / output_date.strftime("%Y-%m") / filename


def _report_title(content: StructuredReportContent) -> str:
    return content.title or content.video_id
