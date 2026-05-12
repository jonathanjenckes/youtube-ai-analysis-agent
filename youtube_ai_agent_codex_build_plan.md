# YouTube AI Analysis Agent, Codex Build Plan

Version: 1.0  
Date: 2026-05-05  
Owner: Jonathan Jenckes  
Primary Goal: Build a personal automation system where a YouTube URL sent from an iPhone Shortcut or Telegram bot is processed into a structured AI analysis report, stored for later reading, and returned to the user with a completion notification.

## 1. Project Summary

This project builds a personal YouTube research assistant.

The system should accept a YouTube URL from either:

1. An iOS Shortcut using the iPhone share sheet.
2. A Telegram bot where the user messages a YouTube URL.

The backend should then:

1. Validate and normalize the YouTube URL.
2. Extract the YouTube video ID.
3. Pull the available transcript when possible.
4. Clean and normalize the transcript.
5. Chunk long transcripts safely.
6. Send the transcript chunks through the Anthropic Claude API using a lower-cost model selected by environment variable.
7. Generate a detailed markdown analysis report.
8. Store the report locally in a predictable folder structure.
9. Save job metadata in SQLite.
10. Notify the user in Telegram when the job is complete.

The build should prioritize reliability, simple local operation, clear logs, and continuation across multiple Codex sessions without context drift.

## 2. Key Architecture Decision

Codex or Claude Code can be used as developer tools to build the repo, but the production application should call the Anthropic Claude API directly for video analysis.

Do not design the production app around an interactive coding assistant session. The running app should be a normal Python backend with explicit API calls, job status tracking, and predictable file output.

## 3. Source References For Implementation

Use official documentation whenever possible.

1. Anthropic Claude API documentation: https://platform.claude.com/docs/en/home
2. Anthropic Messages API reference: https://platform.claude.com/docs/en/api/messages
3. Anthropic API overview: https://platform.claude.com/docs/en/api/overview
4. Telegram Bot API: https://core.telegram.org/bots/api
5. Telegram webhook guide: https://core.telegram.org/bots/webhooks
6. Apple Shortcuts API request guide: https://support.apple.com/guide/shortcuts/request-your-first-api-apd58d46713f/ios

## 4. Product Requirements

### 4.1 Required User Workflow

The user should be able to do either of the following:

Workflow A, iPhone Shortcut:

1. User opens YouTube on iPhone.
2. User taps Share.
3. User selects the custom Shortcut.
4. Shortcut sends the YouTube URL to the backend webhook.
5. Backend creates a processing job.
6. Backend replies to the Shortcut with a basic acknowledgement.
7. Backend processes the transcript and analysis.
8. Backend sends a Telegram notification with a short summary and report path or link.

Workflow B, Telegram:

1. User sends a YouTube URL to the Telegram bot.
2. Bot confirms receipt.
3. Backend creates a processing job.
4. Backend processes the transcript and analysis.
5. Bot sends completion notification with a short summary and report path or link.

### 4.2 Required Output

Every processed video should generate a markdown file with this structure:

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

## 10. Critical Analysis

## 11. Open Questions

## 12. Best Quotes or Important Lines

## 13. Search Tags

## 14. Raw Transcript
```

### 4.3 Required Storage

Default local storage:

```text
/data
  /reports
    /YYYY-MM
      YYYY-MM-DD__video-title__video-id.md
  /transcripts
    /YYYY-MM
      YYYY-MM-DD__video-title__video-id.txt
  /jobs
    app.sqlite3
  /logs
    app.log
