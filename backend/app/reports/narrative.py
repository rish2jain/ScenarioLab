"""Simulation narrative generator."""

import asyncio
import json
import logging
from typing import Any

from pydantic import BaseModel

from app.llm.provider import LLMMessage, LLMProvider
from app.simulation.objectives import format_simulation_objective_for_prompt

logger = logging.getLogger(__name__)


def _parse_llm_json(raw: str) -> Any:
    """Strip markdown JSON fences and parse JSON from LLM output."""
    s = raw.strip().removeprefix("```json").removesuffix("```").strip()
    return json.loads(s)


class SimulationNarrative(BaseModel):
    """Complete narrative summary of a simulation."""

    simulation_id: str
    executive_narrative: str  # <=2 paragraphs
    round_by_round_chronicle: list[dict]
    turning_points: list[dict]
    unexpected_outcomes: list[str]


class NarrativeGenerator:
    """Generates compelling narrative summaries of simulations."""

    def __init__(self, llm_provider: LLMProvider | None = None):
        self.llm = llm_provider

    async def generate_narrative(self, simulation_state) -> SimulationNarrative:
        """Generate compelling narrative summary.

        Args:
            simulation_state: The complete simulation state

        Returns:
            SimulationNarrative with generated content
        """
        if not simulation_state:
            return SimulationNarrative(
                simulation_id="",
                executive_narrative="No simulation data available.",
                round_by_round_chronicle=[],
                turning_points=[],
                unexpected_outcomes=[],
            )

        simulation_id = simulation_state.config.id

        # Run all four narrative sections in parallel — they are independent.
        (
            executive_narrative,
            round_chronicle,
            turning_points,
            unexpected_outcomes,
        ) = await asyncio.gather(
            self._generate_executive_narrative(simulation_state),
            self._generate_round_chronicle(simulation_state),
            self._identify_turning_points(simulation_state),
            self._identify_unexpected_outcomes(simulation_state),
        )

        return SimulationNarrative(
            simulation_id=simulation_id,
            executive_narrative=executive_narrative,
            round_by_round_chronicle=round_chronicle,
            turning_points=turning_points,
            unexpected_outcomes=unexpected_outcomes,
        )

    async def _generate_executive_narrative(self, simulation_state) -> str:
        """Generate executive summary (max 2 paragraphs)."""
        if not self.llm:
            return self._generate_basic_executive_summary(simulation_state)

        # Prepare simulation summary
        sim_summary = self._prepare_simulation_summary(simulation_state)

        prompt = f"""Write a compelling executive narrative (maximum 2 paragraphs) summarizing this strategic simulation.

SIMULATION OVERVIEW:
{sim_summary}

The narrative should:
- Capture the key dynamics and tensions
- Highlight surprising developments
- Summarize the overall arc and outcome
- Be written in an engaging, journalistic style

Write 1-2 paragraphs maximum."""

        try:
            response = await self.llm.generate(
                messages=[
                    LLMMessage(
                        role="system",
                        content=("You are a skilled narrative writer summarizing " "strategic war-game simulations."),
                    ),
                    LLMMessage(role="user", content=prompt),
                ],
                temperature=0.7,
                max_tokens=600,
            )

            return response.content.strip()

        except Exception as e:
            logger.error(f"Failed to generate executive narrative: {e}")
            return self._generate_basic_executive_summary(simulation_state)

    def _generate_basic_executive_summary(self, simulation_state) -> str:
        """Generate a basic executive summary without LLM."""
        agent_names = [a.name for a in simulation_state.agents]
        total_rounds = len(simulation_state.rounds)
        total_messages = sum(len(r.messages) for r in simulation_state.rounds)

        return (
            f"This {total_rounds}-round simulation featured "
            f"{len(agent_names)} participants: {', '.join(agent_names)}. "
            f"The simulation generated {total_messages} messages across all rounds, "
            f"exploring dynamics in a {simulation_state.config.environment_type.value} "
            f"environment. Key themes and decision points emerged through the "
            f"interaction of diverse stakeholder perspectives."
        )

    def _prepare_simulation_summary(self, simulation_state) -> str:
        """Prepare a text summary of the simulation."""
        lines = []

        lines.append(f"Simulation: {simulation_state.config.name}")
        desc = (simulation_state.config.description or "").strip()
        if desc:
            lines.append(f"User objective / description: {desc}")
        obj_block = format_simulation_objective_for_prompt(
            simulation_state.config.description,
            simulation_state.config.parameters,
        )
        if obj_block.strip():
            lines.append("")
            lines.append(obj_block)
        lines.append(f"Environment: {simulation_state.config.environment_type.value}")
        lines.append(f"Status: {simulation_state.status.value}")

        # Agent summary
        lines.append("\nParticipants:")
        for agent in simulation_state.agents:
            lines.append(f"- {agent.name} ({agent.archetype_id})")
            if agent.current_stance:
                lines.append(f"  Final stance: {agent.current_stance}")

        # Round summaries — include all messages with enough
        # content to preserve argument substance
        lines.append("\nRound Summaries:")
        for round_state in simulation_state.rounds:
            lines.append(f"\nRound {round_state.round_number}:")
            lines.append(f"  Phase: {round_state.phase}")
            lines.append(f"  Messages: {len(round_state.messages)}")

            for msg in round_state.messages:
                excerpt = msg.content[:300]
                if len(msg.content) > 300:
                    excerpt += "..."
                lines.append(f"  - {msg.agent_name} ({msg.agent_role}): " f"{excerpt}")

        return "\n".join(lines)

    async def _generate_round_chronicle(self, simulation_state) -> list[dict]:
        """Generate round-by-round narrative.

        Uses a single batched LLM call for all rounds instead of N
        sequential calls, producing more coherent cross-round narratives
        at a fraction of the cost.
        """
        rounds = simulation_state.rounds
        if not rounds:
            return []

        # Always extract key events (no LLM needed).
        events_by_round = {rs.round_number: self._extract_key_events(rs) for rs in rounds}

        if not self.llm:
            return [
                {
                    "round": rs.round_number,
                    "narrative": self._generate_basic_round_narrative(rs),
                    "key_events": events_by_round[rs.round_number],
                }
                for rs in rounds
            ]

        # Build a single prompt with all rounds.
        round_blocks = []
        for rs in rounds:
            msgs = "\n".join(f"{msg.agent_name}: {msg.content[:300]}" for msg in rs.messages[:5])
            round_blocks.append(f"--- ROUND {rs.round_number} ---\n{msgs}")

        prompt = (
            "Write a brief narrative summary (2-3 sentences) for EACH "
            "round below. Connect the narratives so they read as a "
            "coherent story arc.\n\n" + "\n\n".join(round_blocks) + "\n\nRespond with ONLY a JSON array: "
            '[{"round": N, "narrative": "..."}]'
        )

        try:
            response = await self.llm.generate(
                messages=[
                    LLMMessage(
                        role="system",
                        content="You summarize simulation rounds concisely. " "Respond with valid JSON only.",
                    ),
                    LLMMessage(role="user", content=prompt),
                ],
                temperature=0.6,
                max_tokens=200 * len(rounds) + 100,
            )
            parsed = _parse_llm_json(response.content)
            by_round: dict[int, str] = {int(e["round"]): e["narrative"] for e in parsed}
        except Exception as e:
            logger.error(f"Batched round narrative failed: {e}")
            by_round = {}

        chronicle = []
        for rs in rounds:
            narrative = by_round.get(
                rs.round_number,
                self._generate_basic_round_narrative(rs),
            )
            chronicle.append(
                {
                    "round": rs.round_number,
                    "narrative": narrative,
                    "key_events": events_by_round[rs.round_number],
                }
            )

        return chronicle

    def _generate_basic_round_narrative(self, round_state) -> str:
        """Generate basic round narrative without LLM."""
        message_count = len(round_state.messages)
        agent_names = list(set(msg.agent_name for msg in round_state.messages))

        return (
            f"Round {round_state.round_number} featured {message_count} "
            f"messages from {len(agent_names)} participants. "
            f"Key contributors: {', '.join(agent_names[:3])}."
        )

    def _extract_key_events(self, round_state) -> list[str]:
        """Extract key events from a round."""
        events = []

        for msg in round_state.messages:
            # Detect votes
            if msg.message_type == "vote":
                events.append(f"{msg.agent_name} cast a vote")

            # Detect decisions
            if msg.message_type == "decision":
                events.append(f"{msg.agent_name} made a decision")

            # Detect objections
            if msg.message_type == "objection":
                events.append(f"{msg.agent_name} raised an objection")

            # Detect coalition formations
            content_lower = msg.content.lower()
            if any(word in content_lower for word in ["agree", "support", "join"]):
                if "proposal" in content_lower or "plan" in content_lower:
                    events.append(f"{msg.agent_name} expressed support")

        # Limit to unique events
        return list(set(events))[:5]

    async def _identify_turning_points(self, simulation_state) -> list[dict]:
        """Identify key turning points in the simulation.

        When an LLM provider is available, skips the keyword pre-pass and
        goes straight to LLM analysis (more accurate, no duplication).
        Keyword heuristics are the fallback when no LLM is configured.
        """
        if not simulation_state.rounds:
            return []

        if self.llm and len(simulation_state.rounds) > 2:
            try:
                return await self._analyze_turning_points_with_llm(simulation_state)
            except Exception as e:
                logger.error(f"LLM turning points failed: {e}")
                # Fall through to keyword heuristics.

        return self._keyword_turning_points(simulation_state)

    @staticmethod
    def _keyword_turning_points(simulation_state) -> list[dict]:
        """Keyword-based turning point detection (fallback)."""
        turning_points: list[dict] = []
        prev_stances: dict[str, str] = {}
        for round_state in simulation_state.rounds:
            round_num = round_state.round_number
            for msg in round_state.messages:
                if msg.agent_id in prev_stances and len(msg.content) > 50:
                    content_lower = msg.content.lower()
                    if any(
                        w in content_lower
                        for w in (
                            "however",
                            "but",
                            "instead",
                            "changed",
                        )
                    ):
                        turning_points.append(
                            {
                                "round": round_num,
                                "description": f"{msg.agent_name} shifted position",
                                "significance": "major",
                            }
                        )
                prev_stances[msg.agent_id] = msg.content

        seen: set[tuple] = set()
        unique: list[dict] = []
        for pt in turning_points:
            key = (pt.get("round"), pt.get("description"))
            if key not in seen:
                seen.add(key)
                unique.append(pt)
        return unique[:5]

    async def _analyze_turning_points_with_llm(self, simulation_state) -> list[dict]:
        """Use LLM to identify turning points."""
        arc_summary = []
        for round_state in simulation_state.rounds:
            key_msgs = [f"{msg.agent_name} ({msg.agent_role}): " f"{msg.content[:300]}" for msg in round_state.messages]
            arc_summary.append(f"Round {round_state.round_number}:\n" + "\n".join(key_msgs))
        arc_text = "\n\n".join(arc_summary)

        prompt = (
            "Identify 2-3 major turning points where the direction or "
            "dynamics significantly changed.\n\n"
            f"SIMULATION ARC:\n{arc_text}\n\n"
            "Respond with ONLY valid JSON:\n"
            '[{"round": N, "description": "...", "significance": "major|minor"}]'
        )
        response = await self.llm.generate(
            messages=[
                LLMMessage(
                    role="system",
                    content="You identify turning points in simulations. " "Respond with valid JSON only.",
                ),
                LLMMessage(role="user", content=prompt),
            ],
            temperature=0.4,
            max_tokens=400,
        )
        return _parse_llm_json(response.content)[:5]

    async def _identify_unexpected_outcomes(self, simulation_state) -> list[str]:
        """Identify unexpected outcomes from the simulation.

        When an LLM provider is available, combines final-stance analysis
        with LLM insights in a single call (previously 2 separate paths).
        """
        # Keyword heuristics — always cheap to run.
        outcomes: list[str] = []
        for agent in simulation_state.agents:
            if not agent.current_stance:
                continue
            stance_lower = agent.current_stance.lower()
            aid = agent.archetype_id
            if aid == "cfo" and "risk" in stance_lower:
                if "acceptable" in stance_lower or "worth taking" in stance_lower:
                    outcomes.append(f"{agent.name} (CFO) unexpectedly supported a risky position")
            if aid == "ceo" and "cautious" in stance_lower:
                outcomes.append(f"{agent.name} (CEO) took a surprisingly cautious approach")
            if aid == "activist_investor" and "support" in stance_lower:
                outcomes.append(f"{agent.name} (Activist) supported management unexpectedly")

        # LLM enrichment — single call using final stances.
        if self.llm and simulation_state.rounds:
            try:
                stances_text = "\n".join(
                    f"{a.name} ({a.archetype_id}): {a.current_stance}" for a in simulation_state.agents
                )
                prompt = (
                    "Based on these final stances, identify unexpected "
                    "outcomes — things that were surprising given each "
                    "participant's role.\n\n"
                    f"FINAL STANCES:\n{stances_text}\n\n"
                    "Respond with ONLY a JSON array of strings:\n"
                    '["outcome 1", "outcome 2"]'
                )
                resp = await self.llm.generate(
                    messages=[
                        LLMMessage(
                            role="system",
                            content="You identify unexpected outcomes. " "Respond with valid JSON only.",
                        ),
                        LLMMessage(role="user", content=prompt),
                    ],
                    temperature=0.5,
                    max_tokens=300,
                )
                outcomes.extend(_parse_llm_json(resp.content))
            except Exception as e:
                logger.error(f"LLM unexpected outcomes failed: {e}")

        return list(set(outcomes))[:5]
