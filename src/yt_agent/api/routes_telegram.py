"""Telegram webhook routes."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request, status

from yt_agent.core.security import SecurityValidationError, require_matching_token
from yt_agent.telegram.bot import TelegramBotClient, TelegramWebhookHandler

router = APIRouter(prefix="/webhooks", tags=["telegram"])


@router.post("/telegram", status_code=status.HTTP_202_ACCEPTED)
async def telegram_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_telegram_bot_api_secret_token: str | None = Header(
        default=None,
        alias="X-Telegram-Bot-Api-Secret-Token",
    ),
) -> dict[str, str | list[int]]:
    """Accept a Telegram update and queue any YouTube URLs it contains."""

    settings = request.app.state.settings
    try:
        require_matching_token(
            x_telegram_bot_api_secret_token,
            settings.telegram_webhook_secret,
        )
    except SecurityValidationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    telegram_client = getattr(
        request.app.state,
        "telegram_client",
        TelegramBotClient(bot_token=settings.telegram_bot_token),
    )
    job_processor = getattr(request.app.state, "job_processor", None)
    if job_processor is None:
        handler = TelegramWebhookHandler(settings=settings, telegram_client=telegram_client)
    else:
        handler = TelegramWebhookHandler(
            settings=settings,
            telegram_client=telegram_client,
            job_processor=job_processor,
        )

    result = await handler.handle_update(await request.json(), background_tasks=background_tasks)
    return {"status": result.status, "job_ids": result.job_ids}