```

Optional future storage:

1. Obsidian vault sync folder.
2. Google Drive folder.
3. Notion database.
4. Self-hosted web reader.

Do not add these optional storage integrations until the MVP is complete.

## 5. Technical Stack

### 5.1 Recommended MVP Stack

Language: Python 3.11 or newer  
Backend: FastAPI  
Server: Uvicorn  
Database: SQLite  
HTTP Client: httpx  
Transcript Extraction: youtube-transcript-api first, yt-dlp optional later  
AI API: Anthropic Claude Messages API  
Bot Interface: Telegram Bot API  
Config: pydantic-settings or python-dotenv  
Testing: pytest  
Formatting: ruff  
Storage Format: Markdown files plus SQLite metadata

### 5.2 Why This Stack

FastAPI gives a clean webhook server. SQLite avoids database complexity. Markdown keeps the output human-readable and easy to move into Obsidian. Telegram gives a simple personal chat interface. The Anthropic API keeps the AI model external so the local machine does not need to run a large open model.

## 6. Repo Structure

Codex should create this repo structure:

```text
youtube-ai-agent/
  README.md
  PROJECT_OVERVIEW.md
  CURRENT_STATE.md
  ROADMAP.md
  NEXT_SESSION_PROMPT.md
  DECISIONS.md
  .env.example
  .gitignore
  pyproject.toml
  requirements.txt
  /src
    /yt_agent
      __init__.py
      main.py
      config.py
      logging_config.py
      /api
        __init__.py
        routes_health.py
        routes_shortcut.py
        routes_telegram.py
      /core
        __init__.py
        jobs.py
        models.py
        security.py
        url_parser.py
      /transcripts
        __init__.py
        extractor.py
        cleaner.py
        chunker.py
      /ai
        __init__.py
        anthropic_client.py
        prompts.py
        analyzer.py
      /storage
        __init__.py
        db.py
        files.py
        markdown.py
      /telegram
        __init__.py
        bot.py
      /workers
        __init__.py
        processor.py
  /tests
    test_url_parser.py
    test_chunker.py
    test_markdown.py
    test_security.py
  /scripts
    init_db.py
    set_telegram_webhook.py
    process_url_once.py
  /data
    .gitkeep
```

## 7. Environment Variables

Codex should create `.env.example` with:

```bash
APP_ENV=development
APP_BASE_URL=https://example.com
APP_SECRET_TOKEN=change-me

ANTHROPIC_API_KEY=your_anthropic_api_key
ANTHROPIC_MODEL=claude-3-5-haiku-latest
ANTHROPIC_MAX_TOKENS=4000

TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_ALLOWED_CHAT_IDS=123456789
TELEGRAM_WEBHOOK_SECRET=change-me

DATA_DIR=./data
REPORTS_DIR=./data/reports
TRANSCRIPTS_DIR=./data/transcripts
SQLITE_PATH=./data/jobs/app.sqlite3
LOG_PATH=./data/logs/app.log

JOB_MODE=background
MAX_TRANSCRIPT_CHARS_PER_CHUNK=18000
MAX_CHUNKS_PER_VIDEO=20
```

Important: The model name must be configurable. Do not hard-code a model in the analysis code. Use the environment variable.

## 8. Database Schema

Use SQLite for job tracking.

### 8.1 jobs Table

Fields:

```text
id TEXT PRIMARY KEY
source TEXT NOT NULL
status TEXT NOT NULL
original_url TEXT NOT NULL
normalized_url TEXT
video_id TEXT
video_title TEXT
channel_name TEXT
telegram_chat_id TEXT
created_at TEXT NOT NULL
started_at TEXT
completed_at TEXT
failed_at TEXT
error_message TEXT
model_used TEXT
transcript_source TEXT
transcript_path TEXT
report_path TEXT
report_summary TEXT
```

Allowed statuses:

```text
queued
processing
completed
failed
needs_manual_review
```

Allowed sources:

```text
shortcut
telegram
manual_cli
```

### 8.2 Do Not Overbuild The Database

Do not add users, teams, billing, OAuth, or a complex document model in MVP. This is a personal automation tool.

## 9. API Design

### 9.1 Health Check

`GET /health`

Returns:

```json
{
  "status": "ok"
}
```

### 9.2 iOS Shortcut Ingest Endpoint

`POST /api/shortcut/ingest`

Required header:

```text
X-App-Secret: <APP_SECRET_TOKEN>
```

Request body:

```json
{
  "url": "https://www.youtube.com/watch?v=...",
  "source": "ios_shortcut"
}
```

Response body:

```json
{
  "accepted": true,
  "job_id": "...",
  "message": "Video accepted for processing."
}
```

### 9.3 Telegram Webhook Endpoint

`POST /api/telegram/webhook/{secret}`

The `{secret}` path component should match `TELEGRAM_WEBHOOK_SECRET`.

Expected behavior:

1. Receive Telegram update.
2. Extract sender chat ID.
3. Reject if chat ID is not in `TELEGRAM_ALLOWED_CHAT_IDS`.
4. Extract the first YouTube URL from the message text.
5. Create a job.
6. Reply to the user with a receipt message.
7. Process the job in the worker.
8. Notify the user when done.

### 9.4 Manual CLI Script

Codex should create:

```bash
python scripts/process_url_once.py "https://youtube.com/watch?v=..."
```

This allows debugging without Telegram or iOS Shortcut.

## 10. Processing Pipeline

### 10.1 Job Lifecycle

```text
receive URL
  -> validate URL
  -> create job with queued status
  -> start processing
  -> extract video metadata
  -> extract transcript
  -> clean transcript
  -> save raw transcript
  -> chunk transcript
  -> call Anthropic API on chunks
  -> merge analysis
  -> generate markdown report
  -> save report
  -> update job as completed
  -> notify user
