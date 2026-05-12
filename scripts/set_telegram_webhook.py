"""Set the Telegram webhook."""

from __future__ import annotations

import asyncio

from yt_agent.config import get_settings
from yt_agent.telegram.bot import TelegramBotClient


def main() -> None:
    asyncio.run(_main())


async def _main() -> None:
    settings = get_settings()
    webhook_url = f"{settings.app_base_url.rstrip('/')}/webhooks/telegram"
    client = TelegramBotClient(bot_token=settings.telegram_bot_token)
    response = await client.set_webhook(
        webhook_url=webhook_url,
        secret_token=settings.telegram_webhook_secret,
    )
    print(f"Set Telegram webhook to {webhook_url}")
    print(response)


if __name__ == "__main__":
    main()
