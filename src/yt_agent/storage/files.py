"""Local file storage helpers."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

SAFE_FILENAME_RE = re.compile(r"[^a-z0-9]+")


def save_transcript_text(
    *,
    transcripts_dir: Path,
    video_id: str,
    text: str,
    video_title: str | None = None,
    processed_date: date | None = None,
) -> Path:
    """Persist transcript text under the configured transcripts directory."""

    path = build_transcript_path(
        transcripts_dir=transcripts_dir,
        video_id=video_id,
        video_title=video_title,
        processed_date=processed_date,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def build_transcript_path(
    *,
    transcripts_dir: Path,
    video_id: str,
    video_title: str | None = None,
    processed_date: date | None = None,
) -> Path:
    """Build the transcript output path for a video."""

    output_date = processed_date or date.today()
    title_part = slugify_filename(video_title) if video_title else video_id
    filename = f"{output_date.isoformat()}__{title_part}__{video_id}.txt"
    return transcripts_dir / output_date.strftime("%Y-%m") / filename


def slugify_filename(value: str) -> str:
    """Convert a title into a stable, filesystem-safe filename segment."""

    slug = SAFE_FILENAME_RE.sub("-", value.lower()).strip("-")
    return slug[:80].strip("-") or "untitled"
