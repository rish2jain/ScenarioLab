"""Negotiation environment for bilateral/multi-party negotiations."""

import logging

from app.simulation.agent import SimulationAgent
from app.simulation.environments.base import BaseEnvironment
from app.simulation.models import EnvironmentType, RoundState
from app.simulation.turn_rules import TurnManager
from app.simulation.visibility import VisibilityManager

logger = logging.getLogger(__name__)


class NegotiationEnvironment(BaseEnvironment):
    """
    Negotiation environment for bilateral/multi-party negotiations.

    Phases:
    - position_statements: Each party states their position
    - private_caucus: Mediator meets with parties separately
    - counter_proposal: Parties exchange proposals
    - red_line_identification: Identify non-negotiables
    - agreement_check: Verify if agreement is possible

    Features:
    - Bilateral exchanges
    - BATNA triggers if impasse >3 rounds
    - Mediator sees all communications
    """

    env_type = EnvironmentType.NEGOTIATION
    phases = [
        "position_statements",
        "private_caucus",
        "counter_proposal",
        "red_line_identification",
        "agreement_check",
    ]

    def __init__(self):
        super().__init__()
        self._impasse_rounds = 0
        self._agreement_reached = False
        self._batna_triggered = False

    async def run_phase(
        self,
        phase: str,
        round_number: int,
        agents: list[SimulationAgent],
        visibility: VisibilityManager,
        turn_manager: TurnManager,
        round_state: RoundState,
    ) -> RoundState:
        """Execute a single phase of a negotiation round."""
        logger.info(
            f"Running negotiation phase: {phase} (round {round_number})"
        )

        speaking_order = turn_manager.get_speaking_order(phase, round_number)
        participants = turn_manager.get_phase_participants(phase)

        if phase == "position_statements":
            await self._run_position_statements(
                agents, speaking_order, round_state, visibility
            )
        elif phase == "private_caucus":
            await self._run_private_caucus(
                agents, speaking_order, round_state, visibility
            )
        elif phase == "counter_proposal":
            await self._run_counter_proposal(
                agents, speaking_order, participants, round_state, visibility
            )
        elif phase == "red_line_identification":
            await self._run_red_line_identification(
                agents, speaking_order, round_state, visibility
            )
        elif phase == "agreement_check":
            await self._run_agreement_check(
                agents, speaking_order, round_state, visibility
            )

        round_state.phase = phase
        round_state.phase_complete = True

        return round_state

    async def _run_position_statements(
        self,
        agents: list[SimulationAgent],
        speaking_order: list[str],
        round_state: RoundState,
        visibility: VisibilityManager,
    ):
        """Run position statements phase - each party states position."""
        agent_map = {a.id: a for a in agents}

        # Exclude mediator from position statements
        parties = [
            aid for aid in speaking_order
            if aid in [a.id for a in agents if a.archetype.id != "mediator"]
        ]

        for agent_id in parties:
            agent = agent_map.get(agent_id)
            if not agent:
                continue

            message = await self._process_agent_turn(
                agent=agent,
                phase="position_statements",
                round_number=round_state.round_number,
                visibility=visibility,
                round_state=round_state,
                context=(
                    "Clearly state your position and interests in the "
                    "negotiation."
                ),
            )
            if message:
                round_state.messages.append(message)

    async def _run_private_caucus(
        self,
        agents: list[SimulationAgent],
        speaking_order: list[str],
        round_state: RoundState,
        visibility: VisibilityManager,
    ):
        """Run private caucus phase - mediator meets with parties."""
        # Find mediator
        mediator = None
        for agent in agents:
            if agent.archetype.id == "mediator":
                mediator = agent
                break

        if mediator:
            # Mediator summarizes private discussions
            message = await self._process_agent_turn(
                agent=mediator,
                phase="private_caucus",
                round_number=round_state.round_number,
                visibility=visibility,
                round_state=round_state,
                context=(
                    "Summarize the private discussions and identify "
                    "common ground."
                ),
            )
            if message:
                # Mark as coalition visible (mediator's view)
                message.visibility = "coalition"
                round_state.messages.append(message)

    async def _run_counter_proposal(
        self,
        agents: list[SimulationAgent],
        speaking_order: list[str],
        participants: list[str],
        round_state: RoundState,
        visibility: VisibilityManager,
    ):
        """Run counter-proposal phase - parties exchange proposals."""
        agent_map = {a.id: a for a in agents}

        # Alternate between parties
        parties = [
            aid for aid in speaking_order
            if aid in participants and aid in [a.id for a in agents
                                               if a.archetype.id != "mediator"]
        ]

        for i, agent_id in enumerate(parties[:4]):  # Limit exchanges
            agent = agent_map.get(agent_id)
            if not agent:
                continue

            message = await self._process_agent_turn(
                agent=agent,
                phase="counter_proposal",
                round_number=round_state.round_number,
                visibility=visibility,
                round_state=round_state,
                context=(
                    "Make a counter-proposal or respond to the other "
                    "party's offer."
                ),
            )
            if message:
                round_state.messages.append(message)

    async def _run_red_line_identification(
        self,
        agents: list[SimulationAgent],
        speaking_order: list[str],
        round_state: RoundState,
        visibility: VisibilityManager,
    ):
        """Run red line identification phase."""
        agent_map = {a.id: a for a in agents}

        parties = [
            aid for aid in speaking_order
            if aid in [a.id for a in agents if a.archetype.id != "mediator"]
        ]

        for agent_id in parties:
            agent = agent_map.get(agent_id)
            if not agent:
                continue

            message = await self._process_agent_turn(
                agent=agent,
                phase="red_line_identification",
                round_number=round_state.round_number,
                visibility=visibility,
                round_state=round_state,
                context="Identify your non-negotiable red lines clearly.",
            )
            if message:
                round_state.messages.append(message)

    async def _run_agreement_check(
        self,
        agents: list[SimulationAgent],
        speaking_order: list[str],
        round_state: RoundState,
        visibility: VisibilityManager,
    ):
        """Run agreement check phase."""
        agent_map = {a.id: a for a in agents}

        parties = [
            aid for aid in speaking_order
            if aid in [a.id for a in agents if a.archetype.id != "mediator"]
        ]

        for agent_id in parties:
            agent = agent_map.get(agent_id)
            if not agent:
                continue

            message = await self._process_agent_turn(
                agent=agent,
                phase="agreement_check",
                round_number=round_state.round_number,
                visibility=visibility,
                round_state=round_state,
                context=(
                    "Indicate whether you can accept the current terms "
                    "or if we're at an impasse."
                ),
            )
            if message:
                round_state.messages.append(message)

                # Check for agreement indicators
                content_lower = message.content.lower()
                if any(word in content_lower
                       for word in ["agree", "accept", "yes"]):
                    self._agreement_reached = True
                elif any(word in content_lower
                         for word in ["impasse", "no deal", "reject"]):
                    self._impasse_rounds += 1

        # Record agreement status
        round_state.decisions.append({
            "type": "agreement_check",
            "agreement_reached": self._agreement_reached,
            "impasse_rounds": self._impasse_rounds,
        })

    async def evaluate_round(self, round_state: RoundState) -> dict:
        """Evaluate negotiation round outcomes."""
        evaluation = {
            "round_number": round_state.round_number,
            "phase": round_state.phase,
            "message_count": len(round_state.messages),
            "agreement_reached": self._agreement_reached,
            "impasse_rounds": self._impasse_rounds,
            "batna_triggered": self._batna_triggered,
        }

        # Check for BATNA trigger
        if self._impasse_rounds >= 3 and not self._batna_triggered:
            self._batna_triggered = True
            evaluation["batna_triggered"] = True
            evaluation["warning"] = (
                "BATNA (Best Alternative) should be considered"
            )

        # Analyze positions
        concession_keywords = ["concede", "compromise", "flexible", "willing"]
        hardline_keywords = ["non-negotiable", "must", "cannot", "red line"]

        concession_count = sum(
            1 for msg in round_state.messages
            if any(kw in msg.content.lower() for kw in concession_keywords)
        )
        hardline_count = sum(
            1 for msg in round_state.messages
            if any(kw in msg.content.lower() for kw in hardline_keywords)
        )

        evaluation["concession_signals"] = concession_count
        evaluation["hardline_signals"] = hardline_count

        if concession_count > hardline_count:
            evaluation["negotiation_climate"] = "cooperative"
        elif hardline_count > concession_count:
            evaluation["negotiation_climate"] = "contentious"
        else:
            evaluation["negotiation_climate"] = "neutral"

        return evaluation

    def get_phase_instruction(self, phase: str, agent_role: str) -> str:
        """Get phase-specific instruction for an agent."""
        instructions = {
            "position_statements": (
                "Clearly state your opening position and key interests. "
                "Be firm but leave room for negotiation."
            ),
            "private_caucus": (
                "If you're the mediator, identify common ground. "
                "If you're a party, share confidential info with the "
                "mediator."
            ),
            "counter_proposal": (
                "Respond to the other party's position with a "
                "counter-proposal. Show where you can be flexible."
            ),
            "red_line_identification": (
                "Clearly identify your non-negotiable red lines. "
                "Be explicit about what you cannot accept."
            ),
            "agreement_check": (
                "Indicate clearly if you can accept the current terms. "
                "If not, state that we're at an impasse."
            ),
        }
        return instructions.get(phase, "Participate in the negotiation.")
