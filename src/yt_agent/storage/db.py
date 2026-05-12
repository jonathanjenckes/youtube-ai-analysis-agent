"""SQLite storage helpers."""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id TEXT NOT NULL,
    source_url TEXT NOT NULL,
    status TEXT NOT NULL,
    report_path TEXT,
    transcript_path TEXT,
    error_message TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_jobs_video_id ON jobs(video_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE TABLE IF NOT EXISTS telegram_updates (
    update_id INTEGER PRIMARY KEY,
    received_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def connect(sqlite_path: str | Path) -> sqlite3.Connection:
    """Open a SQLite connection with row dictionaries enabled."""

    path = Path(sqlite_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(sqlite_path: str | Path) -> None:
    """Create database parent directories and required tables/indexes."""

    with connect(sqlite_path) as connection:
        connection.executescript(SCHEMA_SQL)
