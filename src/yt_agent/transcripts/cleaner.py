"""Transcript text normalization."""

from __future__ import annotations

import html
import re
import unicodedata

NOISE_CUE_RE = re.compile(
    r"^\s*[\[(](?:"
    r"music|applause|laughter|laughs|silence|intro|outro|inaudible|"
    r"foreign language|speaking foreign language"
    r")[\])]\s*$",
    re.IGNORECASE,
)

WHITESPACE_RE = re.compile(r"[ \t\f\v]+")
EXCESS_BLANK_LINES_RE = re.compile(r"\n{3,}")


def clean_transcript_text(text: str) -> str:
    """Normalize transcript text while preserving readable paragraph breaks."""

    normalized = unicodedata.normalize("NFKC", html.unescape(text))
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n").replace("\xa0", " ")

    cleaned_lines: list[str] = []
    for line in normalized.split("\n"):
        stripped = WHITESPACE_RE.sub(" ", line).strip()
        if NOISE_CUE_RE.match(stripped):
            continue
        cleaned_lines.append(stripped)

    cleaned = "\n".join(cleaned_lines)
    cleaned = EXCESS_BLANK_LINES_RE.sub("\n\n", cleaned)
    return cleaned.strip()
