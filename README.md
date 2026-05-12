# YouTube AI Analysis Agent

Personal automation for turning YouTube URLs into structured AI analysis reports.

The MVP accepts a YouTube URL from an iOS Shortcut, Telegram bot, or manual CLI script, then processes the video transcript into a Markdown report stored locally. The production app is a normal Python backend that calls the Anthropic Claude API directly.

## MVP Scope

- Validate and normalize YouTube URLs.
- Extract available YouTube captions or auto-generated transcripts.
- Fetch public YouTube title/channel metadata when available for report labeling.
- Clean and chunk transcripts.
- Analyze transcript chunks with the Anthropic Messages API.
- Generate a structured Markdown report.
- Store reports, transcripts, logs, and job metadata locally.
- Notify the user through Telegram when processing completes.

Out of scope for MVP: user accounts, OAuth, billing, public sharing, Notion sync, Google Drive sync, Obsidian sync, audio downloads, and Whisper transcription.

## How It Works

1. Send the app a YouTube URL through Telegram, an iOS Shortcut, or the manual command-line script.
2. The backend validates the URL and creates a local processing job.
3. The worker retrieves available public captions or auto-generated transcript text.
4. The transcript is cleaned, chunked, and analyzed with the Anthropic Claude API.
5. The app saves a Markdown report under `data/reports`, stores job metadata in SQLite, and can send the finished report back through Telegram.

## Ways To Use It

- Manual local run: process one YouTube URL from Terminal and save the report locally.
- Telegram bot: send a YouTube URL to your own bot and receive a queued/completed message plus the Markdown report.
- iOS Shortcut: share a YouTube URL from your phone to your Mac-hosted local API.

For a first install, start with the manual command-line flow. Once that works, add Telegram or iOS Shortcut support.

## YouTube Transcript Access Note

This project uses unofficial public transcript retrieval for available YouTube captions and auto-generated transcripts. It is intended for personal/local automation. YouTube may change, restrict, rate-limit, or block transcript access at any time. For production, commercial, or public multi-user use, review YouTube Terms and consider official APIs, user-authorized transcript sources, or user-provided transcript files.

## Local Setup

Create the virtual environment, install dependencies, and create your local `.env`:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` before running the app. Required local values:

```text
APP_ENV=development
APP_BASE_URL=http://localhost:8000
APP_SECRET_TOKEN=replace-with-a-long-local-secret

ANTHROPIC_API_KEY=your_anthropic_api_key
ANTHROPIC_MODEL=claude-sonnet-4-20250514
ANTHROPIC_MAX_TOKENS=4000

TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_ALLOWED_CHAT_IDS=123456789
TELEGRAM_WEBHOOK_SECRET=replace-with-a-long-telegram-webhook-secret

DATA_DIR=./data
REPORTS_DIR=./data/reports
TRANSCRIPTS_DIR=./data/transcripts
SQLITE_PATH=./data/jobs/app.sqlite3
LOG_PATH=./data/logs/app.log

JOB_MODE=background
MAX_TRANSCRIPT_CHARS_PER_CHUNK=18000
MAX_CHUNKS_PER_VIDEO=20
```

Notes:

- `APP_SECRET_TOKEN` is used by the iOS Shortcut and curl requests in the `X-App-Secret` header.
- `ANTHROPIC_API_KEY` is required for real video processing through the manual script or Telegram worker.
- `ANTHROPIC_MODEL` defaults to the stable Anthropic API model name validated during MVP smoke testing. If Anthropic returns a model 404 for your account, replace it with another model name available to your Anthropic workspace.
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_CHAT_IDS`, and `TELEGRAM_WEBHOOK_SECRET` are required only when testing Telegram.
- Set `JOB_MODE=inline` when you want a Telegram webhook smoke test to process before the HTTP response finishes. Keep `JOB_MODE=background` for normal local use.

## Initialize Database

The API initializes SQLite at startup, but you can create it explicitly:

```bash
PYTHONPATH=src .venv/bin/python scripts/init_db.py
```

Expected output:

```text
Initialized SQLite database at data/jobs/app.sqlite3
```

## Run API Locally

Start the FastAPI server:

```bash
.venv/bin/uvicorn yt_agent.main:app --reload --app-dir src
```

Local API base URL:

```text
http://localhost:8000
```

Health check:

```bash
curl -s http://localhost:8000/health
```

Expected response:

```json
{"status":"ok","environment":"development"}
```

## iOS Shortcut Setup

Create a Shortcut that accepts shared URLs and sends them to the local API.

1. Open Shortcuts on iPhone.
2. Create a new Shortcut named `Analyze YouTube`.
3. Open the Shortcut details and enable `Show in Share Sheet`.
4. Set accepted input to URLs.
5. Add `Get URLs from Shortcut Input`.
6. Add `Get Contents of URL`.
7. Set URL to your API endpoint:

```text
http://YOUR-MAC-LAN-IP:8000/ingest/shortcut
```

For local testing from the same Mac, use:

```text
http://localhost:8000/ingest/shortcut
```

For iPhone share sheet use, replace `YOUR-MAC-LAN-IP` with the Mac's local network IP and keep the API running on the Mac.

Configure `Get Contents of URL`:

- Method: `POST`
- Headers:
  - `Content-Type`: `application/json`
  - `X-App-Secret`: the exact `APP_SECRET_TOKEN` value from `.env`
- Request Body: JSON
- JSON body:

```json
{
  "url": "Shortcut Input"
}
```

Add `Get Dictionary Value` for `id` from the response, then add `Show Result` with text like:

```text
Queued YouTube analysis job: id
```

The Shortcut endpoint only queues a job. It does not process the video immediately. Use the manual script for immediate local processing, or Telegram for receipt and completion messages.

