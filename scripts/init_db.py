"""Initialize the SQLite database."""

from yt_agent.config import get_settings
from yt_agent.storage.db import initialize_database


def main() -> None:
    settings = get_settings()
    initialize_database(settings.sqlite_path)
    print(f"Initialized SQLite database at {settings.sqlite_path}")


if __name__ == "__main__":
    main()
