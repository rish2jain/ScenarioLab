"""LLM-based synthesis of raw research results into structured outputs."""

import json
import logging
from typing import Any

from app.llm.factory import get_llm_provider
from app.llm.provider import LLMMessage

logger = logging.getLogger(__name__)


def _strip_code_fences(text: str) -> str:
    """Remove markdown code fences from LLM responses."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


class ResearchSynthesizer:
    """Synthesizes raw research results into structured, module-specific formats."""

    async def synthesize(
        self,
        raw_results: list[dict[str, Any]],
        purpose: str,
        output_schema: str,
        *,
        max_tokens: int = 1500,
    ) -> dict[str, Any]:
        """Synthesize raw research results into a structured output.

        Args:
            raw_results: List of raw research results (from web search or APIs).
            purpose: What the research is for
                (e.g., "persona calibration for a pharma CEO").
            output_schema: JSON schema string describing desired output format.
            max_tokens: Max tokens for LLM response.

        Returns:
            Parsed JSON dict matching the output schema.
        """
        if not raw_results:
            return {}

        # Truncate results to fit in context
        context_parts = []
        total_chars = 0
        for result in raw_results:
            content = result.get("content", "") or result.get("excerpt", "")
            title = result.get("title", "")
            entry = f"**{title}**\n{content}"
            if total_chars + len(entry) > 12000:
                break
            context_parts.append(entry)
            total_chars += len(entry)

        research_context = "\n\n---\n\n".join(context_parts)

        prompt = f"""Synthesize the following research results into a structured output.

PURPOSE: {purpose}

RESEARCH RESULTS:
{research_context}

OUTPUT FORMAT (respond with valid JSON matching this schema):
{output_schema}

Rules:
- Only include information supported by the research results.
- If information is uncertain, note confidence level.
- Omit fields you cannot fill rather than guessing.
- Respond with valid JSON only, no explanation."""

        try:
            llm = get_llm_provider()
            response = await llm.generate(
                messages=[
                    LLMMessage(
                        role="system",
                        content=(
                            "You are a research analyst. Synthesize raw research "
                            "into structured outputs. Respond with valid JSON only."
                        ),
                    ),
                    LLMMessage(role="user", content=prompt),
                ],
                temperature=0.2,
                max_tokens=max_tokens,
            )
            content = _strip_code_fences(response.content)
            return json.loads(content)
        except Exception as exc:
            logger.error(f"Research synthesis failed: {exc}")
            return {}

    async def summarize(
        self,
        raw_results: list[dict[str, Any]],
        purpose: str,
        *,
        max_words: int = 500,
    ) -> str:
        """Produce a prose summary from raw research results.

        Args:
            raw_results: List of raw research results.
            purpose: Context for the summary.
            max_words: Approximate max length.

        Returns:
            Summary string.
        """
        if not raw_results:
            return ""

        context_parts = []
        total_chars = 0
        for result in raw_results:
            content = result.get("content", "") or result.get("excerpt", "")
            title = result.get("title", "")
            entry = f"**{title}**\n{content}"
            if total_chars + len(entry) > 10000:
                break
            context_parts.append(entry)
            total_chars += len(entry)

        research_context = "\n\n---\n\n".join(context_parts)

        prompt = f"""Summarize the following research for this purpose: {purpose}

RESEARCH:
{research_context}

Write a concise summary (~{max_words} words). Focus on facts, not opinions.
Include specific numbers, dates, and names where available."""

        try:
            llm = get_llm_provider()
            response = await llm.generate(
                messages=[
                    LLMMessage(
                        role="system",
                        content=("You are a research analyst. " "Write concise factual summaries."),
                    ),
                    LLMMessage(role="user", content=prompt),
                ],
                temperature=0.2,
                max_tokens=max_words * 2,
            )
            return response.content.strip()
        except Exception as exc:
            logger.error(f"Research summarization failed: {exc}")
            return ""


research_synthesizer = ResearchSynthesizer()
