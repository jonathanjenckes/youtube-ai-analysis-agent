import sqlite3
from types import SimpleNamespace

import httpx
from fastapi.testclient import TestClient

from yt_agent.config import Settings
from yt_agent.core.jobs import get_job, update_job_status
from yt_agent.core.models import JobStatus
from yt_agent.main import create_app
from yt_agent.storage.db import connect
from yt_agent.telegram.bot import TelegramBotClient


class FakeTelegramClient:
    def __init__(self, *, fail_documents: bool = False) -> None:
        self.messages = []
        self.documents = []
        self.fail_documents = fail_documents

    async def send_message(self, chat_id: int, text: str) -> None:
        self.messages.append((chat_id, text))

    async def send_document(self, chat_id: int, document_path, *, caption: str | None = None):
        if self.fail_documents:
            raise RuntimeError("mock document upload failure")
        self.documents.append((chat_id, document_path, caption))


def make_test_settings(tmp_path, **overrides) -> Settings:
    return Settings(
        _env_file=None,
        app_env="test",
        app_secret_token="unit-test-secret-token",
        data_dir=tmp_path,
        **overrides,
    )


def test_app_startup_and_health(tmp_path) -> None:
    app = create_app(make_test_settings(tmp_path))

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "environment": "test"}
    assert (tmp_path / "jobs" / "app.sqlite3").exists()


def test_shortcut_ingest_success_creates_queued_job(tmp_path) -> None:
    app = create_app(make_test_settings(tmp_path))

    with TestClient(app) as client:
        response = client.post(
            "/ingest/shortcut",
            headers={"X-App-Secret": "unit-test-secret-token"},
            json={"url": "https://youtu.be/dQw4w9WgXcQ?si=abc123"},
        )

    body = response.json()

    assert response.status_code == 201
    assert body["id"] > 0
    assert body["video_id"] == "dQw4w9WgXcQ"
    assert body["source_url"] == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert body["status"] == "queued"
    assert body["report_path"] is None
    assert body["transcript_path"] is None
    assert body["error_message"] is None
    assert body["created_at"]
    assert body["updated_at"]


def test_shortcut_ingest_rejects_invalid_secret(tmp_path) -> None:
    app = create_app(make_test_settings(tmp_path))

    with TestClient(app) as client:
        response = client.post(
            "/ingest/shortcut",
            headers={"X-App-Secret": "wrong-secret"},
            json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
        )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid request token."}


def test_shortcut_ingest_rejects_invalid_url(tmp_path) -> None:
    app = create_app(make_test_settings(tmp_path))

    with TestClient(app) as client:
        response = client.post(
            "/ingest/shortcut",
            headers={"X-App-Secret": "unit-test-secret-token"},
            json={"url": "https://example.com/watch?v=dQw4w9WgXcQ"},
        )

    assert response.status_code == 400
    assert response.json() == {"detail": "URL host is not a supported YouTube host."}


def test_shortcut_ingest_persists_queued_job(tmp_path) -> None:
    app = create_app(make_test_settings(tmp_path))
    db_path = tmp_path / "jobs" / "app.sqlite3"

    with TestClient(app) as client:
        response = client.post(
            "/ingest/shortcut",
            headers={"X-App-Secret": "unit-test-secret-token"},
            json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
        )

    job_id = response.json()["id"]

    with sqlite3.connect(db_path) as connection:
        row = connection.execute(
            "SELECT id, video_id, source_url, status FROM jobs WHERE id = ?",
            (job_id,),
        ).fetchone()

    assert row == (
        job_id,
        "dQw4w9WgXcQ",
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "queued",
    )


def test_telegram_webhook_rejects_invalid_secret(tmp_path) -> None:
    app = create_app(
        make_test_settings(
            tmp_path,
            telegram_webhook_secret="unit-test-telegram-secret",
            telegram_allowed_chat_ids=[123456789],
        )
    )

    with TestClient(app) as client:
        response = client.post(
            "/webhooks/telegram",
            headers={"X-Telegram-Bot-Api-Secret-Token": "wrong-secret"},
            json={"message": {"chat": {"id": 123456789}, "text": "https://youtu.be/dQw4w9WgXcQ"}},
        )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid request token."}