```

### 10.2 Failure Handling

If transcript extraction fails:

1. Mark job as `needs_manual_review` or `failed`.
2. Save error message.
3. Notify user that no transcript could be extracted.
4. Do not silently fail.

If Anthropic API fails:

1. Retry up to 2 times with backoff.
2. If still failing, mark job as failed.
3. Preserve transcript if already extracted.
4. Notify user with failure reason.

If report writing fails:

1. Mark job as failed.
2. Log the full error.
3. Notify user.

## 11. Transcript Strategy

### 11.1 MVP Transcript Extraction

Use transcript extraction only from available YouTube captions or auto-generated subtitles.

MVP should not download video or audio.

Reason: The first build should focus on reliable ingestion, analysis, storage, and notification. Audio download and Whisper transcription can be added later as a controlled enhancement.

### 11.2 Future Transcript Fallback

Future enhancement:

1. Use yt-dlp to fetch subtitles if the first method fails.
2. Use local or API speech-to-text only when permitted and needed.
3. Mark transcript source clearly in metadata.

## 12. AI Analysis Strategy

### 12.1 Chunking

Long videos must be chunked before analysis.

Chunking rules:

1. Split transcript into chunks under `MAX_TRANSCRIPT_CHARS_PER_CHUNK`.
2. Preserve timestamp ranges when available.
3. Do not split in the middle of a sentence if avoidable.
4. Store chunk metadata internally.
5. Limit total chunks using `MAX_CHUNKS_PER_VIDEO`.
6. If the video exceeds max chunks, process the first chunks and mark the report as partial, or fail gracefully with a clear message.

### 12.2 Two-Pass Analysis

Use a two-pass analysis system.

Pass 1, chunk analysis:

Each transcript chunk should return structured JSON-like analysis containing:

```text
summary
main_points
examples
tools_or_frameworks
practical_steps
claims
questions
notable_lines
```

Pass 2, final synthesis:

The final synthesis should merge chunk outputs into the required markdown report sections.

### 12.3 Prompt Storage

All AI prompts should live in:

```text
src/yt_agent/ai/prompts.py
```

Prompts must be versioned by constant names.

Example:

```python
CHUNK_ANALYSIS_PROMPT_V1 = """..."""
FINAL_SYNTHESIS_PROMPT_V1 = """..."""
```

Do not bury important prompts inside random functions.

## 13. Telegram Behavior

### 13.1 Accepted URL Message

When a URL is received:

```text
Received. I am processing this video now.
Job ID: <job_id>
```

### 13.2 Completion Message

When complete:

```text
Video analysis complete.
Title: <title>
Report: <report_path>
Summary: <one-paragraph summary>
```

### 13.3 Failure Message

When failed:

```text
I could not complete this video analysis.
Reason: <short reason>
Job ID: <job_id>
```

## 14. iOS Shortcut Setup Requirements

The iOS Shortcut should:

1. Accept URLs from the share sheet.
2. Send a POST request to `/api/shortcut/ingest`.
3. Include JSON body with the URL.
4. Include `X-App-Secret` header.
5. Show the returned job ID to the user.

The repo should include a markdown guide:

```text
README.md section: iOS Shortcut Setup
```

## 15. Security Rules

### 15.1 Required Security Controls

1. iOS Shortcut endpoint must require `X-App-Secret`.
2. Telegram webhook must include a secret path.
3. Telegram must reject unauthorized chat IDs.
4. Secrets must never be committed.
5. `.env` must be in `.gitignore`.
6. Logs must not include API keys.
7. Reports must not include private environment variables.

### 15.2 No Public Multi-User System In MVP

Do not build user accounts, OAuth, billing, admin panels, or public sharing.

This is a personal automation tool.

## 16. Local Development Flow

### 16.1 Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### 16.2 Run Server

```bash
uvicorn yt_agent.main:app --reload --app-dir src
```

### 16.3 Run Tests

```bash
pytest
```

### 16.4 Process One URL Manually

```bash
python scripts/process_url_once.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

## 17. Roadmap By Build Session

This project should be built in controlled sessions. Each session must finish by updating:

1. `CURRENT_STATE.md`
2. `NEXT_SESSION_PROMPT.md`
3. `DECISIONS.md` if any major decision was made
4. Tests for newly added logic

Each new Codex session should load only the documents listed in the session prompt.

## 18. Session 0, Repo Foundation

Goal: Create the repo skeleton and the source-of-truth planning documents.

