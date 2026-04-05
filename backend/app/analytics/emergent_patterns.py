"""Emergent pattern detection for agent behavior divergence."""

import logging
import uuid

from pydantic import BaseModel, Field

from app.llm.provider import LLMMessage, LLMProvider

logger = logging.getLogger(__name__)


class EmergentBehavior(BaseModel):
    """A detected emergent behavior deviation from archetype baseline."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str
    agent_name: str
    archetype_id: str
    round_number: int
    deviation_type: str  # "stance_shift", "coalition_break",
    # "risk_profile_change", "unexpected_vote"
    description: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    causal_explanation: str
    baseline_behavior: str
    observed_behavior: str


class EmergentBehaviorsRegister(BaseModel):
    """Register of all emergent behaviors detected in a simulation."""

    simulation_id: str
    behaviors: list[EmergentBehavior]
    detection_rate: float = Field(..., ge=0.0, le=1.0)


class EmergentPatternDetector:
    """Detects agent behavior divergence from archetype baseline."""

    def __init__(self, llm_provider: LLMProvider | None = None):
        self.llm = llm_provider

    async def detect_patterns(self, simulation_state, archetypes: dict) -> EmergentBehaviorsRegister:
        """Analyze simulation for archetype deviations.

        Args:
            simulation_state: The current simulation state
            archetypes: Dictionary mapping archetype_id to ArchetypeDefinition

        Returns:
            EmergentBehaviorsRegister with detected deviations
        """
        behaviors: list[EmergentBehavior] = []

        if not simulation_state or not simulation_state.agents:
            sim_id = simulation_state.config.id if simulation_state else ""
            return EmergentBehaviorsRegister(
                simulation_id=sim_id,
                behaviors=[],
                detection_rate=0.0,
            )

        simulation_id = simulation_state.config.id

        # Analyze each agent's behavior against their archetype
        for agent_state in simulation_state.agents:
            archetype = archetypes.get(agent_state.archetype_id)
            if not archetype:
                continue

            # Detect stance shifts
            stance_deviation = await self._detect_stance_shift(agent_state, archetype, simulation_state)
            if stance_deviation:
                behaviors.append(stance_deviation)

            # Detect coalition breaks
            coalition_deviation = await self._detect_coalition_break(agent_state, archetype, simulation_state)
            if coalition_deviation:
                behaviors.append(coalition_deviation)

            # Detect unexpected votes
            vote_deviation = await self._detect_unexpected_vote(agent_state, archetype, simulation_state)
            if vote_deviation:
                behaviors.append(vote_deviation)

            # Detect risk profile changes
            risk_deviation = await self._detect_risk_profile_change(agent_state, archetype, simulation_state)
            if risk_deviation:
                behaviors.append(risk_deviation)

        # Calculate detection rate
        total_agents = len(simulation_state.agents)
        agents_with_deviations = len(set(b.agent_id for b in behaviors))
        detection_rate = agents_with_deviations / total_agents if total_agents > 0 else 0.0

        return EmergentBehaviorsRegister(
            simulation_id=simulation_id,
            behaviors=behaviors,
            detection_rate=detection_rate,
        )

    async def _detect_stance_shift(self, agent_state, archetype, simulation_state) -> EmergentBehavior | None:
        """Detect if agent's stance diverges from archetype expectations."""
        # Get agent's messages across rounds
        agent_messages = []
        for round_state in simulation_state.rounds:
            for msg in round_state.messages:
                if msg.agent_id == agent_state.id:
                    agent_messages.append(msg)

        if len(agent_messages) < 3:
            return None

        # Check for significant stance changes using LLM
        if self.llm:
            try:
                stance_analysis = await self._analyze_stance_consistency(agent_state, archetype, agent_messages)
                if stance_analysis.get("significant_deviation", False):
                    return EmergentBehavior(
                        agent_id=agent_state.id,
                        agent_name=agent_state.name,
                        archetype_id=agent_state.archetype_id,
                        round_number=simulation_state.current_round,
                        deviation_type="stance_shift",
                        description=stance_analysis.get("description", "Stance deviation detected"),
                        confidence=stance_analysis.get("confidence", 0.5),
                        causal_explanation=stance_analysis.get("explanation", "Unknown cause"),
                        baseline_behavior=(
                            archetype.behavioral_axioms[0]
                            if archetype.behavioral_axioms
                            else "Expected archetype behavior"
                        ),
                        observed_behavior=stance_analysis.get("observed", "Inconsistent stance"),
                    )
            except Exception as e:
                logger.error(f"Error analyzing stance for {agent_state.name}: {e}")

        return None

    async def _analyze_stance_consistency(self, agent_state, archetype, messages) -> dict:
        """Use LLM to analyze stance consistency."""
        message_texts = [f"Round {msg.round_number}: {msg.content}" for msg in messages[-5:]]
        conversation = "\n".join(message_texts)

        behavioral_axioms = "\n".join([f"- {axiom}" for axiom in archetype.behavioral_axioms])

        prompt = f"""Analyze whether this agent's statements show a
significant deviation from their expected behavioral pattern.

AGENT: {agent_state.name} ({archetype.role})
BEHAVIORAL AXIOMS:
{behavioral_axioms}

RECENT STATEMENTS:
{conversation}

Analyze and respond in this JSON format:
{{
    "significant_deviation": true/false,
    "confidence": 0.0-1.0,
    "description": "Brief description of the deviation",
    "explanation": "Why this deviation occurred based on conversation context",
    "observed": "What the agent actually did/said"
}}"""

        response = await self.llm.generate(
            messages=[
                LLMMessage(
                    role="system",
                    content=(
                        "You analyze agent behavior for deviations from "
                        "expected patterns. Respond with valid JSON only."
                    ),
                ),
                LLMMessage(role="user", content=prompt),
            ],
            temperature=0.3,
            max_tokens=500,
        )

        try:
            import json

            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            return json.loads(content)
        except Exception as e:
            logger.error(f"Failed to parse stance analysis: {e}")
            return {"significant_deviation": False, "confidence": 0.0}

    async def _detect_coalition_break(self, agent_state, archetype, simulation_state) -> EmergentBehavior | None:
        """Detect if agent broke expected coalition patterns."""
        # Check if agent was in a coalition and left
        no_coalition = not agent_state.coalition_members
        high_tendency = archetype.coalition_tendencies > 0.7
        if no_coalition and high_tendency:
            # High coalition tendency but no coalition - potential break
            # Look for evidence of coalition break in messages
            for round_state in simulation_state.rounds:
                for msg in round_state.messages:
                    if msg.agent_id == agent_state.id:
                        content_lower = msg.content.lower()
                        break_words = ["alone", "independent", "disagree", "oppose"]
                        if any(word in content_lower for word in break_words):
                            return EmergentBehavior(
                                agent_id=agent_state.id,
                                agent_name=agent_state.name,
                                archetype_id=agent_state.archetype_id,
                                round_number=round_state.round_number,
                                deviation_type="coalition_break",
                                description=(
                                    f"{agent_state.name} acted independently " "despite high coalition tendency"
                                ),
                                confidence=0.6,
                                causal_explanation=("Agent chose independent action over " "coalition alignment"),
                                baseline_behavior=(
                                    "Expected to form coalitions (tendency: " f"{archetype.coalition_tendencies})"
                                ),
                                observed_behavior=("Acted independently without coalition " "support"),
                            )
        return None

    async def _detect_unexpected_vote(self, agent_state, archetype, simulation_state) -> EmergentBehavior | None:
        """Detect votes that contradict archetype expectations."""
        for vote_record in agent_state.vote_history:
            vote = vote_record.get("vote", "")
            reasoning = vote_record.get("reasoning", "")

            # Check for unexpected votes based on archetype
            unexpected = False
            is_conservative = archetype.risk_tolerance.value == "conservative"
            is_aggressive = archetype.risk_tolerance.value == "aggressive"
            if is_conservative and vote == "for":
                # Conservative archetype voting for - check if risky
                risk_words = ["risky", "aggressive", "uncertain"]
                if any(word in reasoning.lower() for word in risk_words):
                    unexpected = True
            elif is_aggressive and vote == "against":
                # Aggressive archetype voting against - check if opportunity
                opp_words = ["opportunity", "growth", "advantage"]
                if any(word in reasoning.lower() for word in opp_words):
                    unexpected = True

            if unexpected:
                return EmergentBehavior(
                    agent_id=agent_state.id,
                    agent_name=agent_state.name,
                    archetype_id=agent_state.archetype_id,
                    round_number=vote_record.get("round_number", 0),
                    deviation_type="unexpected_vote",
                    description=(f"Unexpected {vote} vote from " f"{archetype.risk_tolerance.value} archetype"),
                    confidence=0.7,
                    causal_explanation=("Vote contradicts typical " f"{archetype.risk_tolerance.value} risk tolerance"),
                    baseline_behavior=(
                        "Expected voting pattern aligned with " f"{archetype.risk_tolerance.value} risk tolerance"
                    ),
                    observed_behavior=(f"Voted '{vote}' with reasoning: {reasoning[:100]}..."),
                )
        return None

    async def _detect_risk_profile_change(self, agent_state, archetype, simulation_state) -> EmergentBehavior | None:
        """Detect changes in risk tolerance over time."""
        # Analyze messages for risk-related language shifts
        early_messages = []
        late_messages = []

        mid_point = len(simulation_state.rounds) // 2
        for i, round_state in enumerate(simulation_state.rounds):
            for msg in round_state.messages:
                if msg.agent_id == agent_state.id:
                    if i < mid_point:
                        early_messages.append(msg.content)
                    else:
                        late_messages.append(msg.content)

        if not early_messages or not late_messages:
            return None

        # Simple heuristic: count risk-related words
        risk_words = ["risk", "safe", "conservative", "cautious", "dangerous"]
        opportunity_words = ["opportunity", "growth", "aggressive", "bold", "innovative"]

        early_risk_score = sum(1 for msg in early_messages for word in risk_words if word in msg.lower())
        early_opportunity_score = sum(1 for msg in early_messages for word in opportunity_words if word in msg.lower())

        late_risk_score = sum(1 for msg in late_messages for word in risk_words if word in msg.lower())
        late_opportunity_score = sum(1 for msg in late_messages for word in opportunity_words if word in msg.lower())

        # Detect significant shift
        if archetype.risk_tolerance.value == "conservative":
            if late_opportunity_score > early_opportunity_score * 2:
                return EmergentBehavior(
                    agent_id=agent_state.id,
                    agent_name=agent_state.name,
                    archetype_id=agent_state.archetype_id,
                    round_number=simulation_state.current_round,
                    deviation_type="risk_profile_change",
                    description=(f"{agent_state.name} shifted toward more " "aggressive/opportunistic language"),
                    confidence=min(0.8, 0.5 + (late_opportunity_score - early_opportunity_score) * 0.1),
                    causal_explanation=("Risk tolerance appears to have increased " "during simulation"),
                    baseline_behavior=(
                        f"Conservative risk tolerance (early: {early_risk_score} "
                        f"risk words vs {early_opportunity_score} opportunity)"
                    ),
                    observed_behavior=(
                        f"More aggressive posture (late: {late_risk_score} "
                        f"risk words vs {late_opportunity_score} opportunity)"
                    ),
                )
        elif archetype.risk_tolerance.value == "aggressive":
            if late_risk_score > early_risk_score * 2:
                return EmergentBehavior(
                    agent_id=agent_state.id,
                    agent_name=agent_state.name,
                    archetype_id=agent_state.archetype_id,
                    round_number=simulation_state.current_round,
                    deviation_type="risk_profile_change",
                    description=(f"{agent_state.name} shifted toward more " "cautious/risk-averse language"),
                    confidence=min(0.8, 0.5 + (late_risk_score - early_risk_score) * 0.1),
                    causal_explanation=("Risk tolerance appears to have decreased " "during simulation"),
                    baseline_behavior=(
                        f"Aggressive risk tolerance (early: {early_risk_score} "
                        f"risk words vs {early_opportunity_score} opportunity)"
                    ),
                    observed_behavior=(
                        f"More cautious posture (late: {late_risk_score} "
                        f"risk words vs {late_opportunity_score} opportunity)"
                    ),
                )

        return None
