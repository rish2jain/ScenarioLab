"""AI-assisted seed material structuring."""

import logging

from pydantic import BaseModel

from app.llm.provider import LLMMessage, LLMProvider

logger = logging.getLogger(__name__)


class CopilotSuggestions(BaseModel):
    """Suggestions from the Playbook Copilot."""

    suggested_playbook: str | None
    suggested_agents: list[dict]
    key_entities: list[str]
    recommended_parameters: dict
    missing_information: list[str]
    structured_seed: dict


class PlaybookCopilot:
    """AI assistant for analyzing seed material and suggesting configurations."""

    def __init__(self, llm_provider: LLMProvider | None = None):
        self.llm = llm_provider

    async def analyze_seed(self, seed_content: str) -> CopilotSuggestions:
        """Analyze seed material and suggest simulation configuration.

        Args:
            seed_content: Raw seed material content

        Returns:
            CopilotSuggestions with recommendations
        """
        if not self.llm:
            return self._basic_analysis(seed_content)

        prompt = f"""Analyze this seed material and suggest simulation configuration.

SEED MATERIAL:
{seed_content[:3000]}  # Limit content length

Provide analysis in this JSON format:
{{
    "suggested_playbook": "playbook_id or null",
    "suggested_agents": [
        {{
            "role": "Role name",
            "archetype_id": "archetype_id",
            "rationale": "Why this agent fits"
        }}
    ],
    "key_entities": ["entity1", "entity2"],
    "recommended_parameters": {{
        "total_rounds": number,
        "environment_type": "boardroom|war_room|negotiation|integration"
    }},
    "missing_information": ["What else would be helpful"],
    "structured_seed": {{
        "title": "Extracted title",
        "context": "Main context",
        "stakeholders": ["stakeholder1", "stakeholder2"],
        "key_issues": ["issue1", "issue2"]
    }}
}}

Respond with valid JSON only."""

        try:
            response = await self.llm.generate(
                messages=[
                    LLMMessage(
                        role="system",
                        content=(
                            "You analyze seed materials for strategic simulations. "
                            "Respond with valid JSON only."
                        ),
                    ),
                    LLMMessage(role="user", content=prompt),
                ],
                temperature=0.4,
                max_tokens=1000,
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

            data = json.loads(content)

            return CopilotSuggestions(
                suggested_playbook=data.get("suggested_playbook"),
                suggested_agents=data.get("suggested_agents", []),
                key_entities=data.get("key_entities", []),
                recommended_parameters=data.get("recommended_parameters", {}),
                missing_information=data.get("missing_information", []),
                structured_seed=data.get("structured_seed", {}),
            )

        except Exception as e:
            logger.error(f"Failed to analyze seed with LLM: {e}")
            return self._basic_analysis(seed_content)

    def _basic_analysis(self, seed_content: str) -> CopilotSuggestions:
        """Basic analysis without LLM."""
        content_lower = seed_content.lower()

        # Simple keyword-based suggestions
        suggested_playbook = None
        if any(word in content_lower for word in ["board", "director", "governance"]):
            suggested_playbook = "boardroom-rehearsal"
        elif any(word in content_lower for word in ["regulator", "compliance"]):
            suggested_playbook = "regulatory-shock-test"
        elif any(word in content_lower for word in ["competitor", "market", "competition"]):
            suggested_playbook = "competitive-response"
        elif any(word in content_lower for word in ["merger", "acquisition", "integration"]):
            suggested_playbook = "mna-culture-clash"

        # Extract potential entities (capitalized words)
        import re
        potential_entities = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', seed_content)
        key_entities = list(set(potential_entities))[:10]

        return CopilotSuggestions(
            suggested_playbook=suggested_playbook,
            suggested_agents=[],
            key_entities=key_entities,
            recommended_parameters={},
            missing_information=["Detailed stakeholder information"],
            structured_seed={
                "title": "Extracted from seed",
                "context": seed_content[:200],
            },
        )

    async def refine_with_feedback(
        self,
        suggestions: CopilotSuggestions,
        feedback: str,
    ) -> CopilotSuggestions:
        """Refine suggestions based on user feedback.

        Args:
            suggestions: Original suggestions
            feedback: User feedback

        Returns:
            Refined CopilotSuggestions
        """
        if not self.llm:
            return suggestions

        prompt = f"""Refine these simulation suggestions based on user feedback.

ORIGINAL SUGGESTIONS:
- Playbook: {suggestions.suggested_playbook}
- Agents: {suggestions.suggested_agents}
- Parameters: {suggestions.recommended_parameters}

USER FEEDBACK:
{feedback}

Provide refined suggestions in the same JSON format as before.

Respond with valid JSON only."""

        try:
            response = await self.llm.generate(
                messages=[
                    LLMMessage(
                        role="system",
                        content="You refine simulation suggestions based on feedback. "
                                "Respond with valid JSON only.",
                    ),
                    LLMMessage(role="user", content=prompt),
                ],
                temperature=0.4,
                max_tokens=800,
            )

            import json

            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            data = json.loads(content)

            return CopilotSuggestions(
                suggested_playbook=data.get("suggested_playbook"),
                suggested_agents=data.get("suggested_agents", []),
                key_entities=data.get("key_entities", []),
                recommended_parameters=data.get("recommended_parameters", {}),
                missing_information=data.get("missing_information", []),
                structured_seed=data.get("structured_seed", {}),
            )

        except Exception as e:
            logger.error(f"Failed to refine suggestions: {e}")
            return suggestions