Tasks:

1. Create repo structure.
2. Create `README.md`.
3. Create `PROJECT_OVERVIEW.md` using this document.
4. Create `CURRENT_STATE.md`.
5. Create `ROADMAP.md`.
6. Create `DECISIONS.md`.
7. Create `NEXT_SESSION_PROMPT.md`.
8. Create `.env.example`.
9. Create `.gitignore`.
10. Create `pyproject.toml` and `requirements.txt`.
11. Add empty package files.

Acceptance Criteria:

1. Repo imports cleanly.
2. `pytest` runs, even if there are only placeholder tests.
3. `README.md` explains the project and local setup.
4. `CURRENT_STATE.md` accurately says Session 0 is complete.
5. `NEXT_SESSION_PROMPT.md` contains a prompt for Session 1.

Copy-Paste Prompt For Session 0:

```text
You are Codex working inside a new repo for the YouTube AI Analysis Agent. Build Session 0 only.

Read and follow PROJECT_OVERVIEW.md. If it does not exist yet, create it from the project plan I provide. Create the repo skeleton, README.md, CURRENT_STATE.md, ROADMAP.md, DECISIONS.md, NEXT_SESSION_PROMPT.md, .env.example, .gitignore, pyproject.toml, requirements.txt, package directories, and placeholder tests.

Do not implement the full app yet. Do not add optional storage integrations. Do not add audio transcription. Keep this session limited to repo foundation.

At the end, update CURRENT_STATE.md with what was created, update ROADMAP.md if needed, and write the exact copy-paste prompt for Session 1 into NEXT_SESSION_PROMPT.md.
```

## 19. Session 1, Core Config, Logging, Database, URL Parser

Goal: Build the core foundation that every later feature depends on.

Tasks:

1. Implement `config.py`.
2. Implement `logging_config.py`.
3. Implement SQLite initialization in `storage/db.py`.
4. Implement job model helpers in `core/jobs.py`.
5. Implement YouTube URL parsing in `core/url_parser.py`.
6. Implement security helper for app secret validation.
7. Add tests for URL parsing, config loading, and security.
8. Create `scripts/init_db.py`.

Acceptance Criteria:

1. App can load config from `.env`.
2. Database can initialize cleanly.
3. YouTube URLs are normalized.
4. Invalid URLs are rejected.
5. Tests pass.
6. `NEXT_SESSION_PROMPT.md` contains Session 2 prompt.

Copy-Paste Prompt For Session 1:

```text
You are Codex continuing the YouTube AI Analysis Agent. Build Session 1 only.

Load only these files first: PROJECT_OVERVIEW.md, CURRENT_STATE.md, ROADMAP.md, DECISIONS.md, NEXT_SESSION_PROMPT.md, .env.example, and the files you need under src/yt_agent.

Goal: implement core config, logging, SQLite initialization, job helpers, URL parsing, and security helpers. Do not build Telegram yet. Do not call the Anthropic API yet. Do not add transcript extraction yet.

Add tests for YouTube URL parsing, config loading, database initialization, and security validation. Run tests. At the end, update CURRENT_STATE.md, DECISIONS.md if needed, and write the exact copy-paste prompt for Session 2 into NEXT_SESSION_PROMPT.md.
```

## 20. Session 2, FastAPI App And Ingest Endpoints

Goal: Build the web server and URL ingestion endpoints.

Tasks:

1. Implement FastAPI app in `main.py`.
2. Add `/health` route.
3. Add `/api/shortcut/ingest` route.
4. Add Telegram webhook route skeleton.
5. Create jobs from incoming URLs.
6. Return job IDs.
7. Do not process the job yet.
8. Add tests for endpoints.

Acceptance Criteria:

1. Server starts locally.
2. `/health` returns OK.
3. Shortcut endpoint accepts valid YouTube URLs with correct secret.
4. Shortcut endpoint rejects bad secret.
5. Shortcut endpoint rejects invalid URLs.
6. Job record is created in SQLite.
7. Tests pass.
8. `NEXT_SESSION_PROMPT.md` contains Session 3 prompt.

Copy-Paste Prompt For Session 2:

```text
You are Codex continuing the YouTube AI Analysis Agent. Build Session 2 only.

Load only these files first: PROJECT_OVERVIEW.md, CURRENT_STATE.md, ROADMAP.md, DECISIONS.md, NEXT_SESSION_PROMPT.md, src/yt_agent/main.py, src/yt_agent/config.py, src/yt_agent/storage/db.py, src/yt_agent/core/jobs.py, src/yt_agent/core/url_parser.py, and tests related to the API.

Goal: implement the FastAPI app, health route, shortcut ingest endpoint, and a Telegram webhook route skeleton. The endpoint should validate secrets, parse YouTube URLs, create queued jobs in SQLite, and return job IDs. Do not implement transcript extraction or AI processing in this session.

Add endpoint tests. Run tests. At the end, update CURRENT_STATE.md, DECISIONS.md if needed, and write the exact copy-paste prompt for Session 3 into NEXT_SESSION_PROMPT.md.
```

