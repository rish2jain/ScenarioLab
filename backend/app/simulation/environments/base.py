"""Base environment class for simulations."""

import logging
from abc import ABC, abstractmethod
from typing import Any

from app.simulation.agent import SimulationAgent
from app.simulation.models import (
    EnvironmentType,
    RoundState,
    SimulationMessage,
)
from app.simulation.objectives import build_round_agenda_line
from app.simulation.turn_rules import TurnManager
from app.simulation.visibility import VisibilityManager

logger = logging.getLogger(__name__)


class BaseEnvironment(ABC):
    """Base class for simulation environments."""

    env_type: EnvironmentType
    phases: list[str]  # Ordered list of phases in each round

    def __init__(self):
        self.current_phase_idx = 0
        self._sim_config: Any = None
        self._memory_manager: Any = None  # Set by engine

    @abstractmethod
    async def run_phase(
        self,
        phase: str,
        round_number: int,
        agents: list[SimulationAgent],
        visibility: VisibilityManager,
        turn_manager: TurnManager,
        round_state: RoundState,
    ) -> RoundState:
        """Execute a single phase of a round."""
        pass

    @abstractmethod
    async def evaluate_round(self, round_state: RoundState) -> dict:
        """Evaluate round outcomes (votes, decisions, etc.)."""
        pass

    def get_phase_instruction(
        self,
        phase: str,
        agent_role: str,
        *,
        round_number: int = 1,
    ) -> str:
        """Get phase-specific instruction for an agent."""
        body = self._resolve_phase_instruction(phase, agent_role)
        line = build_round_agenda_line(
            round_number,
            getattr(self._sim_config, "parameters", None) or {},
        )
        if line:
            return f"{body}\n\nRound focus (objective hypothesis): {line}"
        return body

    def _resolve_phase_instruction(self, phase: str, agent_role: str) -> str:
        """Subclass override for phase copy; agenda is appended in ``get_phase_instruction``."""
        default = "Participate in the discussion."
        return self._default_instructions().get(phase, default)

    def _default_instructions(self) -> dict[str, str]:
        """Default phase instructions."""
        return {
            "presentation": "Present your proposal clearly and persuasively.",
            "qa": "Ask clarifying questions or provide answers.",
            "objection": "Raise any objections or concerns you have.",
            "rebuttal": "Address the objections raised.",
            "vote": "Cast your vote on the proposal.",
        }

    def get_next_phase(self, current_phase: str) -> str | None:
        """Get the next phase in the sequence."""
        try:
            idx = self.phases.index(current_phase)
            if idx + 1 < len(self.phases):
                return self.phases[idx + 1]
        except ValueError:
            pass
        return None

    def get_first_phase(self) -> str:
        """Get the first phase of a round."""
        return self.phases[0] if self.phases else ""

    def is_final_phase(self, phase: str) -> bool:
        """Check if this is the final phase of a round."""
        return phase == self.phases[-1] if self.phases else True

    async def _process_agent_turn(
        self,
        agent: SimulationAgent,
        phase: str,
        round_number: int,
        visibility: VisibilityManager,
        round_state: RoundState,
        context: str = "",
    ) -> SimulationMessage | None:
        """Process a single agent's turn."""
        try:
            # Get visible messages for this agent
            visible_messages = visibility.filter_messages_for_agent(
                agent.state, round_state.messages
            )

            # Enrich context with agent's cross-round memories
            enriched_context = context
            if self._memory_manager and round_number > 1:
                sim_id = getattr(
                    self._sim_config, "id", ""
                )
                if sim_id:
                    try:
                        mem_ctx = (
                            await self._memory_manager
                            .get_agent_context(
                                agent_id=agent.id,
                                simulation_id=sim_id,
                                current_round=round_number,
                            )
                        )
                        if mem_ctx:
                            enriched_context = (
                                f"{context}\n\n{mem_ctx}"
                                if context
                                else mem_ctx
                            )
                    except Exception:
                        logger.debug(
                            "Memory retrieval failed for %s",
                            agent.name,
                            exc_info=True,
                        )

            # Get phase instruction
            instruction = self.get_phase_instruction(
                phase,
                agent.archetype.role,
                round_number=round_number,
            )

            # Generate response
            message = await agent.generate_response(
                context=enriched_context,
                phase=phase,
                round_number=round_number,
                visible_messages=visible_messages,
                instruction=instruction,
            )

            return message

        except Exception as e:
            logger.error(
                f"Error processing turn for agent {agent.name}: {e}"
            )
            return None

    async def _run_voting_phase(
        self,
        proposal: str,
        agents: list[SimulationAgent],
        round_state: RoundState,
    ) -> list[dict]:
        """Run a voting phase and collect results."""
        votes = []

        for agent in agents:
            try:
                vote_result = await agent.cast_vote(
                    proposal=proposal,
                    arguments=round_state.messages,
                    round_number=round_state.round_number,
                )
                votes.append(vote_result)

                # Create a vote message
                vote_message = SimulationMessage(
                    round_number=round_state.round_number,
                    phase="vote",
                    agent_id=agent.id,
                    agent_name=agent.name,
                    agent_role=agent.archetype.role,
                    content=(
                        f"Vote: {vote_result['vote']}. "
                        f"{vote_result['reasoning']}"
                    ),
                    message_type="vote",
                )
                round_state.messages.append(vote_message)

            except Exception as e:
                logger.error(f"Error collecting vote from {agent.name}: {e}")
                votes.append({
                    "agent_id": agent.id,
                    "agent_name": agent.name,
                    "vote": "abstain",
                    "reasoning": f"Error: {str(e)}",
                })

        return votes

    def _count_votes(self, votes: list[dict]) -> dict:
        """Count votes and determine outcome."""
        for_votes = sum(1 for v in votes if v["vote"] == "for")
        against_votes = sum(1 for v in votes if v["vote"] == "against")
        abstain_votes = sum(1 for v in votes if v["vote"] == "abstain")
        total = len(votes)

        if total == 0:
            return {
                "result": "no_quorum",
                "for": 0, "against": 0, "abstain": 0,
            }

        # Simple majority (51%)
        majority_threshold = total / 2

        if for_votes > majority_threshold:
            result = "passed"
        elif against_votes > majority_threshold:
            result = "rejected"
        else:
            result = "tie"

        return {
            "result": result,
            "for": for_votes,
            "against": against_votes,
            "abstain": abstain_votes,
            "total": total,
            "majority_threshold": majority_threshold,
        }
