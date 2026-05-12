"""Security validation helpers."""

from __future__ import annotations

import hmac

PLACEHOLDER_TOKENS = {
    "",
    "change-me",
    "changeme",
    "your-secret",
    "your_app_secret",
    "your_telegram_webhook_secret",
}


class SecurityValidationError(ValueError):
    """Raised when security-related configuration is invalid."""


def validate_secret_token(token: str, *, name: str = "secret token") -> str:
    """Validate that a configured secret is usable for request authentication."""

    normalized = token.strip()
    if len(normalized) < 16:
        raise SecurityValidationError(f"{name} must be at least 16 characters long.")
    if normalized.lower() in PLACEHOLDER_TOKENS:
        raise SecurityValidationError(f"{name} must not use a placeholder value.")
    return normalized


def token_matches(provided: str | None, expected: str) -> bool:
    """Compare tokens using a timing-safe equality check."""

    if provided is None:
        return False
    return hmac.compare_digest(provided, expected)


def require_matching_token(provided: str | None, expected: str) -> None:
    """Raise when a provided request token does not match the expected token."""

    if not token_matches(provided, expected):
        raise SecurityValidationError("Invalid request token.")


def is_allowed_chat_id(chat_id: int, allowed_chat_ids: list[int]) -> bool:
    """Return whether a Telegram chat ID is explicitly allowed."""

    return chat_id in allowed_chat_ids