## 21. Session 3, Transcript Extraction And Cleaning

Goal: Extract and clean transcripts from YouTube URLs.

Tasks:

1. Implement `transcripts/extractor.py`.
2. Implement `transcripts/cleaner.py`.
3. Implement `transcripts/chunker.py`.
4. Save raw transcript to `/data/transcripts/YYYY-MM`.
5. Add tests using fixture transcript data.
6. Create manual script path to extract transcript without AI.

Acceptance Criteria:

1. Transcript extraction returns text and metadata when available.
2. Cleaning removes excessive whitespace and obvious transcript artifacts.
3. Chunker respects configured max chunk size.
4. Transcript gets saved to disk.
5. Failures are explicit and logged.
6. Tests pass.
7. `NEXT_SESSION_PROMPT.md` contains Session 4 prompt.

Copy-Paste Prompt For Session 3:

```text
You are Codex continuing the YouTube AI Analysis Agent. Build Session 3 only.

Load only these files first: PROJECT_OVERVIEW.md, CURRENT_STATE.md, ROADMAP.md, DECISIONS.md, NEXT_SESSION_PROMPT.md, src/yt_agent/config.py, src/yt_agent/core/url_parser.py, src/yt_agent/transcripts, src/yt_agent/storage/files.py, and relevant tests.

Goal: implement transcript extraction, transcript cleaning, transcript chunking, and transcript file storage. Use available YouTube captions or auto-generated subtitles only. Do not download audio. Do not add Whisper. Do not call the Anthropic API yet.

Add tests using local fixtures and avoid relying on live YouTube calls inside unit tests. Run tests. At the end, update CURRENT_STATE.md, DECISIONS.md if needed, and write the exact copy-paste prompt for Session 4 into NEXT_SESSION_PROMPT.md.
```

## 22. Session 4, Anthropic Client And AI Analysis Pipeline

Goal: Build the AI analysis engine.

Tasks:

1. Implement `ai/anthropic_client.py`.
2. Implement `ai/prompts.py`.
3. Implement `ai/analyzer.py`.
4. Create chunk analysis function.
5. Create final synthesis function.
6. Add retry logic.
7. Add mock tests for Anthropic API calls.

Acceptance Criteria:

1. Model is read from environment variable.
2. API key is read from environment variable.
3. Chunk analysis can be tested with mocked responses.
4. Final synthesis can be tested with mocked responses.
5. No real API calls happen in unit tests.
6. Tests pass.
7. `NEXT_SESSION_PROMPT.md` contains Session 5 prompt.

Copy-Paste Prompt For Session 4:

```text
You are Codex continuing the YouTube AI Analysis Agent. Build Session 4 only.

Load only these files first: PROJECT_OVERVIEW.md, CURRENT_STATE.md, ROADMAP.md, DECISIONS.md, NEXT_SESSION_PROMPT.md, src/yt_agent/config.py, src/yt_agent/ai, src/yt_agent/transcripts/chunker.py, and relevant tests.

Goal: implement the Anthropic API client, prompt constants, chunk analysis, final synthesis, and retry-safe analysis pipeline. Use the Anthropic model from environment variables. Do not hard-code a model. Do not build Telegram notification yet. Do not implement background workers yet.

Add mock-based tests. Do not make live Anthropic calls in tests. Run tests. At the end, update CURRENT_STATE.md, DECISIONS.md if needed, and write the exact copy-paste prompt for Session 5 into NEXT_SESSION_PROMPT.md.
```

## 23. Session 5, Markdown Report Generation And Storage

Goal: Generate and store final reports.

Tasks:

1. Implement `storage/markdown.py`.
2. Implement safe file naming.
3. Implement report path creation by month.
4. Save final markdown report.
5. Update job records with report path and summary.
6. Add tests for markdown output.

Acceptance Criteria:

1. Markdown file has required sections.
2. File name is safe and predictable.
3. Report path is saved in SQLite.
4. Raw transcript path is saved in SQLite.
5. Tests pass.
6. `NEXT_SESSION_PROMPT.md` contains Session 6 prompt.

Copy-Paste Prompt For Session 5:

