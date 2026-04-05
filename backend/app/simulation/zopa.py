"""ZOPA (Zone of Possible Agreement) analysis for negotiations."""

import json
import logging

from pydantic import BaseModel, Field

from app.llm.provider import LLMMessage, LLMProvider
from app.simulation.models import EnvironmentType, SimulationState

logger = logging.getLogger(__name__)


class AgentPosition(BaseModel):
    """Negotiation position for a single agent."""

    agent_id: str
    agent_name: str
    red_lines: list[str] = Field(default_factory=list)
    batna: str = ""  # Best Alternative to Negotiated Agreement
    current_position: str = ""
    flexibility_score: float = Field(default=0.5, ge=0.0, le=1.0)


class ConcessionRecommendation(BaseModel):
    """A recommendation for concessions to expand ZOPA."""

    agent_id: str
    agent_name: str
    concession: str
    impact_score: float = Field(..., ge=0.0, le=1.0)
    description: str = ""


class ZOPABoundaries(BaseModel):
    """ZOPA boundaries for the negotiation."""

    lower_bound: str = ""
    upper_bound: str = ""
    overlap_description: str = ""


class ZOPAResult(BaseModel):
    """Complete ZOPA analysis result."""

    positions: list[AgentPosition] = Field(default_factory=list)
    zopa_exists: bool = False
    zopa_boundaries: ZOPABoundaries | None = None
    concession_recommendations: list[ConcessionRecommendation] = Field(default_factory=list)
    no_deal_probability: float = Field(default=0.5, ge=0.0, le=1.0)
    analysis_summary: str = ""


