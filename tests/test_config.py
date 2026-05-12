from pathlib import Path

from yt_agent.config import Settings


def test_settings_loads_environment_values(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("APP_BASE_URL", "https://agent.example.com")
    monkeypatch.setenv("APP_SECRET_TOKEN", "unit-test-secret")
    monkeypatch.setenv("ANTHROPIC_MODEL", "configurable-model")
    monkeypatch.setenv("TELEGRAM_ALLOWED_CHAT_IDS", "123, 456")
    monkeypatch.setenv("DATA_DIR", "/tmp/youtube-agent-test")

    settings = Settings(_env_file=None)

    assert settings.app_env == "test"
    assert settings.app_base_url == "https://agent.example.com"
    assert settings.anthropic_model == "configurable-model"
    assert settings.telegram_allowed_chat_ids == [123, 456]
    assert settings.reports_dir == Path("/tmp/youtube-agent-test/reports")
    assert settings.transcripts_dir == Path("/tmp/youtube-agent-test/transcripts")
    assert settings.sqlite_path == Path("/tmp/youtube-agent-test/jobs/app.sqlite3")
    assert settings.log_path == Path("/tmp/youtube-agent-test/logs/app.log")


def test_settings_allows_explicit_storage_paths(monkeypatch, tmp_path) -> None:
    db_path = tmp_path / "custom.sqlite3"
    log_path = tmp_path / "custom.log"

    monkeypatch.setenv("SQLITE_PATH", str(db_path))
    monkeypatch.setenv("LOG_PATH", str(log_path))

    settings = Settings(_env_file=None)

    assert settings.sqlite_path == db_path
    assert settings.log_path == log_path