```text
You are Codex continuing the YouTube AI Analysis Agent. Build Session 5 only.

Load only these files first: PROJECT_OVERVIEW.md, CURRENT_STATE.md, ROADMAP.md, DECISIONS.md, NEXT_SESSION_PROMPT.md, src/yt_agent/storage, src/yt_agent/core/jobs.py, src/yt_agent/ai/analyzer.py, and relevant tests.

Goal: implement markdown report generation, safe file naming, report storage by month, and job updates with transcript path, report path, model used, and summary. Do not build Telegram notification yet. Do not build background workers yet.

Add tests for markdown generation and file storage. Run tests. At the end, update CURRENT_STATE.md, DECISIONS.md if needed, and write the exact copy-paste prompt for Session 6 into NEXT_SESSION_PROMPT.md.
```

## 24. Session 6, Worker Pipeline

Goal: Wire the full processing pipeline together.

Tasks:

1. Implement `workers/processor.py`.
2. Add `process_job(job_id)`.
3. Make the manual CLI process a full video from URL to report.
4. Update job status through lifecycle.
5. Handle failures clearly.
6. Add integration-style tests with mocked transcript and mocked AI.

Acceptance Criteria:

1. Manual CLI can process one URL into a report when dependencies are mocked or live config is present.
2. Job status transitions are correct.
3. Failed jobs preserve useful error messages.
4. Tests pass.
5. `NEXT_SESSION_PROMPT.md` contains Session 7 prompt.

Copy-Paste Prompt For Session 6:

```text
You are Codex continuing the YouTube AI Analysis Agent. Build Session 6 only.

Load only these files first: PROJECT_OVERVIEW.md, CURRENT_STATE.md, ROADMAP.md, DECISIONS.md, NEXT_SESSION_PROMPT.md, src/yt_agent/workers, src/yt_agent/core/jobs.py, src/yt_agent/transcripts, src/yt_agent/ai, src/yt_agent/storage, scripts/process_url_once.py, and relevant tests.

Goal: implement the full job processor that takes a queued job through transcript extraction, transcript cleaning, chunking, Anthropic analysis, markdown generation, file storage, and final job status update. Implement the manual CLI for full processing.

Do not build Telegram notification yet. Do not add a queue service like Redis. Use a simple background task or direct processor call for now. Add integration-style tests with mocked transcript and mocked AI. Run tests. At the end, update CURRENT_STATE.md, DECISIONS.md if needed, and write the exact copy-paste prompt for Session 7 into NEXT_SESSION_PROMPT.md.
```

## 25. Session 7, Telegram Bot Integration

Goal: Accept URLs through Telegram and notify on completion.

Tasks:

1. Implement Telegram message parsing.
2. Implement allowed chat ID validation.
3. Implement `telegram/bot.py` send message helper.
4. Connect Telegram webhook to job creation.
5. Send receipt message.
6. Send completion or failure message.
7. Create `scripts/set_telegram_webhook.py`.
8. Add tests with fixture Telegram updates.

Acceptance Criteria:

1. Telegram webhook rejects unauthorized chat IDs.
2. Telegram webhook extracts YouTube URL from message.
3. Telegram webhook creates job.
4. Telegram bot sends receipt message.
5. Job completion sends message to original chat ID.
6. Tests pass.
7. `NEXT_SESSION_PROMPT.md` contains Session 8 prompt.

Copy-Paste Prompt For Session 7:

```text
You are Codex continuing the YouTube AI Analysis Agent. Build Session 7 only.

Load only these files first: PROJECT_OVERVIEW.md, CURRENT_STATE.md, ROADMAP.md, DECISIONS.md, NEXT_SESSION_PROMPT.md, src/yt_agent/api/routes_telegram.py, src/yt_agent/telegram, src/yt_agent/core/jobs.py, src/yt_agent/workers/processor.py, src/yt_agent/config.py, and relevant tests.

Goal: implement Telegram webhook ingestion, allowed chat ID validation, YouTube URL extraction from Telegram messages, Telegram send-message helper, receipt messages, completion messages, failure messages, and set-webhook script.

Do not add WhatsApp. Do not add user accounts. Do not add Redis unless absolutely necessary. Add tests with fixture Telegram update payloads and mocked Telegram API calls. Run tests. At the end, update CURRENT_STATE.md, DECISIONS.md if needed, and write the exact copy-paste prompt for Session 8 into NEXT_SESSION_PROMPT.md.
```

## 26. Session 8, iOS Shortcut Guide And End-To-End Local Test

Goal: Make the system usable from the phone.

Tasks:

