# Decisions

## 2026-05-05: Use Planned MVP Stack

Decision: Use Python 3.11+, FastAPI, Uvicorn, SQLite, httpx, youtube-transcript-api, pydantic-settings, pytest, and ruff.

Rationale: This matches the project plan and keeps local operation simple.

## 2026-05-05: Keep Session 0 To Repo Foundation

Decision: Session 0 only creates structure, documents, placeholders, and test scaffolding.

Rationale: The build plan explicitly asks for controlled sessions to avoid context drift and premature implementation.

## 2026-05-05: Treat Current Folder As Repo Root

Decision: Create the planned repository files directly in the current workspace folder.

Rationale: The workspace already contains the project plan and appears to be the intended project root.

## 2026-05-05: Require A Handoff Prompt After Every Session

Decision: Every build session must end by updating `NEXT_SESSION_PROMPT.md` with a short copy-paste prompt for the next session.

Rationale: The project will move across Codex sessions, so each session needs an explicit transfer note that preserves the starting point, scope, file list, constraints, and verification steps.

## 2026-05-05: Use A Minimal Jobs Table For MVP State

Decision: Store jobs in one SQLite `jobs` table with video ID, source URL, status, optional output paths, optional error message, and created/updated timestamps.

Rationale: Session 1 only needs durable ingest and lifecycle state. A single table is enough for the MVP and can support later transcript, analysis, report, worker, Telegram, and Shortcut sessions without adding premature storage integrations.

## 2026-05-05: Normalize YouTube URLs To Canonical Watch URLs

Decision: Accept common YouTube video URL forms, extract the 11-character video ID, and normalize stored URLs to `https://www.youtube.com/watch?v={video_id}`.

Rationale: Canonical URLs make duplicate handling and report metadata simpler while still allowing users to submit mobile, short, embed, live, and youtu.be links.

## 2026-05-05: Accept Comma-Separated Telegram Chat IDs In Config

Decision: Parse `TELEGRAM_ALLOWED_CHAT_IDS` as a comma-separated list of integers.

Rationale: This matches `.env.example` and is easier to maintain by hand than requiring JSON syntax in the environment file.

## 2026-05-05: Authenticate Shortcut Ingest With `X-App-Secret`

Decision: Require the iOS Shortcut ingest endpoint to send the configured app secret in the `X-App-Secret` HTTP header.

Rationale: A header-based shared secret keeps the request body focused on the submitted URL and is straightforward for iOS Shortcuts and curl-based local testing.

## 2026-05-05: Prefer Manual Captions Before Auto-Generated Subtitles

Decision: Transcript extraction selects manually created captions for requested languages before falling back to auto-generated subtitles and then any available transcript.

Rationale: Human captions are usually cleaner, but the MVP still needs to work when only auto-generated subtitles are available.

## 2026-05-05: Enforce Transcript Chunk Limits Strictly

Decision: Transcript chunking raises an explicit error when cleaned transcript text requires more chunks than `MAX_CHUNKS_PER_VIDEO`.

Rationale: Silent truncation would create incomplete analyses. Later worker processing can mark the job failed with a clear error message if a transcript exceeds configured limits.

## 2026-05-05: Use Video ID In Transcript Filenames Until Titles Exist

Decision: Transcript persistence supports title-based filenames, but uses the video ID as the filename title portion when no video title has been retrieved yet.

Rationale: Session 3 does not fetch YouTube metadata. This keeps saved transcript paths deterministic now and leaves the planned report/title metadata work for later sessions.

## 2026-05-05: Use Versioned JSON Prompts For AI Analysis

Decision: AI analysis uses prompt version `2026-05-05.v1`, asks Anthropic for JSON-only chunk analysis and synthesis responses, and validates that the synthesized report content includes every required report section key before later Markdown generation.

Rationale: Versioned prompts make analysis behavior auditable across future runs. JSON-only intermediate output keeps Session 4 separate from report rendering while giving Session 5 a stable structured input contract.

## 2026-05-05: Keep Report Metadata Separate From AI Content

Decision: Markdown report rendering accepts `StructuredReportContent` from AI analysis plus a separate `ReportMetadata` object for URL, raw transcript, processed date, channel, and status.