def test_telegram_webhook_queues_and_processes_youtube_url_with_mocked_worker(tmp_path) -> None:
    settings = make_test_settings(
        tmp_path,
        telegram_webhook_secret="unit-test-telegram-secret",
        telegram_allowed_chat_ids=[123456789],
        job_mode="inline",
    )
    app = create_app(settings)
    telegram_client = FakeTelegramClient()
    processed_job_ids = []

    def fake_process_job(job_id: int, *, settings: Settings):
        processed_job_ids.append(job_id)
        report_path = settings.reports_dir / "unit-test-report.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text("# Unit Test Report\n", encoding="utf-8")
        with connect(settings.sqlite_path) as connection:
            job = update_job_status(
                connection,
                job_id,
                JobStatus.COMPLETED,
                report_path=report_path,
            )
        return SimpleNamespace(job=job)

    app.state.telegram_client = telegram_client
    app.state.job_processor = fake_process_job

    with TestClient(app) as client:
        response = client.post(
            "/webhooks/telegram",
            headers={"X-Telegram-Bot-Api-Secret-Token": "unit-test-telegram-secret"},
            json={
                "update_id": 111,
                "message": {
                    "chat": {"id": 123456789},
                    "text": "Please analyze this: https://youtu.be/dQw4w9WgXcQ?si=abc",
                }
            },
        )

    body = response.json()
    job_id = body["job_ids"][0]

    assert response.status_code == 202
    assert body == {"status": "queued", "job_ids": [job_id]}
    assert processed_job_ids == [job_id]
    report_path = settings.reports_dir / "unit-test-report.md"
    completed_message = f"Job {job_id} completed.\nReport: {report_path}"
    assert telegram_client.messages == [
        (123456789, f"Queued job {job_id} for https://www.youtube.com/watch?v=dQw4w9WgXcQ."),
        (123456789, completed_message),
    ]
    assert telegram_client.documents == [
        (123456789, report_path, f"Markdown report for job {job_id}"),
    ]

    with sqlite3.connect(settings.sqlite_path) as connection:
        row = connection.execute(
            "SELECT id, video_id, source_url, status, report_path FROM jobs WHERE id = ?",
            (job_id,),
        ).fetchone()

    assert row == (
        job_id,
        "dQw4w9WgXcQ",
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "completed",
        str(settings.reports_dir / "unit-test-report.md"),
    )


def test_telegram_webhook_ignores_duplicate_update_id(tmp_path) -> None:
    settings = make_test_settings(
        tmp_path,
        telegram_webhook_secret="unit-test-telegram-secret",
        telegram_allowed_chat_ids=[123456789],
        job_mode="background",
    )
    app = create_app(settings)
    telegram_client = FakeTelegramClient()
    processed_job_ids = []

    def fake_process_job(job_id: int, *, settings: Settings):
        processed_job_ids.append(job_id)
        with connect(settings.sqlite_path) as connection:
            job = update_job_status(connection, job_id, JobStatus.COMPLETED)
        return SimpleNamespace(job=job)

    app.state.telegram_client = telegram_client
    app.state.job_processor = fake_process_job
    payload = {
        "update_id": 222,
        "message": {
            "chat": {"id": 123456789},
            "text": "https://youtu.be/dQw4w9WgXcQ",
        },
    }

    with TestClient(app) as client:
        first = client.post(
            "/webhooks/telegram",
            headers={"X-Telegram-Bot-Api-Secret-Token": "unit-test-telegram-secret"},
            json=payload,
        )
        second = client.post(
            "/webhooks/telegram",
            headers={"X-Telegram-Bot-Api-Secret-Token": "unit-test-telegram-secret"},
            json=payload,
        )

    assert first.status_code == 202
    assert first.json()["status"] == "queued"
    assert second.status_code == 202
    assert second.json() == {"status": "duplicate", "job_ids": []}
    assert len(processed_job_ids) == 1

    with sqlite3.connect(settings.sqlite_path) as connection:
        job_count = connection.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        update_count = connection.execute("SELECT COUNT(*) FROM telegram_updates").fetchone()[0]

    assert job_count == 1
    assert update_count == 1


