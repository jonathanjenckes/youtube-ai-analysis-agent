import pytest

from yt_agent.core.security import (
    SecurityValidationError,
    is_allowed_chat_id,
    require_matching_token,
    token_matches,
    validate_secret_token,
)


def test_validate_secret_token_accepts_strong_token() -> None:
    assert validate_secret_token("  strong-secret-token  ") == "strong-secret-token"


@pytest.mark.parametrize("token", ["", "change-me", "short"])
def test_validate_secret_token_rejects_weak_tokens(token: str) -> None:
    with pytest.raises(SecurityValidationError):
        validate_secret_token(token)


def test_token_matches_uses_exact_match() -> None:
    assert token_matches("expected-token", "expected-token")
    assert not token_matches("wrong-token", "expected-token")
    assert not token_matches(None, "expected-token")


def test_require_matching_token_raises_for_mismatch() -> None:
    with pytest.raises(SecurityValidationError):
        require_matching_token("wrong-token", "expected-token")


def test_is_allowed_chat_id_requires_explicit_allowlist() -> None:
    assert is_allowed_chat_id(123, [123, 456])
    assert not is_allowed_chat_id(789, [123, 456])
