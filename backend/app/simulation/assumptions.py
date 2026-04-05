"""Assumption register with evidence tracing for simulations."""

import logging
import uuid

from pydantic import BaseModel, Field

from app.llm.provider import LLMMessage, LLMProvider

logger = logging.getLogger(__name__)


class Assumption(BaseModel):
    """A single assumption in the simulation."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    description: str
    value: str  # The assumed value
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence: list[str]  # Links to evidence sources
    sensitivity_score: float = Field(..., ge=0.0, le=1.0)
    # "agent_behavior", "market_condition", "organizational", "external"
    category: str
    # "seed_material", "archetype_default", "user_configured"
    source: str
    high_sensitivity: bool = False


class AssumptionRegister(BaseModel):
    """Register of all assumptions in a simulation."""

    simulation_id: str
    assumptions: list[Assumption]
    high_sensitivity_count: int = 0


class AssumptionTracker:
    """Tracks and analyzes assumptions in simulations."""

    def __init__(self, llm_provider: LLMProvider | None = None):
        self.llm = llm_provider

    async def extract_assumptions(self, simulation_config, simulation_state) -> AssumptionRegister:
        """Extract all assumptions from simulation config and state.

        Args:
            simulation_config: The simulation configuration
            simulation_state: The current simulation state

        Returns:
            AssumptionRegister with all extracted assumptions
        """
        assumptions: list[Assumption] = []

        if not simulation_config:
            return AssumptionRegister(
                simulation_id="",
                assumptions=[],
                high_sensitivity_count=0,
            )

        simulation_id = simulation_config.id

        # Extract agent initialization assumptions
        for agent_config in simulation_config.agents:
            # Archetype selection assumption
            desc = f"Agent {agent_config.name} follows {agent_config.archetype_id} archetype"
            assumptions.append(
                Assumption(
                    description=desc,
                    value=agent_config.archetype_id,
                    confidence=0.8,
                    evidence=["archetype_definition"],
                    sensitivity_score=0.6,
                    category="agent_behavior",
                    source="archetype_default",
                )
            )

            # Customization assumptions
            if agent_config.customization:
                for key, value in agent_config.customization.items():
                    desc = f"Agent {agent_config.name} customization: {key}"
                    assumptions.append(
                        Assumption(
                            description=desc,
                            value=str(value),
                            confidence=0.7,
                            evidence=["user_configuration"],
                            sensitivity_score=0.5,
                            category="agent_behavior",
                            source="user_configured",
                        )
                    )

        # Extract environment assumptions
        assumptions.append(
            Assumption(
                description="Simulation environment type",
                value=simulation_config.environment_type.value,
                confidence=0.9,
                evidence=["configuration"],
                sensitivity_score=0.7,
                category="organizational",
                source="user_configured",
            )
        )

        assumptions.append(
            Assumption(
                description="Total number of rounds",
                value=str(simulation_config.total_rounds),
                confidence=0.95,
                evidence=["configuration"],
                sensitivity_score=0.4,
                category="organizational",
                source="user_configured",
            )
        )

        # Extract seed material assumptions
        if simulation_config.seed_id:
            assumptions.append(
                Assumption(
                    description="Seed material provides accurate context",
                    value=simulation_config.seed_id,
                    confidence=0.75,
                    evidence=["seed_material"],
                    sensitivity_score=0.8,
                    category="external",
                    source="seed_material",
                    high_sensitivity=True,
                )
            )

        # Extract playbook assumptions
        if simulation_config.playbook_id:
            desc = f"Playbook {simulation_config.playbook_id} is appropriate"
            assumptions.append(
                Assumption(
                    description=desc,
                    value=simulation_config.playbook_id,
                    confidence=0.7,
                    evidence=["playbook_selection"],
                    sensitivity_score=0.6,
                    category="organizational",
                    source="user_configured",
                )
            )

        # Compute sensitivity for all assumptions
        for assumption in assumptions:
            assumption.sensitivity_score = await self._estimate_sensitivity(assumption, simulation_config)
            assumption.high_sensitivity = assumption.sensitivity_score > 0.7

        high_sensitivity_count = sum(1 for a in assumptions if a.high_sensitivity)

        return AssumptionRegister(
            simulation_id=simulation_id,
            assumptions=assumptions,
            high_sensitivity_count=high_sensitivity_count,
        )

    async def _estimate_sensitivity(self, assumption: Assumption, simulation_config) -> float:
        """Estimate sensitivity score for an assumption.

        Uses heuristic rules based on assumption category and content.

        Args:
            assumption: The assumption to analyze
            simulation_config: The simulation configuration

        Returns:
            Sensitivity score between 0.0 and 1.0
        """
        # Base sensitivity by category
        category_base = {
            "agent_behavior": 0.6,
            "market_condition": 0.8,
            "organizational": 0.5,
            "external": 0.7,
        }

        base = category_base.get(assumption.category, 0.5)

        # Adjust based on source
        source_multiplier = {
            "seed_material": 1.2,
            "archetype_default": 1.0,
            "user_configured": 0.9,
        }

        multiplier = source_multiplier.get(assumption.source, 1.0)

        # Adjust based on description keywords
        description_lower = assumption.description.lower()
        acc_words = ["accurate", "correct"]
        if any(word in description_lower for word in acc_words):
            multiplier *= 1.1
        cust_words = ["customization", "override"]
        if any(word in description_lower for word in cust_words):
            multiplier *= 0.9

        # Cap at 1.0
        return min(1.0, base * multiplier)

    async def compute_sensitivity(
        self,
        assumption: Assumption,
        simulation_engine,
        config,
    ) -> float:
        """Compute sensitivity considering what would change if assumption changes.

        Args:
            assumption: The assumption to analyze
            simulation_engine: The simulation engine instance
            config: The simulation configuration

        Returns:
            Sensitivity score between 0.0 and 1.0
        """
        # Use the heuristic-based estimate
        return await self._estimate_sensitivity(assumption, config)

    async def what_if_analysis(
        self,
        assumption_id: str,
        new_value: str,
        register: AssumptionRegister,
    ) -> dict:
        """Answer 'What if we're wrong about X?' queries.

        Args:
            assumption_id: ID of the assumption to analyze
            new_value: Hypothetical new value for the assumption
            register: The assumption register

        Returns:
            Dictionary with impact analysis
        """
        # Find the assumption
        assumption = None
        for a in register.assumptions:
            if a.id == assumption_id:
                assumption = a
                break

        if not assumption:
            return {
                "error": f"Assumption {assumption_id} not found",
                "impact": "unknown",
                "affected_agents": [],
                "scenario_changes": [],
            }

        if not self.llm:
            # Basic analysis without LLM
            return {
                "assumption_id": assumption_id,
                "original_value": assumption.value,
                "new_value": new_value,
                "impact": ("moderate" if assumption.sensitivity_score > 0.5 else "low"),
                "affected_agents": [],
                "scenario_changes": [f"{assumption.description} would change"],
                "confidence": 0.5,
            }

        # Use LLM for richer analysis
        try:
            prompt = f"""Analyze the impact of changing an assumption in a
