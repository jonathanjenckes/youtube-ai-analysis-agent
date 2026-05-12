"""AI transcript analysis pipeline."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol

from yt_agent.ai.prompts import (
    PROMPT_VERSION,
    REPORT_SECTION_KEYS,
    build_chunk_prompt,
    build_synthesis_prompt,
)
from yt_agent.transcripts.extractor import TranscriptExtractionResult


class AnalysisError(RuntimeError):
    """Raised when transcript analysis cannot be completed."""


class AnalysisClient(Protocol):
    """Protocol implemented by Anthropic and test clients."""

    @property
    def model(self) -> str:
        """Configured model name."""

    def complete(self, *, system_prompt: str, user_prompt: str) -> str:
        """Return model text for a prompt."""


@dataclass(frozen=True)
class ChunkAnalysis:
    """Structured analysis for one transcript chunk."""

    chunk_index: int
    chunk_total: int
    prompt_version: str
    content: dict[str, Any]


@dataclass(frozen=True)
class StructuredReportContent:
    """Report-ready content produced by AI analysis before Markdown generation."""

    video_id: str
    model: str
    prompt_version: str
    transcript_source: str
    transcript_language_code: str
    title: str | None
    tags: list[str]
    sections: dict[str, str]
    chunk_analyses: list[ChunkAnalysis]


def analyze_transcript(
    transcript: TranscriptExtractionResult,
    *,
    client: AnalysisClient,
) -> StructuredReportContent:
    """Analyze transcript chunks and synthesize structured report content."""

    if not transcript.chunks:
        raise AnalysisError("Transcript has no chunks to analyze.")

    chunk_analyses: list[ChunkAnalysis] = []
    for chunk in transcript.chunks:
        prompt = build_chunk_prompt(chunk)
        raw_response = client.complete(system_prompt=prompt.system, user_prompt=prompt.user)
        chunk_analyses.append(
            ChunkAnalysis(
                chunk_index=chunk.index,
                chunk_total=chunk.total,
                prompt_version=prompt.version,
                content=_parse_json_object(raw_response, label=f"chunk {chunk.index} analysis"),
            )
        )

    synthesis_prompt = build_synthesis_prompt(
        chunk_analyses_json=json.dumps(
            [analysis.content for analysis in chunk_analyses],
            ensure_ascii=True,
            sort_keys=True,
        )
    )
    synthesis = _parse_json_object(
        client.complete(
            system_prompt=synthesis_prompt.system,
            user_prompt=synthesis_prompt.user,
        ),
        label="synthesis",
    )

    sections = _coerce_sections(synthesis.get("sections"))

    return StructuredReportContent(
        video_id=transcript.video_id,
        model=client.model,
        prompt_version=PROMPT_VERSION,
        transcript_source=transcript.source,
        transcript_language_code=transcript.language_code,
        title=_coerce_optional_string(synthesis.get("title")),
        tags=_coerce_string_list(synthesis.get("tags")),
        sections=sections,
        chunk_analyses=chunk_analyses,
    )


def _parse_json_object(raw_response: str, *, label: str) -> dict[str, Any]:
    normalized = _extract_json_text(raw_response)
    try:
        parsed = json.loads(normalized)
    except json.JSONDecodeError as exc:
        raise AnalysisError(f"Model returned invalid JSON for {label}.") from exc

    if not isinstance(parsed, dict):
        raise AnalysisError(f"Model returned non-object JSON for {label}.")
    return parsed


def _extract_json_text(raw_response: str) -> str:
    text = raw_response.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    decoder = json.JSONDecoder()
    for index, character in enumerate(text):
        if character != "{":
            continue
        try:
            _, end = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        return text[index : index + end]

    return text


def _coerce_sections(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        raise AnalysisError("Synthesis response must include a sections object.")

    sections: dict[str, str] = {}
    missing_keys: list[str] = []
    for key in REPORT_SECTION_KEYS:
        section_value = value.get(key)
        if section_value is None:
            missing_keys.append(key)
            continue
        sections[key] = str(section_value).strip()

    if missing_keys:
        joined = ", ".join(missing_keys)
        raise AnalysisError(f"Synthesis response missing required section keys: {joined}.")

    return sections


def _coerce_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _coerce_optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
