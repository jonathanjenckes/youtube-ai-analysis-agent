"""FastAPI application entry point."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from yt_agent.api.routes_health import router as health_router
from yt_agent.api.routes_shortcut import router as shortcut_router
from yt_agent.api.routes_telegram import router as telegram_router
from yt_agent.config import Settings
from yt_agent.core.security import validate_secret_token
from yt_agent.logging_config import configure_logging
from yt_agent.storage.db import initialize_database

APP_NAME = "YouTube AI Analysis Agent"


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app_settings = settings or Settings()
        validate_secret_token(app_settings.app_secret_token, name="APP_SECRET_TOKEN")
        configure_logging(app_settings)
        initialize_database(app_settings.sqlite_path)
        app.state.settings = app_settings
        app.state.sqlite_path = app_settings.sqlite_path
        yield

    app = FastAPI(title=APP_NAME, lifespan=lifespan)
    app.include_router(health_router)
    app.include_router(shortcut_router)
    app.include_router(telegram_router)
    return app


app = create_app()