strategic simulation.

ASSUMPTION:
- Description: {assumption.description}
- Current Value: {assumption.value}
- Hypothetical Value: {new_value}
- Category: {assumption.category}
- Sensitivity Score: {assumption.sensitivity_score:.2f}

Provide an analysis of what would change if this assumption were different.

Respond in this JSON format:
{{
    "impact": "high|moderate|low",
    "affected_agents": ["agent names or roles that would be affected"],
    "scenario_changes": ["specific changes to the scenario"],
    "reasoning": "explanation of the impact",
    "recommendation": "whether to validate this assumption"
}}"""

            response = await self.llm.generate(
                messages=[
                    LLMMessage(
                        role="system",
                        content=(
                            "You analyze the impact of assumption changes "
                            "in strategic simulations. "
                            "Respond with valid JSON only."
                        ),
                    ),
                    LLMMessage(role="user", content=prompt),
                ],
                temperature=0.3,
                max_tokens=600,
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

            analysis = json.loads(content)

            return {
                "assumption_id": assumption_id,
                "original_value": assumption.value,
                "new_value": new_value,
                "impact": analysis.get("impact", "unknown"),
                "affected_agents": analysis.get("affected_agents", []),
                "scenario_changes": analysis.get("scenario_changes", []),
                "reasoning": analysis.get("reasoning", ""),
                "recommendation": analysis.get("recommendation", ""),
                "confidence": 0.7,
            }

        except Exception as e:
            logger.error(f"Failed to perform what-if analysis: {e}")
            return {
                "assumption_id": assumption_id,
                "original_value": assumption.value,
                "new_value": new_value,
                "impact": "unknown",
                "affected_agents": [],
                "scenario_changes": [],
                "error": str(e),
                "confidence": 0.0,
            }
