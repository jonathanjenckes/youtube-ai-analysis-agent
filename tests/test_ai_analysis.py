from __future__ import annotations

import json
from dataclasses import dataclass

import pytest

from yt_agent.ai.analyzer import AnalysisError, analyze_transcript
from yt_agent.ai.anthropic_client import (
    AnthropicAnalysisClient,
    AnthropicClientError,
    AnthropicConfig,
)
from yt_agent.ai.prompts import PROMPT_VERSION, REPORT_SECTION_KEYS
from yt_agent.transcripts.chunker import TranscriptChunk
from yt_agent.transcripts.extractor import TranscriptExtractionResult


@dataclass
class FakeTextBlock:
    text: str
    type: str = "text"


@dataclass
class FakeMessage:
    content: list[FakeTextBlock]


class FakeMessages:
    def __init__(self) -> None:
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return FakeMessage(content=[FakeTextBlock('{"ok": true}')])


class FakeAnthropicSdk:
    last_instance = None

    def __init__(self, *, api_key: str) -> None:
        self.api_key = api_key
        self.messages = FakeMessages()
        FakeAnthropicSdk.last_instance = self


class FakeAnalysisClient:
    model = "unit-test-model"

    def __init__(self, responses: list[dict]) -> None:
        self.responses = [json.dumps(response) for response in responses]
        self.calls = []

    def complete(self, *, system_prompt: str, user_prompt: str) -> str:
        self.calls.append((system_prompt, user_prompt))
        return self.responses.pop(0)


def make_transcript(chunks: list[TranscriptChunk] | None = None) -> TranscriptExtractionResult:
    return TranscriptExtractionResult(
        video_id="dQw4w9WgXcQ",
        language="English",
        language_code="en",
        source="captions",
        segments=[],
        text="First useful idea.\nSecond useful idea.",
        chunks=chunks
        or [
            TranscriptChunk(
                index=1,
                total=1,
                text="First useful idea.\nSecond useful idea.",
                start_char=0,
                end_char=37,
            )
        ],
    )


def make_synthesis_response() -> dict:
    return {
        "title": "Useful Video",
        "tags": ["research", "systems"],
        "sections": {key: f"{key} content" for key in REPORT_SECTION_KEYS},
    }


def test_anthropic_client_uses_configured_model_and_token_limit() -> None:
    client = AnthropicAnalysisClient(
        AnthropicConfig(
            api_key="unit-test-key",
            model="configured-model",
            max_tokens=1234,
        ),
        client_factory=FakeAnthropicSdk,
    )

    response = client.complete(system_prompt="system", user_prompt="user")

    sdk = FakeAnthropicSdk.last_instance
    assert sdk.api_key == "unit-test-key"
    assert response == '{"ok": true}'
    assert sdk.messages.calls == [
        {
            "model": "configured-model",
            "max_tokens": 1234,
            "system": "system",
            "messages": [{"role": "user", "content": "user"}],
        }
    ]


def test_anthropic_client_requires_api_key() -> None:
    with pytest.raises(AnthropicClientError, match="ANTHROPIC_API_KEY"):
        AnthropicAnalysisClient(
            AnthropicConfig(api_key="", model="configured-model", max_tokens=100),
            client_factory=FakeAnthropicSdk,
        )


def test_analyze_transcript_analyzes_chunks_and_synthesizes_report_content() -> None:
    client = FakeAnalysisClient(
        [
            {
                "summary": "Chunk summary",
                "core_points": ["Point"],
                "tools_methods_frameworks": [],
                "practical_applications": ["Application"],
                "action_items": ["Action"],
                "quotes": ["Quote"],
                "questions": ["Question"],
                "tags": ["research"],
                "critical_notes": ["Caveat"],
            },
            make_synthesis_response(),
        ]
    )

    result = analyze_transcript(make_transcript(), client=client)

    assert result.video_id == "dQw4w9WgXcQ"
    assert result.model == "unit-test-model"
    assert result.prompt_version == PROMPT_VERSION
    assert result.transcript_source == "captions"
    assert result.transcript_language_code == "en"
    assert result.title == "Useful Video"
    assert result.tags == ["research", "systems"]
    assert result.sections["executive_summary"] == "executive_summary content"
    assert result.chunk_analyses[0].content["summary"] == "Chunk summary"
    assert len(client.calls) == 2
    assert "Analyze transcript chunk 1 of 1" in client.calls[0][1]
    assert "Synthesize these chunk analyses" in client.calls[1][1]
    assert "Full cleaned transcript for context" not in client.calls[1][1]
    assert "First useful idea.\nSecond useful idea." not in client.calls[1][1]


def test_analyze_transcript_rejects_invalid_model_json() -> None:
    class InvalidJsonClient:
        model = "unit-test-model"

        def complete(self, *, system_prompt: str, user_prompt: str) -> str:
            return "not json"

    with pytest.raises(AnalysisError, match="invalid JSON"):
        analyze_transcript(make_transcript(), client=InvalidJsonClient())


def test_analyze_transcript_accepts_fenced_json_response() -> None:
    class FencedJsonClient:
        model = "unit-test-model"

        def __init__(self) -> None:
            self.responses = [
                '```json\n{"summary": "Chunk summary"}\n```',
                "Here is the JSON:\n" + json.dumps(make_synthesis_response()),
            ]

        def complete(self, *, system_prompt: str, user_prompt: str) -> str:
            return self.responses.pop(0)

    result = analyze_transcript(make_transcript(), client=FencedJsonClient())

    assert result.chunk_analyses[0].content["summary"] == "Chunk summary"
    assert result.sections["executive_summary"] == "executive_summary content"


def test_analyze_transcript_requires_all_report_sections() -> None:
    synthesis = make_synthesis_response()
    synthesis["sections"].pop("open_questions")
    client = FakeAnalysisClient([{"summary": "Chunk summary"}, synthesis])

    with pytest.raises(AnalysisError, match="open_questions"):
        analyze_transcript(make_transcript(), client=client)