Rationale: AI analysis should provide report content, while deterministic operational metadata should come from the job, transcript, and worker pipeline. Keeping those inputs separate makes Session 6 worker wiring straightforward without asking the model to reproduce known system facts.

## 2026-05-05: Use A Synchronous Injectable Worker For MVP Processing

Decision: Process one queued job synchronously through an injectable `process_job` function, and expose manual local full processing through `scripts/process_url_once.py`.

Rationale: The MVP needs a predictable lifecycle before background orchestration. Dependency injection lets tests mock transcript extraction and AI analysis so worker tests never call YouTube, Anthropic, or Telegram.

## 2026-05-05: Use Telegram Webhook Secret Header And Allowed Chat IDs

Decision: Require Telegram webhook requests to include the configured `X-Telegram-Bot-Api-Secret-Token` value and only allow explicitly configured chat IDs to queue jobs.

Rationale: This keeps the personal bot private while matching Telegram's webhook secret mechanism and the existing `TELEGRAM_ALLOWED_CHAT_IDS` configuration.

## 2026-05-05: Map `JOB_MODE` To Inline Or FastAPI Background Telegram Processing

Decision: Telegram webhook jobs use the same worker path in both modes: `inline` awaits processing before the webhook response, while `background` schedules processing with FastAPI background tasks.

Rationale: This preserves one processing implementation for the MVP and gives local testing a deterministic inline path without adding a separate queue or storage integration.

## 2026-05-06: Default To Anthropic Sonnet 4 Dated Model For MVP Validation

Decision: Use `claude-sonnet-4-20250514` as the default `ANTHROPIC_MODEL` in config, `.env.example`, and README examples.

Rationale: Real-service validation showed the previous Haiku aliases returned model 404 errors for the configured Anthropic workspace, while `claude-sonnet-4-20250514` completed live analysis successfully. The model remains configurable through environment variables.

## 2026-05-06: Accept JSON Wrapped In Common Model Formatting

Decision: AI analysis parsing accepts a valid JSON object even if the model wraps it in a Markdown code fence or includes a short preface before the object.

Rationale: Telegram real-service validation showed Claude can occasionally return valid JSON with surrounding formatting despite JSON-only instructions. Accepting the object keeps the MVP robust while still rejecting responses that do not contain a JSON object.

## 2026-05-06: Use Public YouTube oEmbed Metadata For Report Labels

Decision: Fetch public YouTube oEmbed metadata during worker processing and use the returned title/channel for transcript filenames, report filenames, and report headers when available.

Rationale: Real reports should be labeled by the actual video title instead of opaque video IDs. oEmbed provides public title and author metadata without adding YouTube Data API keys or optional storage integrations, and failures fall back to the previous video ID behavior.

## 2026-05-06: Send Completed Markdown Reports Back Through Telegram

Decision: After Telegram-triggered processing completes, send the saved Markdown report back to the submitting allowed chat as a Telegram document when the local report file exists.

Rationale: The report should remain saved locally under `data/reports/`, but sending a copy back through Telegram makes the MVP usable from a phone without adding any storage integration or changing the worker pipeline.

## 2026-05-06: Dedupe Telegram Retries By Update ID

Decision: Store handled Telegram `update_id` values in SQLite and ignore duplicate updates before creating jobs.

Rationale: Real Telegram webhook retries can occur when analysis takes longer than Telegram waits for the HTTP response, especially if `JOB_MODE=inline` is used for full videos. Dedupe keeps retries from creating duplicate jobs or repeated Anthropic calls while still allowing a user to intentionally submit the same video again in a new Telegram message.

## 2026-05-06: Use Prompt V2 For More Concrete Learning Reports

Decision: Add prompt version `2026-05-06.v2`, include light section-by-section guidance, add a `Real-World Examples and Scenarios` report section, remove `Raw Transcript` from Markdown reports, and stop sending the full cleaned transcript to the synthesis prompt.

Rationale: The tool is meant to help the user understand complex ideas, not only summarize videos. Real-world scenarios improve comprehension, while removing the transcript from the final report and synthesis prompt keeps saved reports cleaner and reduces token use. Full transcripts remain available as separate `.txt` files.
