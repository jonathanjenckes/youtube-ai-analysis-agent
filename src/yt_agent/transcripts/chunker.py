"""Transcript chunking helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass

SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


class TranscriptChunkingError(ValueError):
    """Raised when transcript text cannot fit within configured chunk limits."""


@dataclass(frozen=True)
class TranscriptChunk:
    """A bounded transcript chunk ready for later analysis."""

    index: int
    total: int
    text: str
    start_char: int
    end_char: int


def chunk_transcript_text(
    text: str,
    *,
    max_chars_per_chunk: int,
    max_chunks: int,
) -> list[TranscriptChunk]:
    """Split transcript text into readable chunks within configured limits."""

    if max_chars_per_chunk < 1:
        raise ValueError("max_chars_per_chunk must be at least 1.")
    if max_chunks < 1:
        raise ValueError("max_chunks must be at least 1.")

    stripped = text.strip()
    if not stripped:
        return []

    pieces = _split_to_bounded_pieces(stripped, max_chars_per_chunk)
    chunk_texts = _pack_pieces(pieces, max_chars_per_chunk)

    if len(chunk_texts) > max_chunks:
        raise TranscriptChunkingError(
            f"Transcript requires {len(chunk_texts)} chunks, exceeding configured limit of "
            f"{max_chunks}."
        )

    chunks: list[TranscriptChunk] = []
    cursor = 0
    total = len(chunk_texts)
    for index, chunk_text in enumerate(chunk_texts, start=1):
        start = stripped.find(chunk_text, cursor)
        if start == -1:
            start = cursor
        end = start + len(chunk_text)
        chunks.append(
            TranscriptChunk(
                index=index,
                total=total,
                text=chunk_text,
                start_char=start,
                end_char=end,
            )
        )
        cursor = end

    return chunks


def _pack_pieces(pieces: list[str], max_chars: int) -> list[str]:
    chunks: list[str] = []
    current = ""

    for piece in pieces:
        separator = "\n\n" if "\n" in piece or "\n" in current else " "
        candidate = piece if not current else f"{current}{separator}{piece}"
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            chunks.append(current)
        current = piece

    if current:
        chunks.append(current)

    return chunks


def _split_to_bounded_pieces(text: str, max_chars: int) -> list[str]:
    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n{2,}", text) if paragraph.strip()]
    pieces: list[str] = []

    for paragraph in paragraphs:
        if len(paragraph) <= max_chars:
            pieces.append(paragraph)
            continue
        pieces.extend(_split_long_paragraph(paragraph, max_chars))

    return pieces


def _split_long_paragraph(paragraph: str, max_chars: int) -> list[str]:
    sentences = [
        sentence.strip()
        for sentence in SENTENCE_SPLIT_RE.split(paragraph)
        if sentence.strip()
    ]
    pieces: list[str] = []

    for sentence in sentences:
        if len(sentence) <= max_chars:
            pieces.append(sentence)
            continue
        pieces.extend(_split_long_sentence(sentence, max_chars))

    return pieces


def _split_long_sentence(sentence: str, max_chars: int) -> list[str]:
    words = sentence.split()
    pieces: list[str] = []
    current = ""

    for word in words:
        if len(word) > max_chars:
            if current:
                pieces.append(current)
                current = ""
            pieces.extend(
                word[start : start + max_chars] for start in range(0, len(word), max_chars)
            )
            continue

        candidate = word if not current else f"{current} {word}"
        if len(candidate) <= max_chars:
            current = candidate
            continue
        pieces.append(current)
        current = word

    if current:
        pieces.append(current)

    return pieces
