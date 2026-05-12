"""Logging configuration."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from yt_agent.config import Settings


def configure_logging(settings: Settings) -> None:
    """Configure console and file logging for the application."""

    log_path = Path(settings.log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=3)
    file_handler.setFormatter(formatter)

    root.addHandler(console_handler)
    root.addHandler(file_handler)

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
