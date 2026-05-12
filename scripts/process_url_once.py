"""Process one YouTube URL from the command line."""

from __future__ import annotations

import argparse

from yt_agent.config import get_settings
from yt_agent.core.jobs import create_job
from yt_agent.core.url_parser import YouTubeURLParseError, parse_youtube_url
from yt_agent.storage.db import connect, initialize_database
from yt_agent.workers.processor import process_job


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Process one YouTube URL now.")
    parser.add_argument("url", help="YouTube video URL to process")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    settings = get_settings()
    initialize_database(settings.sqlite_path)

    try:
        video_ref = parse_youtube_url(args.url)
    except YouTubeURLParseError as exc:
        parser.error(str(exc))

    with connect(settings.sqlite_path) as connection:
        job = create_job(
            connection,
            video_id=video_ref.video_id,
            source_url=video_ref.normalized_url,
        )

    print(f"Created queued job {job.id} for {job.source_url}", flush=True)
    try:
        result = process_job(job.id, settings=settings)
    except Exception as exc:
        parser.exit(status=1, message=f"Processing failed: {exc}\n")

    print(f"Completed job {result.job.id}")
    print(f"Transcript: {result.job.transcript_path}")
    print(f"Report: {result.job.report_path}")


if __name__ == "__main__":
    main()
