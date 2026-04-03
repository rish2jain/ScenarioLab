"""Automated playbook suggestion based on scenario description."""

import logging

from pydantic import BaseModel, Field

from app.llm.provider import LLMMessage, LLMProvider
from app.playbooks.manager import playbook_manager

logger = logging.getLogger(__name__)


class PlaybookSuggestion(BaseModel):
    """A suggested playbook with confidence and reasoning."""

    playbook_id: str
    playbook_name: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning: str
    pre_fill_suggestions: dict


class AutoTemplater:
    """Automatically suggests playbooks based on scenario descriptions."""

    def __init__(self, llm_provider: LLMProvider | None = None):
        self.llm = llm_provider

    async def suggest_playbook(
        self, scenario_description: str
    ) -> list[PlaybookSuggestion]:
        """Suggest most relevant playbook based on scenario description.

        Uses LLM semantic matching against playbook descriptions.

        Args:
            scenario_description: Description of the scenario

        Returns:
            List of PlaybookSuggestion ranked by confidence
        """
        if not self.llm:
            # Fallback to keyword matching
            return self._keyword_based_suggestion(scenario_description)

        # Get all available playbooks
        playbooks = playbook_manager.get_all_playbooks()

        if not playbooks:
            return []

        # Build playbook context for LLM
        playbook_context = []
        for pb in playbooks:
            playbook_context.append({
                "id": pb.id,
                "name": pb.name,
                "description": pb.description,
                "category": pb.category,
                "environment": pb.environment,
            })

        # Use LLM to rank playbooks
        prompt = f"""Given this scenario description, rank the most relevant playbooks.

SCENARIO DESCRIPTION:
{scenario_description}

AVAILABLE PLAYBOOKS:
{self._format_playbooks_for_prompt(playbook_context)}

Analyze the scenario and rank the top 3 most relevant playbooks.

Respond in this JSON format:
[
    {{
        "playbook_id": "id",
        "confidence": 0.0-1.0,
        "reasoning": "Why this playbook fits",
        "pre_fill_suggestions": {{
            "suggested_rounds": number,
            "key_considerations": ["point 1", "point 2"]
        }}
    }}
]

Respond with valid JSON only."""

        try:
            response = await self.llm.generate(
                messages=[
                    LLMMessage(
                        role="system",
                        content=(
                            "You match scenarios to simulation playbooks. "
                            "Respond with valid JSON only."
                        ),
                    ),
                    LLMMessage(role="user", content=prompt),
                ],
                temperature=0.3,
                max_tokens=800,
            )

            import json

            content = response.content.strip()
            # Remove markdown code blocks if present
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            rankings = json.loads(content)

            # Build suggestions from rankings
            suggestions = []
            for ranking in rankings:
                pb_id = ranking.get("playbook_id")
                # Find playbook details
                pb = next((p for p in playbooks if p.id == pb_id), None)
                if pb:
                    suggestions.append(PlaybookSuggestion(
                        playbook_id=pb_id,
                        playbook_name=pb.name,
                        confidence=ranking.get("confidence", 0.5),
                        reasoning=ranking.get("reasoning", ""),
                        pre_fill_suggestions=ranking.get("pre_fill_suggestions", {}),
                    ))

            # Sort by confidence descending
            suggestions.sort(key=lambda x: x.confidence, reverse=True)

            return suggestions

        except Exception as e:
            logger.error(f"Failed to suggest playbooks with LLM: {e}")
            return self._keyword_based_suggestion(scenario_description)

    def _format_playbooks_for_prompt(self, playbooks: list[dict]) -> str:
        """Format playbooks for LLM prompt."""
        lines = []
        for pb in playbooks:
            lines.append(f"\nID: {pb['id']}")
            lines.append(f"Name: {pb['name']}")
            lines.append(f"Category: {pb['category']}")
            lines.append(f"Environment: {pb['environment']}")
            lines.append(f"Description: {pb['description']}")
        return "\n".join(lines)

    def _keyword_based_suggestion(
        self, scenario_description: str
    ) -> list[PlaybookSuggestion]:
        """Fallback keyword-based suggestion without LLM."""
        desc_lower = scenario_description.lower()

        # Keyword mappings
        keyword_playbook_map = {
            "board": ["boardroom-rehearsal"],
            "director": ["boardroom-rehearsal"],
            "governance": ["boardroom-rehearsal"],
            "regulator": ["regulatory-shock-test"],
            "compliance": ["regulatory-shock-test"],
            "regulation": ["regulatory-shock-test"],
            "competitor": ["competitive-response"],
            "competition": ["competitive-response"],
            "market": ["competitive-response"],
            "merger": ["mna-culture-clash"],
            "acquisition": ["mna-culture-clash"],
            "integration": ["mna-culture-clash"],
            "culture": ["mna-culture-clash"],
        }

        # Score playbooks by keyword matches
        scores = {}
        for keyword, playbook_ids in keyword_playbook_map.items():
            if keyword in desc_lower:
                for pb_id in playbook_ids:
                    scores[pb_id] = scores.get(pb_id, 0) + 1

        # Get playbook details
        suggestions = []
        for pb_id, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
            pb = playbook_manager.get_playbook(pb_id)
            if pb:
                confidence = min(0.9, 0.5 + score * 0.15)
                suggestions.append(PlaybookSuggestion(
                    playbook_id=pb_id,
                    playbook_name=pb.name,
                    confidence=confidence,
                    reasoning=f"Matched keywords related to {pb.category}",
                    pre_fill_suggestions={
                        "suggested_rounds": pb.typical_duration_rounds[0],
                    },
                ))

        return suggestions[:3]