1. Finalize Shortcut endpoint behavior.
2. Add README instructions for iOS Shortcut setup.
3. Add sample Shortcut JSON body.
4. Add curl examples.
5. Add local tunneling notes without requiring a specific vendor.
6. Run end-to-end test path.
7. Fix rough edges.

Acceptance Criteria:

1. README clearly explains iOS Shortcut setup.
2. README clearly explains Telegram setup.
3. README includes local run command.
4. README includes production deployment notes.
5. End-to-end path is documented.
6. Tests pass.
7. `NEXT_SESSION_PROMPT.md` contains Session 9 prompt.

Copy-Paste Prompt For Session 8:

```text
You are Codex continuing the YouTube AI Analysis Agent. Build Session 8 only.

Load only these files first: PROJECT_OVERVIEW.md, CURRENT_STATE.md, ROADMAP.md, DECISIONS.md, NEXT_SESSION_PROMPT.md, README.md, src/yt_agent/api/routes_shortcut.py, src/yt_agent/api/routes_telegram.py, and scripts.

Goal: finish the iOS Shortcut documentation, Telegram setup documentation, curl examples, local testing steps, and end-to-end runbook. Tighten any rough edges found in the ingest flow. Do not add major new features.

Run tests. At the end, update CURRENT_STATE.md, DECISIONS.md if needed, and write the exact copy-paste prompt for Session 9 into NEXT_SESSION_PROMPT.md.
```

## 27. Session 9, Hardening And MVP Release

Goal: Make the MVP stable and ready for daily personal use.

Tasks:

1. Add better error messages.
2. Add retry handling where missing.
3. Add structured logging.
4. Add job status inspection command.
5. Add report index command.
6. Validate `.env.example`.
7. Validate no secrets are committed.
8. Run full test suite.
9. Update README for MVP release.

Acceptance Criteria:

1. MVP can process URLs from Telegram.
2. MVP can process URLs from iOS Shortcut.
3. Completed reports are stored in markdown.
4. Failed jobs explain what failed.
5. README contains setup and usage instructions.
6. Tests pass.
7. `CURRENT_STATE.md` says MVP complete.
8. `NEXT_SESSION_PROMPT.md` contains optional enhancement prompt.

Copy-Paste Prompt For Session 9:

```text
You are Codex continuing the YouTube AI Analysis Agent. Build Session 9 only.

Load only these files first: PROJECT_OVERVIEW.md, CURRENT_STATE.md, ROADMAP.md, DECISIONS.md, NEXT_SESSION_PROMPT.md, README.md, .env.example, src/yt_agent, scripts, and tests.

Goal: harden the MVP. Improve error messages, retry handling, structured logging, job status inspection, report indexing, setup validation, and README accuracy. Do not add optional storage integrations. Do not add audio transcription. Do not add WhatsApp.

Run the full test suite. Verify no secrets are committed. Update CURRENT_STATE.md to indicate whether MVP is complete. Update DECISIONS.md if needed. Write an optional enhancement prompt into NEXT_SESSION_PROMPT.md.
```

## 28. Optional Enhancement Sessions After MVP

Only start these after MVP is stable.

### 28.1 Audio Transcription Fallback

Add yt-dlp subtitle fallback first. Add audio transcription only if needed and legally acceptable.

### 28.2 Obsidian Integration

Allow `REPORTS_DIR` to point to an Obsidian vault folder.

### 28.3 Web Reader

Create a local web interface to search and read reports.

### 28.4 Tagging And Knowledge Base Index

Add automatic tagging and SQLite full-text search.

### 28.5 WhatsApp Integration

Only add WhatsApp after Telegram works reliably.

## 29. Anti-Drift Rules For Every Codex Session

Every session must follow these rules:

1. Load `PROJECT_OVERVIEW.md` first.
2. Load `CURRENT_STATE.md` second.
3. Load `ROADMAP.md` third.
4. Load `DECISIONS.md` fourth.
5. Load `NEXT_SESSION_PROMPT.md` fifth.
6. Load only the source files needed for the current session.
7. Do not redesign the architecture unless the user explicitly asks.
8. Do not add optional features before MVP completion.
9. Do not change database schema casually.
10. Do not hard-code model names.
11. Do not hard-code user paths.
12. Do not commit secrets.
13. Do not use live external APIs inside unit tests.
14. At the end of every session, update `CURRENT_STATE.md`.
15. At the end of every session, write the next exact prompt into `NEXT_SESSION_PROMPT.md`.

## 30. Required Start-Of-Session Checklist

At the beginning of each Codex session, Codex should write a short checklist in the chat:

