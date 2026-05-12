# Project Overview

This project builds a personal YouTube research assistant.

The system accepts a YouTube URL from either an iOS Shortcut or a Telegram bot. The backend validates the URL, extracts the video ID, retrieves available transcripts, cleans and chunks transcript text, sends transcript chunks to the Anthropic Claude Messages API, generates a detailed Markdown report, stores job metadata in SQLite, and notifies the user through Telegram when processing completes.

The production application must be a normal Python backend with explicit API calls, job status tracking, and predictable local file output. It should not depend on an interactive coding assistant session to perform analysis.

## Required Report Structure

Every processed video should generate a Markdown file with these sections:

```markdown
# Video Title

URL:
Video ID:
Channel:
Processed Date:
Model Used:
Transcript Source:
Tags:
Status:

## 1. Executive Summary

## 2. Core Thesis

## 3. Detailed Section-by-Section Breakdown

## 4. Key Ideas and Claims

## 5. Tools, Methods, Frameworks, or Processes Mentioned

## 6. Practical Applications

## 7. Step-by-Step Implementation Plan

## 8. Exercises or Action Items

## 9. Analogies and Mental Models

## 10. Real-World Examples and Scenarios

## 11. Critical Analysis

## 12. Open Questions

## 13. Best Quotes or Important Lines

## 14. Search Tags
```

## Storage Layout

```text
data/
  reports/
    YYYY-MM/
      YYYY-MM-DD__video-title__video-id.md
  transcripts/
    YYYY-MM/
      YYYY-MM-DD__video-title__video-id.txt
  jobs/
    app.sqlite3
  logs/
    app.log
```

## Technical Stack

- Python 3.11+
- FastAPI
- Uvicorn
- SQLite
- httpx
- youtube-transcript-api
- Anthropic Claude Messages API
- Telegram Bot API
- pydantic-settings
- pytest
- ruff

## Core Rules

- Keep the Anthropic model configurable through environment variables.
- Do not hard-code model names inside analysis logic.
- Use official documentation when implementing external APIs.
- Do not add optional storage integrations before the MVP is complete.
- Do not download audio or add speech-to-text in the MVP.
- Keep build sessions controlled and update continuity docs after each session.
- At the end of every build session, write a short copy-paste prompt in `NEXT_SESSION_PROMPT.md` telling the next Codex session exactly where to start, which files to load first, what to build next, what not to build yet, and what verification to run.

## Build Sessions

Session 0 creates the repository foundation. Later sessions implement config, database, API routes, transcript extraction, AI analysis, report generation, worker processing, Telegram integration, and iOS Shortcut documentation.