def test_telegram_webhook_keeps_completed_job_when_document_delivery_fails(tmp_path) -> None:
    settings = make_test_settings(
        tmp_path,
        telegram_webhook_secret="unit-test-telegram-secret",
        telegram_allowed_chat_ids=[123456789],
        job_mode="inline",
    )
    app = create_app(settings)
    telegram_client = FakeTelegramClient(fail_documents=True)

    def fake_process_job(job_id: int, *, settings: Settings):
        report_path = settings.reports_dir / "unit-test-report.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text("# Unit Test Report\n", encoding="utf-8")
        with connect(settings.sqlite_path) as connection:
            job = update_job_status(
                connection,
                job_id,
                JobStatus.COMPLETED,
                report_path=report_path,
            )
        return SimpleNamespace(job=job)

    app.state.telegram_client = telegram_client
    app.state.job_processor = fake_process_job

    with TestClient(app) as client:
        response = client.post(
            "/webhooks/telegram",
            headers={"X-Telegram-Bot-Api-Secret-Token": "unit-test-telegram-secret"},
            json={
                "message": {
                    "chat": {"id": 123456789},
                    "text": "https://youtu.be/dQw4w9WgXcQ",
                }
            },
        )

    body = response.json()
    job_id = body["job_ids"][0]

    assert response.status_code == 202
    assert body == {"status": "queued", "job_ids": [job_id]}
    assert telegram_client.messages[-1] == (
        123456789,
        f"Job {job_id} completed.\nReport: {settings.reports_dir / 'unit-test-report.md'}",
    )


def test_telegram_webhook_schedules_background_processing(tmp_path) -> None:
    settings = make_test_settings(
        tmp_path,
        telegram_webhook_secret="unit-test-telegram-secret",
        telegram_allowed_chat_ids=[123456789],
        job_mode="background",
    )
    app = create_app(settings)
    telegram_client = FakeTelegramClient()
    processed_job_ids = []

    def fake_process_job(job_id: int, *, settings: Settings):
        processed_job_ids.append(job_id)
        with connect(settings.sqlite_path) as connection:
            job = update_job_status(connection, job_id, JobStatus.COMPLETED)
        return SimpleNamespace(job=job)

    app.state.telegram_client = telegram_client
    app.state.job_processor = fake_process_job

    with TestClient(app) as client:
        response = client.post(
            "/webhooks/telegram",
            headers={"X-Telegram-Bot-Api-Secret-Token": "unit-test-telegram-secret"},
            json={
                "message": {
                    "chat": {"id": 123456789},
                    "text": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                }
            },
        )

    assert response.status_code == 202
    assert processed_job_ids == response.json()["job_ids"]
    assert telegram_client.messages[-1] == (
        123456789,
        f"Job {processed_job_ids[0]} completed.",
    )
    assert telegram_client.documents == []


