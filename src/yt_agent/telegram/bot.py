"""Telegram bot helpers."""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from starlette.background import BackgroundTasks
from starlette.concurrency import run_in_threadpool

from yt_agent.config import Settings
from yt_agent.core.jobs import create_job
from yt_agent.core.models import Job, YouTubeVideoRef
from yt_agent.core.url_parser import YouTubeURLParseError, parse_youtube_url
from yt_agent.storage.db import connect
from yt_agent.workers.processor import ProcessedJobResult, process_job

URL_RE = re.compile(r"https?://[^\s<>()]+")
TRAILING_PUNCTUATION = ".,;:!?)\"]}'"
logger = logging.getLogger(__name__)

JobProcessor = Callable[..., ProcessedJobResult]


@dataclass(frozen=True)
class TelegramMessage:
    """The Telegram message fields needed by the bot."""

    chat_id: int
    text: str


@dataclass(frozen=True)
class TelegramWebhookResult:
    """Summary of one handled Telegram update."""

    status: str
    job_ids: list[int]


class TelegramBotClient:
    """Small Telegram Bot API client."""

    def __init__(
        self,
        *,
        bot_token: str,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.bot_token = bot_token
        self._http_client = http_client

    async def send_message(self, chat_id: int, text: str) -> None:
        """Send a plain text message to one Telegram chat."""

        await self._post("sendMessage", json={"chat_id": chat_id, "text": text})

    async def send_document(
        self,
        chat_id: int,
        document_path: Path,
        *,
        caption: str | None = None,
    ) -> None:
        """Send a local file as a Telegram document."""

        data: dict[str, Any] = {"chat_id": chat_id}
        if caption:
            data["caption"] = caption
        with document_path.open("rb") as document_file:
            await self._post(
                "sendDocument",
                data=data,
                files={"document": (document_path.name, document_file, "text/markdown")},
            )

    async def set_webhook(self, *, webhook_url: str, secret_token: str) -> dict[str, Any]:
        """Configure the Telegram webhook URL for this bot."""

        response = await self._post(
            "setWebhook",
            json={"url": webhook_url, "secret_token": secret_token},
        )
        return response.json()

    async def _post(
        self,
        method: str,
        *,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
    ) -> httpx.Response:
        if not self.bot_token:
            raise TelegramBotError("TELEGRAM_BOT_TOKEN is required.")

        url = f"https://api.telegram.org/bot{self.bot_token}/{method}"
        if self._http_client is not None:
            try:
                response = await self._http_client.post(url, json=json, data=data, files=files)
                response.raise_for_status()
                return response
            except httpx.HTTPError:
                raise TelegramBotError(f"Telegram Bot API {method} request failed.") from None

        async with httpx.AsyncClient(timeout=20) as client:
            try:
                response = await client.post(url, json=json, data=data, files=files)
                response.raise_for_status()
                return response
            except httpx.HTTPError:
                raise TelegramBotError(f"Telegram Bot API {method} request failed.") from None


class TelegramBotError(RuntimeError):
    """Raised when Telegram bot processing cannot continue."""


class TelegramWebhookHandler:
    """Handle Telegram updates and connect them to queued video jobs."""

    def __init__(
        self,
        *,
        settings: Settings,
        telegram_client: TelegramBotClient,
        job_processor: JobProcessor = process_job,
    ) -> None:
        self.settings = settings
        self.telegram_client = telegram_client
        self.job_processor = job_processor

    async def handle_update(
        self,
        update: dict[str, Any],
        *,
        background_tasks: BackgroundTasks,
    ) -> TelegramWebhookResult:
        """Parse one Telegram update, enqueue jobs, and schedule processing."""

        message = parse_telegram_message(update)
        if message is None:
            return TelegramWebhookResult(status="ignored", job_ids=[])

        update_id = update.get("update_id")
        if isinstance(update_id, int) and not self._claim_update(update_id):
            logger.info("Ignoring duplicate Telegram update %s", update_id)
            return TelegramWebhookResult(status="duplicate", job_ids=[])

        if message.chat_id not in self.settings.telegram_allowed_chat_ids:
            await self.telegram_client.send_message(
                message.chat_id,
                "This chat is not allowed to use this bot.",
            )
            return TelegramWebhookResult(status="forbidden", job_ids=[])

        video_refs = extract_youtube_video_refs(message.text)
        if not video_refs:
            await self.telegram_client.send_message(
                message.chat_id,
                "Send a YouTube video URL to queue an analysis.",
            )
            return TelegramWebhookResult(status="no_url", job_ids=[])

        jobs = [self._create_job(ref.video_id, ref.normalized_url) for ref in video_refs]
        for job in jobs:
            await self.telegram_client.send_message(
                message.chat_id,
                f"Queued job {job.id} for {job.source_url}.",
            )
            if self.settings.job_mode == "inline":
                await self.process_job_and_notify(job.id, message.chat_id)
            else:
                background_tasks.add_task(self.process_job_and_notify, job.id, message.chat_id)

        return TelegramWebhookResult(status="queued", job_ids=[job.id for job in jobs])

    async def process_job_and_notify(self, job_id: int, chat_id: int) -> None:
        """Run one existing worker job and notify Telegram when it finishes."""

        try:
            result = await run_in_threadpool(
                self.job_processor,
                job_id,
                settings=self.settings,
            )
        except Exception as exc:
            await self.telegram_client.send_message(
                chat_id,
                f"Job {job_id} failed: {exc}",
            )
            return

        report_path = result.job.report_path
        suffix = f"\nReport: {report_path}" if report_path else ""
        await self.telegram_client.send_message(
            chat_id,
            f"Job {result.job.id} completed.{suffix}",
        )
        if report_path and report_path.exists():
            try:
                await self.telegram_client.send_document(
                    chat_id,
                    report_path,
                    caption=f"Markdown report for job {result.job.id}",
                )
            except Exception:
                logger.exception(
                    "Failed to send Telegram report document for job %s at %s",
                    result.job.id,
                    report_path,
                )

    def _create_job(self, video_id: str, source_url: str) -> Job:
        with connect(self.settings.sqlite_path) as connection:
            return create_job(connection, video_id=video_id, source_url=source_url)

    def _claim_update(self, update_id: int) -> bool:
        with connect(self.settings.sqlite_path) as connection:
            cursor = connection.execute(
                "INSERT OR IGNORE INTO telegram_updates (update_id) VALUES (?)",
                (update_id,),
            )
            connection.commit()
            return cursor.rowcount == 1


def parse_telegram_message(update: dict[str, Any]) -> TelegramMessage | None:
    """Extract chat ID and text from supported Telegram update shapes."""

    raw_message = (
        update.get("message")
        or update.get("edited_message")
        or update.get("channel_post")
        or update.get("edited_channel_post")
    )
    if not isinstance(raw_message, dict):
        return None

    raw_chat = raw_message.get("chat")
    if not isinstance(raw_chat, dict):
        return None

    chat_id = raw_chat.get("id")
    text = raw_message.get("text") or raw_message.get("caption")
    if not isinstance(chat_id, int) or not isinstance(text, str):
        return None

    return TelegramMessage(chat_id=chat_id, text=text)


def extract_youtube_video_refs(text: str) -> list[YouTubeVideoRef]:
    """Return unique, valid YouTube video references found in message text."""

    refs = []
    seen_urls = set()
    for match in URL_RE.finditer(text):
        candidate = match.group(0).rstrip(TRAILING_PUNCTUATION)
        try:
            ref = parse_youtube_url(candidate)
        except YouTubeURLParseError:
            continue
        if ref.normalized_url in seen_urls:
            continue
        seen_urls.add(ref.normalized_url)
        refs.append(ref)
    return refs
