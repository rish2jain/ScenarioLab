"""Simulation narrative generator."""

import logging

from pydantic import BaseModel

from app.llm.provider import LLMMessage, LLMProvider
from app.simulation.objectives import format_simulation_objective_for_prompt

logger = logging.getLogger(__name__)


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

    async def generate_narrative(
        self, simulation_state
    ) -> SimulationNarrative:
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

        # Generate executive narrative
        executive_narrative = await self._generate_executive_narrative(
            simulation_state
        )

        # Generate round-by-round chronicle
        round_chronicle = await self._generate_round_chronicle(simulation_state)

        # Identify turning points
        turning_points = await self._identify_turning_points(simulation_state)

        # Identify unexpected outcomes
        unexpected_outcomes = await self._identify_unexpected_outcomes(
            simulation_state
        )

        return SimulationNarrative(
            simulation_id=simulation_id,
            executive_narrative=executive_narrative,
            round_by_round_chronicle=round_chronicle,
            turning_points=turning_points,
            unexpected_outcomes=unexpected_outcomes,
        )

    async def _generate_executive_narrative(
        self, simulation_state
    ) -> str:
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
                        content=(
                            "You are a skilled narrative writer summarizing "
                            "strategic war-game simulations."
                        ),
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
                lines.append(
                    f"  - {msg.agent_name} ({msg.agent_role}): "
                    f"{excerpt}"
                )

        return "\n".join(lines)

    async def _generate_round_chronicle(
        self, simulation_state
    ) -> list[dict]:
        """Generate round-by-round narrative."""
        chronicle = []

        for round_state in simulation_state.rounds:
            round_num = round_state.round_number

            if self.llm:
                try:
                    round_narrative = await self._generate_round_narrative(
                        round_state, simulation_state
                    )
                except Exception as e:
                    logger.error(f"Failed to generate round narrative: {e}")
                    round_narrative = self._generate_basic_round_narrative(
                        round_state
                    )
            else:
                round_narrative = self._generate_basic_round_narrative(
                    round_state
                )

            # Extract key events
            key_events = self._extract_key_events(round_state)

            chronicle.append({
                "round": round_num,
                "narrative": round_narrative,
                "key_events": key_events,
            })

        return chronicle

    async def _generate_round_narrative(
        self, round_state, simulation_state
    ) -> str:
        """Generate narrative for a single round using LLM."""
        # Prepare round content
        messages_text = "\n".join([
            f"{msg.agent_name}: {msg.content}"
            for msg in round_state.messages[:5]
        ])

        prompt = f"""Write a brief narrative summary (2-3 sentences) of Round {round_state.round_number}.

MESSAGES:
{messages_text}

Summarize the key developments and dynamics in 2-3 sentences."""

        response = await self.llm.generate(
            messages=[
                LLMMessage(
                    role="system",
                    content="You summarize simulation rounds concisely.",
                ),
                LLMMessage(role="user", content=prompt),
            ],
            temperature=0.6,
            max_tokens=200,
        )

        return response.content.strip()

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
        """Identify key turning points in the simulation."""
        turning_points = []

        if not simulation_state.rounds:
            return turning_points

        # Analyze for significant changes between rounds
        prev_stances = {}
        for round_state in simulation_state.rounds:
            round_num = round_state.round_number

            for msg in round_state.messages:
                # Check for significant stance changes
                if msg.agent_id in prev_stances:
                    # Simple heuristic: significant content change
                    if len(msg.content) > 50:
                        # Check for contradiction keywords
                        content_lower = msg.content.lower()
                        if any(word in content_lower for word in ["however", "but", "instead", "changed"]):
                            turning_points.append({
                                "round": round_num,
                                "description": f"{msg.agent_name} shifted position",
                                "significance": "major",
                            })

                # Update stance tracking
                prev_stances[msg.agent_id] = msg.content

        # Use LLM for deeper analysis if available
        if self.llm and len(simulation_state.rounds) > 2:
            try:
                llm_turning_points = await self._analyze_turning_points_with_llm(
                    simulation_state
                )
                turning_points.extend(llm_turning_points)
            except Exception as e:
                logger.error(f"Failed to analyze turning points with LLM: {e}")

        # Remove duplicates and limit
        seen = set()
        unique_points = []
        for point in turning_points:
            key = (point.get("round"), point.get("description"))
            if key not in seen:
                seen.add(key)
                unique_points.append(point)

        return unique_points[:5]

    async def _analyze_turning_points_with_llm(
        self, simulation_state
    ) -> list[dict]:
        """Use LLM to identify turning points."""
        # Prepare simulation arc with all messages
        arc_summary = []
        for round_state in simulation_state.rounds:
            key_msgs = [
                f"{msg.agent_name} ({msg.agent_role}): "
                f"{msg.content[:300]}"
                for msg in round_state.messages
            ]
            arc_summary.append(
                f"Round {round_state.round_number}:\n"
                + "\n".join(key_msgs)
            )

        arc_text = "\n\n".join(arc_summary)

        prompt = f"""Identify the key turning points in this simulation.

SIMULATION ARC:
{arc_text}

Identify 2-3 major turning points where the direction or dynamics significantly changed.

Respond in this JSON format:
[
    {{
        "round": round_number,
        "description": "What happened at this turning point",
        "significance": "major|minor"
    }}
]

Respond with valid JSON only."""

        response = await self.llm.generate(
            messages=[
                LLMMessage(
                    role="system",
                    content="You identify turning points in simulations. "
                            "Respond with valid JSON only.",
                ),
                LLMMessage(role="user", content=prompt),
            ],
            temperature=0.4,
            max_tokens=400,
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
            logger.error(f"Failed to parse turning points: {e}")
            return []

    async def _identify_unexpected_outcomes(
        self, simulation_state
    ) -> list[str]:
        """Identify unexpected outcomes from the simulation."""
        outcomes = []

        # Analyze final stances vs initial archetype expectations
        for agent in simulation_state.agents:
            if agent.current_stance:
                # Check if stance is unexpected for archetype
                stance_lower = agent.current_stance.lower()
                archetype_id = agent.archetype_id

                # Simple heuristics for unexpected outcomes
                if archetype_id == "cfo" and "risk" in stance_lower:
                    if "acceptable" in stance_lower or "worth taking" in stance_lower:
                        outcomes.append(
                            f"{agent.name} (CFO) unexpectedly supported a risky position"
                        )

                if archetype_id == "ceo" and "cautious" in stance_lower:
                    outcomes.append(
                        f"{agent.name} (CEO) took a surprisingly cautious approach"
                    )

                if archetype_id == "activist_investor" and "support" in stance_lower:
                    outcomes.append(
                        f"{agent.name} (Activist) supported management unexpectedly"
                    )

        # Use LLM for additional insights
        if self.llm and simulation_state.rounds:
            try:
                llm_outcomes = await self._analyze_unexpected_outcomes_with_llm(
                    simulation_state
                )
                outcomes.extend(llm_outcomes)
            except Exception as e:
                logger.error(f"Failed to analyze unexpected outcomes: {e}")

        return list(set(outcomes))[:5]

    async def _analyze_unexpected_outcomes_with_llm(
        self, simulation_state
    ) -> list[str]:
        """Use LLM to identify unexpected outcomes."""
        # Prepare summary
        agent_final_stances = []
        for agent in simulation_state.agents:
            agent_final_stances.append(
                f"{agent.name} ({agent.archetype_id}): {agent.current_stance}"
            )

        stances_text = "\n".join(agent_final_stances)

        prompt = f"""Based on these final stances, identify any unexpected outcomes.

FINAL STANCES:
{stances_text}

What outcomes were surprising given the participants' roles?

Respond with a JSON array of strings describing unexpected outcomes:
["outcome 1", "outcome 2"]

Respond with valid JSON only."""

        response = await self.llm.generate(
            messages=[
                LLMMessage(
                    role="system",
                    content="You identify unexpected outcomes in simulations. "
                            "Respond with valid JSON only.",
                ),
                LLMMessage(role="user", content=prompt),
            ],
            temperature=0.5,
            max_tokens=300,
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
            logger.error(f"Failed to parse unexpected outcomes: {e}")
            return []