class ZOPAAnalyzer:
    """Analyzer for Zone of Possible Agreement in negotiations.

    Analyzes agent messages in NEGOTIATION environments to extract
    positions, red lines, and BATNA, then computes the ZOPA.
    """

    def __init__(self, llm_provider: LLMProvider | None = None):
        """Initialize the ZOPA analyzer.

        Args:
            llm_provider: LLM provider for position extraction.
        """
        self.llm = llm_provider

    async def extract_positions(self, simulation_state: SimulationState) -> list[AgentPosition]:
        """Extract negotiation positions from agent messages.

        Analyzes agent messages to extract:
        - Red lines (non-negotiable positions)
        - BATNA (Best Alternative to Negotiated Agreement)
        - Current position/offer
        - Flexibility score

        Works with all environment types; uses LLM analysis for NEGOTIATION
        environments and heuristic analysis for others.

        Args:
            simulation_state: The simulation state.

        Returns:
            List of AgentPosition for each agent.
        """
        env = simulation_state.config.environment_type

        # LLM-based extraction only runs when env is NEGOTIATION and self.llm is set;
        # otherwise use heuristics: non-negotiation (env != EnvironmentType.NEGOTIATION)
        # or negotiation without an LLM (not self.llm).
        if env != EnvironmentType.NEGOTIATION or not self.llm:
            return self._extract_basic_positions(simulation_state)

        positions = []

        # Group messages by agent
        agent_messages: dict[str, list[str]] = {}
        for round_state in simulation_state.rounds:
            for msg in round_state.messages:
                if msg.agent_id not in agent_messages:
                    agent_messages[msg.agent_id] = []
                agent_messages[msg.agent_id].append(msg.content)

        # Extract position for each agent using LLM
        for agent in simulation_state.agents:
            messages = agent_messages.get(agent.id, [])
            if not messages:
                continue

            position = await self._extract_agent_position(agent.id, agent.name, messages)
            positions.append(position)

        return positions

    def _extract_basic_positions(self, simulation_state: SimulationState) -> list[AgentPosition]:
        """Extract basic positions without LLM.

        Uses heuristic extraction from message content.
        """
        positions = []

        for agent in simulation_state.agents:
            # Collect agent's messages
            agent_messages = []
            for round_state in simulation_state.rounds:
                for msg in round_state.messages:
                    if msg.agent_id == agent.id:
                        agent_messages.append(msg.content.lower())

            all_text = " ".join(agent_messages)

            # Heuristic red line detection — extract full sentence around keyword
            red_lines: list[str] = []
            seen_red_line_spans: set[str] = set()
            red_line_keywords = [
                "will not",
                "cannot accept",
                "non-negotiable",
                "deal breaker",
                "refuse",
            ]
            for keyword in red_line_keywords:
                if len(red_lines) >= 3:
                    break
                if keyword in all_text:
                    idx = all_text.find(keyword)
                    # Walk back to sentence start (period/newline)
                    start = max(0, idx - 150)
                    sent_start = all_text.rfind(".", start, idx)
                    start = (sent_start + 1) if sent_start >= start else start
                    # Walk forward to sentence end
                    end = min(len(all_text), idx + 200)
                    sent_end = all_text.find(".", idx, end)
                    end = (sent_end + 1) if sent_end > idx else end
                    candidate = all_text[start:end].strip()
                    if candidate and candidate not in seen_red_line_spans:
                        seen_red_line_spans.add(candidate)
                        red_lines.append(candidate)

            # Heuristic BATNA detection — extract full sentence around keyword
            batna = ""
            batna_keywords = [
                "alternative",
                "walk away",
                "backup",
                "other option",
                "without a deal",
            ]
            for keyword in batna_keywords:
                if keyword in all_text:
                    idx = all_text.find(keyword)
                    start = max(0, idx - 150)
                    sent_start = all_text.rfind(".", start, idx)
                    start = (sent_start + 1) if sent_start >= start else start
                    end = min(len(all_text), idx + 200)
                    sent_end = all_text.find(".", idx, end)
                    end = (sent_end + 1) if sent_end > idx else end
                    batna = all_text[start:end].strip()
                    break

            # Flexibility based on message count and stance
            flexibility = min(1.0, len(agent_messages) / 10)
            if "flexible" in all_text or "willing to" in all_text:
                flexibility = min(1.0, flexibility + 0.2)

            positions.append(
                AgentPosition(
                    agent_id=agent.id,
                    agent_name=agent.name,
                    red_lines=red_lines[:3],  # Limit to 3
                    batna=batna,
                    current_position=agent.current_stance,
                    flexibility_score=flexibility,
                )
            )

        return positions

    async def _extract_agent_position(
        self,
        agent_id: str,
        agent_name: str,
        messages: list[str],
    ) -> AgentPosition:
        """Extract position for a single agent using LLM."""
        prompt = f"""Analyze the following negotiation messages from {agent_name}
and extract their negotiation position.

MESSAGES:
{chr(10).join(f'- {m}' for m in messages[-10:])}

Extract and respond in JSON format:
{{
    "red_lines": ["list of non-negotiable positions or deal breakers"],
    "batna": "best alternative if no deal is reached",
    "current_position": "their current offer or stance",
    "flexibility_score": 0.0 to 1.0 (how flexible they seem)
}}

Respond with valid JSON only."""

        try:
            response = await self.llm.generate(
                messages=[
                    LLMMessage(
                        role="system",
                        content="You analyze negotiation positions. " "Respond with valid JSON only.",
                    ),
                    LLMMessage(role="user", content=prompt),
                ],
                temperature=0.3,
                max_tokens=500,
            )

            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            data = json.loads(content)

            return AgentPosition(
                agent_id=agent_id,
                agent_name=agent_name,
                red_lines=data.get("red_lines", []),
                batna=data.get("batna", ""),
                current_position=data.get("current_position", ""),
                flexibility_score=data.get("flexibility_score", 0.5),
            )

        except Exception as e:
            logger.error(f"Failed to extract position for {agent_name}: {e}")
            return AgentPosition(
                agent_id=agent_id,
                agent_name=agent_name,
                red_lines=[],
                batna="",
                current_position="",
                flexibility_score=0.5,
            )

    def compute_zopa(self, positions: list[AgentPosition]) -> tuple[bool, ZOPABoundaries | None]:
        """Compute the Zone of Possible Agreement.

        Finds the overlap zone across all parties' positions.

        Args:
            positions: List of agent positions.

        Returns:
            Tuple of (zopa_exists, zopa_boundaries).
        """
        if len(positions) < 2:
            return False, None

        # Analyze common ground
        all_positions = []
        for pos in positions:
            all_positions.append(
                {
                    "agent": pos.agent_name,
                    "flexibility": pos.flexibility_score,
                    "red_lines": pos.red_lines,
                }
            )

        # Check for contradictory red lines
        red_line_conflicts = 0
        for i, pos1 in enumerate(positions):
            for pos2 in positions[i + 1 :]:
                # Check if red lines directly conflict
                for rl1 in pos1.red_lines:
                    for rl2 in pos2.red_lines:
                        # Simple heuristic: check for opposing terms
                        if self._are_contradictory(rl1, rl2):
                            red_line_conflicts += 1

        # If many red line conflicts, ZOPA unlikely
        if red_line_conflicts >= len(positions):
            return False, None

        # Compute average flexibility as ZOPA indicator
        avg_flexibility = sum(p.flexibility_score for p in positions) / len(positions)

        # ZOPA exists if average flexibility is moderate to high
        zopa_exists = avg_flexibility > 0.3 and red_line_conflicts < len(positions)

        if zopa_exists:
            # Create synthetic ZOPA boundaries based on positions
            most_flexible = max(positions, key=lambda p: p.flexibility_score)
            least_flexible = min(positions, key=lambda p: p.flexibility_score)

            boundaries = ZOPABoundaries(
                lower_bound=f"Constrained by {least_flexible.agent_name}",
                upper_bound=f"Expanded by {most_flexible.agent_name}",
                overlap_description=(
                    f"Potential agreement zone exists with " f"{avg_flexibility:.0%} average flexibility"
                ),
            )
            return True, boundaries

        return False, None

    def _are_contradictory(self, text1: str, text2: str) -> bool:
        """Check if two texts contain contradictory positions."""
        # Simple heuristic check for common opposing terms
        opposing_pairs = [
            ("increase", "decrease"),
            ("raise", "lower"),
            ("more", "less"),
            ("higher", "lower"),
            ("accept", "reject"),
            ("yes", "no"),
            ("must", "cannot"),
            ("will", "will not"),
        ]

        text1_lower = text1.lower()
        text2_lower = text2.lower()

        for term1, term2 in opposing_pairs:
            if (term1 in text1_lower and term2 in text2_lower) or (term2 in text1_lower and term1 in text2_lower):
                return True

        return False

    async def recommend_concessions(
        self, positions: list[AgentPosition], zopa_exists: bool
    ) -> list[ConcessionRecommendation]:
        """Identify concessions that would expand ZOPA.

        Args:
            positions: List of agent positions.
            zopa_exists: Whether ZOPA currently exists.

        Returns:
            List of concession recommendations ranked by impact.
        """
        recommendations = []

        if not positions:
            return recommendations

        # Sort positions by flexibility (least flexible first)
        sorted_positions = sorted(positions, key=lambda p: p.flexibility_score)

        # Recommend concessions from least flexible agents
        for pos in sorted_positions:
            if pos.flexibility_score < 0.5:
                # Low flexibility agent - recommend opening up
                for red_line in pos.red_lines[:2]:
                    impact = 1.0 - pos.flexibility_score
                    recommendations.append(
                        ConcessionRecommendation(
                            agent_id=pos.agent_id,
                            agent_name=pos.agent_name,
                            concession=(f"Consider flexibility on: " f"{red_line[:200]}"),
                            impact_score=impact,
                            description=(
                                f"{pos.agent_name} has low flexibility. " "Softening this position could expand ZOPA."
                            ),
                        )
                    )

        # Sort by impact score
        recommendations.sort(key=lambda r: r.impact_score, reverse=True)
        return recommendations[:5]  # Top 5 recommendations

    def compute_no_deal_probability(self, positions: list[AgentPosition], zopa_exists: bool) -> float:
        """Compute probability of no deal.

        Args:
            positions: List of agent positions.
            zopa_exists: Whether ZOPA currently exists.

        Returns:
            Probability of no deal (0.0 to 1.0).
        """
        if not positions:
            return 0.5

        # Base probability from ZOPA existence
        base_prob = 0.2 if zopa_exists else 0.7

        # Adjust based on average flexibility
        avg_flexibility = sum(p.flexibility_score for p in positions) / len(positions)
        flexibility_adjustment = (1.0 - avg_flexibility) * 0.3

        # Adjust based on number of red lines
        total_red_lines = sum(len(p.red_lines) for p in positions)
        red_line_adjustment = min(0.2, total_red_lines * 0.02)

        probability = base_prob + flexibility_adjustment + red_line_adjustment
        return max(0.0, min(1.0, probability))

    async def analyze(self, simulation_state: SimulationState) -> ZOPAResult:
        """Perform complete ZOPA analysis.

        Args:
            simulation_state: The simulation state.

        Returns:
            Complete ZOPAResult with all analysis.
        """
        # Extract positions
        positions = await self.extract_positions(simulation_state)

        # Compute ZOPA
        zopa_exists, zopa_boundaries = self.compute_zopa(positions)

        # Generate recommendations
        recommendations = await self.recommend_concessions(positions, zopa_exists)

        # Compute no-deal probability
        no_deal_prob = self.compute_no_deal_probability(positions, zopa_exists)

        # Generate summary
        if zopa_exists:
            summary = f"ZOPA identified across {len(positions)} parties. " f"No-deal probability: {no_deal_prob:.0%}."
        else:
            summary = (
                f"No clear ZOPA found among {len(positions)} parties. "
                f"No-deal probability: {no_deal_prob:.0%}. "
                "Consider the recommended concessions."
            )

        return ZOPAResult(
            positions=positions,
            zopa_exists=zopa_exists,
            zopa_boundaries=zopa_boundaries,
            concession_recommendations=recommendations,
            no_deal_probability=no_deal_prob,
            analysis_summary=summary,
        )
