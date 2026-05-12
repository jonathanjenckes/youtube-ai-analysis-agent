"""Anthropic Messages API client."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from anthropic import Anthropic, AnthropicError


class AnthropicClientError(RuntimeError):
    """Raised when Anthropic analysis cannot be completed."""


@dataclass(frozen=True)
class AnthropicConfig:
    """Configuration required for Anthropic Messages API calls."""

    api_key: str
    model: str
    max_tokens: int


class AnthropicAnalysisClient:
    """Small wrapper around Anthropic's Messages API."""

    def __init__(
        self,
        config: AnthropicConfig,
        *,
        client_factory: Callable[..., Any] = Anthropic,
    ) -> None:
        if not config.api_key.strip():
            raise AnthropicClientError("ANTHROPIC_API_KEY is required for analysis.")
        if not config.model.strip():
            raise AnthropicClientError("ANTHROPIC_MODEL is required for analysis.")
        if config.max_tokens < 1:
            raise AnthropicClientError("ANTHROPIC_MAX_TOKENS must be at least 1.")

        self._model = config.model
        self._max_tokens = config.max_tokens
        self._client = client_factory(api_key=config.api_key)

    @property
    def model(self) -> str:
        """Return the configured Anthropic model name."""

        return self._model

    def complete(self, *, system_prompt: str, user_prompt: str) -> str:
        """Send a single analysis prompt and return text content."""

        try:
            message = self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
        except AnthropicError as exc:
            raise AnthropicClientError("Anthropic Messages API request failed.") from exc

        text = _extract_text(message).strip()
        if not text:
            raise AnthropicClientError("Anthropic Messages API returned no text content.")
        return text


def _extract_text(message: Any) -> str:
    content_blocks = getattr(message, "content", None)
    if content_blocks is None and isinstance(message, dict):
        content_blocks = message.get("content")
    if content_blocks is None:
        return ""

    parts: list[str] = []
    for block in content_blocks:
        if isinstance(block, dict):
            if block.get("type") == "text":
                parts.append(str(block.get("text", "")))
            continue

        if getattr(block, "type", None) == "text":
            parts.append(str(getattr(block, "text", "")))

    return "\n".join(part for part in parts if part)
