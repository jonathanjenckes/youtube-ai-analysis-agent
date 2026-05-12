"""Versioned prompts for transcript analysis."""

from __future__ import annotations

from dataclasses import dataclass

from yt_agent.transcripts.chunker import TranscriptChunk

PROMPT_VERSION = "2026-05-06.v2"


REPORT_SECTION_KEYS = (
    "executive_summary",
    "core_thesis",
    "detailed_breakdown",
    "key_ideas_and_claims",
    "tools_methods_frameworks",
    "practical_applications",
    "implementation_plan",
    "exercises_or_action_items",
    "analogies_and_mental_models",
    "real_world_examples_and_scenarios",
    "critical_analysis",
    "open_questions",
    "best_quotes",
    "search_tags",
)


@dataclass(frozen=True)
class Prompt:
    """One prompt payload sent to the model."""

    version: str
    system: str
    user: str


CHUNK_SYSTEM_PROMPT = f"""\
You are a precise research analyst extracting durable insight from YouTube transcripts.
Return only valid JSON. Use prompt version {PROMPT_VERSION}.
Do not write Markdown. Do not include code fences.
Do not invent facts that are not supported by the transcript chunk.
Prefer clear explanation over impressive wording.
"""

SYNTHESIS_SYSTEM_PROMPT = f"""\
You are a precise research analyst synthesizing chunk-level notes into report-ready content.
Return only valid JSON. Use prompt version {PROMPT_VERSION}.
Do not write Markdown. Do not include code fences.
Write for a user who wants help understanding complex ideas deeply and practically.
Do not invent facts about the speaker or video.
You may create clearly labeled illustrative examples based on transcript concepts.
"""


def build_chunk_prompt(chunk: TranscriptChunk) -> Prompt:
    """Build the prompt for one transcript chunk."""

    user = f"""\
Analyze transcript chunk {chunk.index} of {chunk.total}.

Return JSON with this exact object shape:
{{
  "summary": "concise chunk summary",
  "core_points": ["important ideas, claims, or arguments"],
  "tools_methods_frameworks": ["tools, methods, frameworks, or processes mentioned"],
  "practical_applications": ["specific applications or use cases"],
  "action_items": ["exercises, steps, or recommended actions"],
  "real_world_examples": ["concrete examples or scenarios that illustrate abstract ideas"],
  "quotes": ["short important lines from the transcript"],
  "questions": ["open questions or uncertainties"],
  "tags": ["search tags"],
  "critical_notes": ["critical analysis notes"]
}}

Transcript chunk:
{chunk.text}
"""
    return Prompt(version=PROMPT_VERSION, system=CHUNK_SYSTEM_PROMPT, user=user)


def build_synthesis_prompt(*, chunk_analyses_json: str) -> Prompt:
    """Build the prompt that synthesizes chunk analyses into report content."""

    section_keys = ", ".join(f'"{key}"' for key in REPORT_SECTION_KEYS)
    user = f"""\
Synthesize these chunk analyses into structured content for a later Markdown report.

Return JSON with this exact object shape:
{{
  "title": null,
  "tags": ["search tags"],
  "sections": {{
    "executive_summary": "...",
    "core_thesis": "...",
    "detailed_breakdown": "...",
    "key_ideas_and_claims": "...",
    "tools_methods_frameworks": "...",
    "practical_applications": "...",
    "implementation_plan": "...",
    "exercises_or_action_items": "...",
    "analogies_and_mental_models": "...",
    "real_world_examples_and_scenarios": "...",
    "critical_analysis": "...",
    "open_questions": "...",
    "best_quotes": "...",
    "search_tags": "..."
  }}
}}

The sections object must include these keys: {section_keys}.
Do not generate Markdown. Keep content report-ready but plain.

Section guidance:
- executive_summary: Explain the whole video in plain language, focusing on the highest-value ideas.
- core_thesis: State the central argument in 1-2 tight paragraphs.
- detailed_breakdown: Walk through the video in order and preserve the speaker's progression.
- key_ideas_and_claims: Identify the most important claims, assumptions, and takeaways.
- tools_methods_frameworks: Extract named tools, systems, processes, formulas, or methods.
- practical_applications: Explain where the ideas could be used in life, work, business,
  learning, or creative projects.
- implementation_plan: Turn the ideas into concrete steps someone could follow.
- exercises_or_action_items: Give specific actions or reflection prompts after watching.
- analogies_and_mental_models: Explain abstract ideas through simple comparisons or models.
- real_world_examples_and_scenarios: Walk through concrete examples, before/after
  situations, or situation/action/result scenarios. Label invented examples as illustrative.
- critical_analysis: Evaluate strengths, weaknesses, blind spots, and unsupported claims.
- open_questions: Identify what remains uncertain or worth investigating.
- best_quotes: Preserve concise transcript-supported lines or close paraphrases.
- search_tags: Provide searchable tags and phrases.

Chunk analyses JSON:
{chunk_analyses_json}
"""
    return Prompt(version=PROMPT_VERSION, system=SYNTHESIS_SYSTEM_PROMPT, user=user)
