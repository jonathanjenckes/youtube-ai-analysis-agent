# Roadmap

## Session 0: Repo Foundation

Status: Complete

- Create repo structure.
- Create planning and continuity documents.
- Create environment and packaging files.
- Add empty package files and placeholder tests.

## Session 1: Core Config, Logging, Database, URL Parser

Status: Complete

- Implement config loading.
- Implement logging configuration.
- Implement SQLite initialization.
- Implement job helpers.
- Implement YouTube URL parsing.
- Implement app secret validation.
- Add tests for config, database, URL parsing, and security.
- Add `scripts/init_db.py`.

## Session 2: FastAPI App And Ingest Endpoints

Status: Complete

- Implement FastAPI app.
- Add `/health`.
- Add Shortcut ingest endpoint.
- Add Telegram webhook skeleton.
- Create queued jobs from incoming URLs.

## Session 3: Transcript Extraction And Cleaning

Status: Complete

- Extract available YouTube captions.
- Clean transcript text.
- Chunk transcript text safely.
- Save transcripts locally.

## Session 4: Anthropic Client And AI Analysis Pipeline

Status: Complete

- Implement Anthropic client.
- Add versioned prompts.
- Analyze chunks.
- Synthesize final report content.

## Session 5: Markdown Report Generation And Storage

Status: Complete

- Generate required Markdown report structure.
- Save reports by month.
- Update jobs with paths and summaries.

## Session 6: Worker Pipeline

Status: Complete

- Wire job processing lifecycle.
- Implement manual full processing CLI.
- Handle failures clearly.

## Session 7: Telegram Bot Integration

Status: Complete

- Parse Telegram updates.
- Validate allowed chat IDs.
- Send receipt and completion messages.
- Add webhook setup script.

## Session 8: iOS Shortcut Guide And End-To-End Local Test

Status: Complete

- Finalize Shortcut setup docs.
- Add curl examples.
- Document local tunnel setup.
- Document end-to-end local flow.

## Session 9: MVP Hardening And Local Smoke-Test Review

Status: Complete

- Follow the documented local setup and smoke-test flows.
- Fix only small bugs exposed by those workflows.
- Improve any confusing docs discovered during smoke testing.
- Do not add optional storage integrations, audio download, or speech-to-text.

## Session 10: Real-Service End-To-End MVP Validation

Status: Blocked, partial validation complete

- Run the documented local workflows with real local secrets.
- Process one captioned YouTube video through transcript extraction, Anthropic analysis, Markdown report generation, and SQLite job updates.
- Smoke test Telegram with a valid bot token, allowed chat ID, webhook secret, and local HTTPS tunnel.
- Fix only small concrete bugs or documentation gaps exposed by real-service validation.
- Do not add optional storage integrations, audio download, or speech-to-text.

Session 10 confirmed real YouTube caption extraction and hardened CLI/network error handling, but full real-service validation could not complete because the repo root did not contain a real `.env` and no HTTPS tunnel was configured.

## Session 11: Real-Service Validation Retry

Status: Blocked

- Add or verify local-only `.env` values for Anthropic, Telegram, allowed chat ID, webhook secret, `JOB_MODE=inline`, and an HTTPS tunnel `APP_BASE_URL`.
- Process one captioned YouTube video through transcript extraction, Anthropic analysis, Markdown report generation, and SQLite job updates.
- Smoke test Telegram through the configured webhook using the real bot and allowed chat.
- Fix only small concrete bugs or documentation gaps exposed by validation.
- Do not add optional storage integrations, audio download, or speech-to-text.

Session 11 stopped before real-service validation because `.env` was missing from the repo root. Follow-up troubleshooting created a local ignored `.env` scaffold, set `JOB_MODE=inline`, generated local app/webhook secrets, confirmed the local API health check, confirmed ngrok is installed/configured, and wrote an ngrok HTTPS URL to `APP_BASE_URL`. Real Anthropic and Telegram account values are still required, and the ngrok HTTPS tunnel should be rechecked after restart.

## Session 12: Real-Service Validation Retry

Status: Complete

- Add or verify local-only `.env` values for Anthropic, Telegram, allowed chat ID, webhook secret, `JOB_MODE=inline`, and an HTTPS tunnel `APP_BASE_URL`.
- Process one captioned YouTube video through transcript extraction, Anthropic analysis, Markdown report generation, and SQLite job updates.
- Smoke test Telegram through the configured webhook using the real bot and allowed chat.
- Fix only small concrete bugs or documentation gaps exposed by validation.
- Do not add optional storage integrations, audio download, or speech-to-text.

Session 12 completed real-service validation. Manual processing completed job 10 for `arj7oStGLkU`; Telegram webhook smoke testing completed job 12 for `jNQXAC9IVRw`. Validation exposed and fixed a stale Anthropic default model, transient YouTube transcript retrieval retries, and AI JSON response tolerance. Post-validation polish added public YouTube title/channel labeling and Telegram `.md` report document delivery.

## Session 13: MVP Operational Polish

Status: Complete

- Review the completed real-service validation artifacts and docs.
- Improve only small operational rough edges discovered from actual use, such as clearer setup guidance, status inspection commands, or error messages.
- Keep the MVP scope closed: do not add optional storage integrations, audio download, speech-to-text, accounts, public sharing, or a background queue redesign.
- Run `.venv/bin/python -m pytest` and `.venv/bin/python -m ruff check src tests`.

Session 13 reviewed saved validation artifacts and SQLite rows, documented recent job/report inspection commands, logged metadata fallback failures, and made Telegram `.md` document delivery best-effort so a document upload failure does not make a completed job look failed.

## MVP Complete

Status: Complete

The validated MVP is ready for normal local use. Do not create another build session for broad finalization or polish. Start a new session only for a concrete bug, operational issue, or explicit feature request.