```text
I have loaded:
1. PROJECT_OVERVIEW.md
2. CURRENT_STATE.md
3. ROADMAP.md
4. DECISIONS.md
5. NEXT_SESSION_PROMPT.md
6. Current session files only

Current session goal:
<one sentence>

Files I expect to edit:
<list>

Files I will not touch:
<list>
```

This helps prevent context drift and accidental overbuilding.

## 31. Required End-Of-Session Checklist

At the end of each Codex session, Codex must update the repo and report:

```text
Completed:
<list>

Tests run:
<commands and result>

Files changed:
<list>

Decisions made:
<list or none>

Known issues:
<list or none>

Next session prompt written to:
NEXT_SESSION_PROMPT.md
```

## 32. CURRENT_STATE.md Template

Codex should maintain this file like a compact project memory.

```markdown
# Current State

Last Updated: YYYY-MM-DD
Current Phase: Session X
MVP Status: Not complete / Complete

## What Exists

## What Works

## What Does Not Work Yet

## Files Recently Changed

## Decisions Since Last Session

## Known Issues

## Next Session Goal
```

## 33. DECISIONS.md Template

```markdown
# Decisions

## Decision Log

### YYYY-MM-DD, Decision Title

Decision:

Reason:

Tradeoffs:

Affected Files:
```

## 34. ROADMAP.md Template

```markdown
# Roadmap

## MVP Sessions

- [ ] Session 0, Repo Foundation
- [ ] Session 1, Core Config, Logging, Database, URL Parser
- [ ] Session 2, FastAPI App And Ingest Endpoints
- [ ] Session 3, Transcript Extraction And Cleaning
- [ ] Session 4, Anthropic Client And AI Analysis Pipeline
- [ ] Session 5, Markdown Report Generation And Storage
- [ ] Session 6, Worker Pipeline
- [ ] Session 7, Telegram Bot Integration
- [ ] Session 8, iOS Shortcut Guide And End-To-End Local Test
- [ ] Session 9, Hardening And MVP Release

## Optional Enhancements

- [ ] Audio transcription fallback
- [ ] Obsidian integration
- [ ] Web reader
- [ ] Search index
- [ ] WhatsApp integration
```

## 35. NEXT_SESSION_PROMPT.md Template

```markdown
# Next Session Prompt

Copy and paste this into the next Codex session.

```text
<exact prompt goes here>
```
```

## 36. Testing Standards

### 36.1 Unit Tests

Required:

1. URL parser tests.
2. Security tests.
3. Chunker tests.
4. Markdown generation tests.
5. Database job status tests.
6. Telegram payload parsing tests.

### 36.2 Mock External APIs

Do not hit Anthropic, Telegram, or YouTube from unit tests.

Use mocks and fixture payloads.

### 36.3 Manual Test Commands

README should include:

```bash
pytest
python scripts/init_db.py
python scripts/process_url_once.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

## 37. Deployment Notes

MVP can run on:

1. A Mac that stays on.
2. A small VPS.
3. A home server.
4. A Docker container later, but Docker is not required for MVP.

For Telegram webhooks, the server needs an HTTPS-accessible URL. Local development can use a secure tunnel. Production can use a VPS or reverse proxy.

Do not make Docker mandatory in the first build unless the user asks.

## 38. Minimum MVP Definition

The MVP is complete when:

1. User can send a YouTube URL through Telegram.
2. User can send a YouTube URL through iOS Shortcut.
3. Backend creates a job.
4. Transcript is extracted when available.
5. Claude API generates an analysis.
6. Markdown report is stored locally.
7. Telegram notifies the user of completion.
8. Errors are clear and visible.
9. Codex continuation files are maintained.
10. README explains setup and operation.

## 39. What Not To Build Yet

Do not build these during MVP:

1. WhatsApp integration.
2. Notion integration.
3. Google Drive integration.
4. Web dashboard.
5. Multi-user account system.
6. Payment system.
7. Browser extension.
8. Automatic YouTube playlist scraping.
9. Audio download and transcription.
10. Complex vector database.
11. RAG system.
12. Agent swarm.
13. Multi-model evaluation system.

These can come later, after the basic personal workflow is reliable.

## 40. Final Instruction To Codex

Build the system one controlled session at a time.

Prioritize the boring reliable pipeline over clever agent behavior.

The main risk is drift. The protection against drift is the source-of-truth document set:

1. `PROJECT_OVERVIEW.md`
2. `CURRENT_STATE.md`
3. `ROADMAP.md`
4. `DECISIONS.md`
5. `NEXT_SESSION_PROMPT.md`

Every session must update the state and write the next prompt before stopping.