def test_telegram_webhook_sends_failure_message_when_worker_fails(tmp_path) -> None:
    app = create_app(
        make_test_settings(
            tmp_path,
            telegram_webhook_secret="unit-test-telegram-secret",
            telegram_allowed_chat_ids=[123456789],
            job_mode="inline",
        )
    )
    telegram_client = FakeTelegramClient()

    def fake_process_job(job_id: int, *, settings: Settings):
        with connect(settings.sqlite_path) as connection:
            loaded = get_job(connection, job_id)
        assert loaded is not None
        raise RuntimeError("mock worker failure")

    app.state.telegram_client = telegram_client
    app.state.job_processor = fake_process_job

    with TestClient(app) as client:
        response = client.post(
            "/webhooks/telegram",
            headers={"X-Telegram-Bot-Api-Secret-Token": "unit-test-telegram-secret"},
            json={
                "message": {
                    "chat": {"id": 123456789},
                    "text": "https://youtu.be/dQw4w9WgXcQ",
                }
            },
        )

    job_id = response.json()["job_ids"][0]

    assert response.status_code == 202
    assert telegram_client.messages == [
        (123456789, f"Queued job {job_id} for https://www.youtube.com/watch?v=dQw4w9WgXcQ."),
        (123456789, f"Job {job_id} failed: mock worker failure"),
    ]


def test_telegram_webhook_rejects_disallowed_chat_without_creating_job(tmp_path) -> None:
    settings = make_test_settings(
        tmp_path,
        telegram_webhook_secret="unit-test-telegram-secret",
        telegram_allowed_chat_ids=[123456789],
    )
    app = create_app(settings)
    telegram_client = FakeTelegramClient()
    app.state.telegram_client = telegram_client

    with TestClient(app) as client:
        response = client.post(
            "/webhooks/telegram",
            headers={"X-Telegram-Bot-Api-Secret-Token": "unit-test-telegram-secret"},
            json={
                "message": {
                    "chat": {"id": 987654321},
                    "text": "https://youtu.be/dQw4w9WgXcQ",
                }
            },
        )

    assert response.status_code == 202
    assert response.json() == {"status": "forbidden", "job_ids": []}
    assert telegram_client.messages == [
        (987654321, "This chat is not allowed to use this bot."),
    ]
    with sqlite3.connect(settings.sqlite_path) as connection:
        row_count = connection.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    assert row_count == 0


def test_telegram_webhook_prompts_when_message_has_no_youtube_url(tmp_path) -> None:
    app = create_app(
        make_test_settings(
            tmp_path,
            telegram_webhook_secret="unit-test-telegram-secret",
            telegram_allowed_chat_ids=[123456789],
        )
    )
    telegram_client = FakeTelegramClient()
    app.state.telegram_client = telegram_client

    with TestClient(app) as client:
        response = client.post(
            "/webhooks/telegram",
            headers={"X-Telegram-Bot-Api-Secret-Token": "unit-test-telegram-secret"},
            json={"message": {"chat": {"id": 123456789}, "text": "hello"}},
        )

    assert response.status_code == 202
    assert response.json() == {"status": "no_url", "job_ids": []}
    assert telegram_client.messages == [
        (123456789, "Send a YouTube video URL to queue an analysis."),
    ]


def test_telegram_bot_client_uses_mocked_http_transport() -> None:
    requests = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"ok": True, "result": True})

    transport = httpx.MockTransport(handler)

    async def run_client() -> None:
        async with httpx.AsyncClient(transport=transport) as http_client:
            bot = TelegramBotClient(bot_token="unit-test-token", http_client=http_client)
            await bot.send_message(123456789, "Done.")

    import anyio

    anyio.run(run_client)

    assert len(requests) == 1
    assert str(requests[0].url) == "https://api.telegram.org/botunit-test-token/sendMessage"
    assert requests[0].content == b'{"chat_id":123456789,"text":"Done."}'


def test_telegram_bot_client_error_message_does_not_expose_token() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, request=request, json={"ok": False})

    transport = httpx.MockTransport(handler)

    async def run_client() -> str:
        async with httpx.AsyncClient(transport=transport) as http_client:
            bot = TelegramBotClient(bot_token="unit-test-secret-token", http_client=http_client)
            try:
                await bot.send_message(123456789, "Done.")
            except Exception as exc:
                return str(exc)
        raise AssertionError("Expected Telegram send to fail.")

    import anyio

    message = anyio.run(run_client)

    assert message == "Telegram Bot API sendMessage request failed."
    assert "unit-test-secret-token" not in message