## Shortcut Ingest Curl Test

With the API running, test the same request shape the Shortcut sends:

```bash
curl -s -X POST http://localhost:8000/ingest/shortcut \
  -H "Content-Type: application/json" \
  -H "X-App-Secret: replace-with-a-long-local-secret" \
  -d '{"url":"https://youtu.be/dQw4w9WgXcQ"}'
```

Expected response shape:

```json
{
  "id": 1,
  "video_id": "dQw4w9WgXcQ",
  "source_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "status": "queued",
  "report_path": null,
  "transcript_path": null,
  "error_message": null,
  "created_at": "2026-05-05 12:00:00",
  "updated_at": "2026-05-05 12:00:00"
}
```

An invalid or missing `X-App-Secret` returns `401`. A non-YouTube URL returns `400`.

## Process One URL Manually

Use the manual script when you want to run the whole transcript, AI analysis, Markdown report, and job update flow immediately:

```bash
PYTHONPATH=src .venv/bin/python scripts/process_url_once.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

Expected output shape:

```text
Created queued job 1 for https://www.youtube.com/watch?v=VIDEO_ID
Completed job 1
Transcript: data/transcripts/YYYY-MM/YYYY-MM-DD__VIDEO_ID__VIDEO_ID.txt
Report: data/reports/YYYY-MM/YYYY-MM-DD__VIDEO_ID__VIDEO_ID.md
```

This script requires:

- A valid `ANTHROPIC_API_KEY`.
- A YouTube video with available captions or auto-generated subtitles.
- Network access to YouTube transcript data and the Anthropic API.
- Public YouTube metadata access is optional. When available, report and transcript filenames use the video title; otherwise they fall back to the video ID.

## Inspect Recent Jobs

Use SQLite directly when you want to confirm the latest job status, output paths, or failure reason:

```bash
sqlite3 data/jobs/app.sqlite3 \
  "SELECT id, video_id, status, report_path, transcript_path, error_message, updated_at FROM jobs ORDER BY id DESC LIMIT 10;"
```

Open the saved report path from a completed row, or list recent Markdown reports:

```bash
find data/reports -name "*.md" -type f | sort
```

If a job completed but the report title still uses the video ID, public YouTube metadata was unavailable during that run. The report is still valid, and the local output paths remain saved in SQLite.

## Telegram Local Testing

Telegram must reach your local API over a public HTTPS URL. Use a tunnel such as ngrok, Cloudflare Tunnel, or another HTTPS tunnel you already trust.

Example with ngrok:

```bash
ngrok http 8000
```

Set `APP_BASE_URL` in `.env` to the tunnel's HTTPS URL:

```text
APP_BASE_URL=https://your-tunnel.example
```

Then configure the webhook:

```bash
PYTHONPATH=src .venv/bin/python scripts/set_telegram_webhook.py
```

Expected output shape:

```text
Set Telegram webhook to https://your-tunnel.example/webhooks/telegram
{'ok': True, ...}
```

Use your own Telegram account to find the allowed chat ID, then set:

```text
TELEGRAM_ALLOWED_CHAT_IDS=123456789
```

For deterministic local smoke testing, set:

```text
JOB_MODE=inline
```

Use `JOB_MODE=inline` only for short controlled smoke tests. Real video analysis can take longer than Telegram waits for a webhook response, which can make Telegram retry the same update. Keep `JOB_MODE=background` for normal Telegram use.

Restart the API after changing `.env`.

## Telegram Webhook Curl Smoke Tests

These curl tests call the local webhook route directly. They verify local request validation and job creation. They also call Telegram's `sendMessage` API unless you run them through tests with a fake client, so use real bot values only when you intend to send messages.

The allowed-chat and disallowed-chat curl examples require a valid `TELEGRAM_BOT_TOKEN` because the route sends Telegram messages before returning. With a placeholder or fake bot token, those requests can return `500 Internal Server Error` after local validation reaches the Telegram API call.

Unauthorized request:

```bash
curl -s -i -X POST http://localhost:8000/webhooks/telegram \
  -H "Content-Type: application/json" \
  -H "X-Telegram-Bot-Api-Secret-Token: wrong-secret" \
  -d '{"message":{"chat":{"id":123456789},"text":"https://youtu.be/dQw4w9WgXcQ"}}'
```

Expected status:

```text
HTTP/1.1 401 Unauthorized
```

Allowed chat with a YouTube URL:

```bash
curl -s -X POST http://localhost:8000/webhooks/telegram \
  -H "Content-Type: application/json" \
  -H "X-Telegram-Bot-Api-Secret-Token: replace-with-a-long-telegram-webhook-secret" \
  -d '{"message":{"chat":{"id":123456789},"text":"Please analyze https://youtu.be/dQw4w9WgXcQ"}}'
```

Expected response shape:

```json
{"status":"queued","job_ids":[1]}
```

Disallowed chat:

```bash
curl -s -X POST http://localhost:8000/webhooks/telegram \
  -H "Content-Type: application/json" \
  -H "X-Telegram-Bot-Api-Secret-Token: replace-with-a-long-telegram-webhook-secret" \
  -d '{"message":{"chat":{"id":987654321},"text":"https://youtu.be/dQw4w9WgXcQ"}}'
```

Expected response:

```json
{"status":"forbidden","job_ids":[]}
```

## Run Tests

```bash
.venv/bin/python -m pytest
.venv/bin/python -m ruff check src tests
```

The tests mock Telegram and worker processing where needed. They do not call real YouTube, Anthropic, or Telegram services.

## Data Layout

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

Generated runtime data is ignored by git except for `data/.gitkeep`.
