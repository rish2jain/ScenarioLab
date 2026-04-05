"""Boardroom environment for formal decision-making simulations."""

import logging

from app.simulation.agent import SimulationAgent
from app.simulation.environments.base import BaseEnvironment
from app.simulation.models import EnvironmentType, RoundState
from app.simulation.turn_rules import TurnManager
from app.simulation.visibility import VisibilityManager

logger = logging.getLogger(__name__)


class BoardroomEnvironment(BaseEnvironment):
    """
    Boardroom environment for formal decision-making.

    Phases:
    - presentation: CEO/proposer presents
    - qa: Others ask clarifying questions (strict rotation)
    - objection: Any agent can raise objections
    - rebuttal: Proposer addresses objections
    - vote: Majority vote (51%), Chair tie-breaker, CEO override option
    """

    env_type = EnvironmentType.BOARDROOM
    phases = ["presentation", "qa", "objection", "rebuttal", "vote"]

    def __init__(self):
        super().__init__()
        self._proposer_id: str | None = None

    async def run_phase(
        self,
        phase: str,
        round_number: int,
        agents: list[SimulationAgent],
        visibility: VisibilityManager,
        turn_manager: TurnManager,
        round_state: RoundState,
    ) -> RoundState:
        """Execute a single phase of a boardroom round."""
        logger.info(f"Running boardroom phase: {phase} (round {round_number})")

        # Get speaking order
        speaking_order = turn_manager.get_speaking_order(phase, round_number)
        participants = turn_manager.get_phase_participants(phase)

        if phase == "presentation":
            await self._run_presentation_phase(agents, speaking_order, round_state, visibility)
        elif phase == "qa":
            await self._run_qa_phase(agents, speaking_order, participants, round_state, visibility)
        elif phase == "objection":
            await self._run_objection_phase(agents, speaking_order, round_state, visibility)
        elif phase == "rebuttal":
            await self._run_rebuttal_phase(agents, speaking_order, round_state, visibility)
        elif phase == "vote":
            await self._run_vote_phase(agents, round_state)

        round_state.phase = phase
        round_state.phase_complete = True

        return round_state

    async def _run_presentation_phase(
        self,
        agents: list[SimulationAgent],
        speaking_order: list[str],
        round_state: RoundState,
        visibility: VisibilityManager,
    ):
        """Run the presentation phase - proposer presents."""
        # Find the proposer (CEO or first agent)
        proposer = None
        for agent in agents:
            if agent.archetype.id == "ceo":
                proposer = agent
                break

        if not proposer and agents:
            proposer = agents[0]

        if proposer:
            self._proposer_id = proposer.id
            message = await self._process_agent_turn(
                agent=proposer,
                phase="presentation",
                round_number=round_state.round_number,
                visibility=visibility,
                round_state=round_state,
                context="You are presenting a proposal to the board.",
            )
            if message:
                round_state.messages.append(message)

    async def _run_qa_phase(
        self,
        agents: list[SimulationAgent],
        speaking_order: list[str],
        participants: list[str],
        round_state: RoundState,
        visibility: VisibilityManager,
    ):
        """Run the Q&A phase - strict rotation."""
        agent_map = {a.id: a for a in agents}

        for agent_id in speaking_order:
            if agent_id not in participants:
                continue
            if agent_id == self._proposer_id:
                continue  # Proposer doesn't ask questions

            agent = agent_map.get(agent_id)
            if not agent:
                continue

            message = await self._process_agent_turn(
                agent=agent,
                phase="qa",
                round_number=round_state.round_number,
                visibility=visibility,
                round_state=round_state,
                context="Ask a clarifying question about the proposal.",
            )
            if message:
                round_state.messages.append(message)

    async def _run_objection_phase(
        self,
        agents: list[SimulationAgent],
        speaking_order: list[str],
        round_state: RoundState,
        visibility: VisibilityManager,
    ):
        """Run the objection phase - any agent can raise objections."""
        agent_map = {a.id: a for a in agents}

        for agent_id in speaking_order:
            agent = agent_map.get(agent_id)
            if not agent:
                continue

            message = await self._process_agent_turn(
                agent=agent,
                phase="objection",
                round_number=round_state.round_number,
                visibility=visibility,
                round_state=round_state,
                context="Raise any objections or concerns about the proposal.",
            )
            if message:
                round_state.messages.append(message)

    async def _run_rebuttal_phase(
        self,
        agents: list[SimulationAgent],
        speaking_order: list[str],
        round_state: RoundState,
        visibility: VisibilityManager,
    ):
        """Run the rebuttal phase - proposer addresses objections."""
        if not self._proposer_id:
            return

        agent_map = {a.id: a for a in agents}
        proposer = agent_map.get(self._proposer_id)

        if proposer:
            message = await self._process_agent_turn(
                agent=proposer,
                phase="rebuttal",
                round_number=round_state.round_number,
                visibility=visibility,
                round_state=round_state,
                context="Address the objections raised against your proposal.",
            )
            if message:
                round_state.messages.append(message)

    async def _run_vote_phase(
        self,
        agents: list[SimulationAgent],
        round_state: RoundState,
    ):
        """Run the voting phase."""
        # Get proposal text from presentation
        proposal = "the proposal"
        for msg in round_state.messages:
            if msg.phase == "presentation":
                proposal = msg.content[:200]  # First 200 chars
                break

        votes = await self._run_voting_phase(proposal, agents, round_state)
        vote_result = self._count_votes(votes)

        round_state.decisions.append(
            {
                "type": "vote",
                "result": vote_result,
                "votes": votes,
            }
        )

        logger.info(f"Vote result: {vote_result['result']}")

    async def evaluate_round(self, round_state: RoundState) -> dict:
        """Evaluate boardroom round outcomes."""
        evaluation = {
            "round_number": round_state.round_number,
            "phase": round_state.phase,
            "message_count": len(round_state.messages),
            "decisions": [],
        }

        # Check for vote decision
        for decision in round_state.decisions:
            if decision.get("type") == "vote":
                evaluation["vote_result"] = decision["result"]
                evaluation["decisions"].append(decision)

        # Determine if proposal passed
        if "vote_result" in evaluation:
            result = evaluation["vote_result"]
            if result.get("result") == "passed":
                evaluation["outcome"] = "accepted"
            elif result.get("result") == "rejected":
                evaluation["outcome"] = "rejected"
            else:
                evaluation["outcome"] = "inconclusive"

        return evaluation

    # Role-specific instruction overlays keyed by (phase, role_keyword).
    # Matched via substring so "CFO" matches "Chief Financial Officer".
    _ROLE_OVERLAYS: dict[tuple[str, str], str] = {
        ("qa", "cfo"): (
            "Probe the financial assumptions: margins, payback " "period, capital requirements, and downside scenarios."
        ),
        ("qa", "cro"): ("Assess risk exposure: regulatory, operational, and " "reputational. Quantify where possible."),
        ("qa", "analyst"): ("Challenge with data: market sizing, competitive " "benchmarks, and customer evidence."),
        ("qa", "competitor"): (
            "Identify how competitors would respond and what " "defensive gaps the proposal creates."
        ),
        ("objection", "cfo"): (
            "Object on financial grounds: insufficient ROI, " "unquantified risk, or missing budget detail."
        ),
        ("objection", "cro"): (
            "Object on risk grounds: compliance gaps, " "unmitigated exposure, or missing controls."
        ),
        ("objection", "operations"): (
            "Object on execution grounds: capacity " "constraints, timeline risks, or dependencies."
        ),
        ("presentation", "ceo"): (
            "Present the strategic vision. Frame the "
            "opportunity, articulate the thesis, and set "
            "success criteria for the board."
        ),
        ("rebuttal", "ceo"): (
            "Address objections directly. Acknowledge valid "
            "concerns with mitigations; push back on "
            "objections that misread the strategic intent."
        ),
    }

    def _resolve_phase_instruction(
        self,
        phase: str,
        agent_role: str,
    ) -> str:
        """Get phase-specific instruction, enriched by role."""
        base = {
            "presentation": (
                "Present your proposal clearly and "
                "persuasively. Explain the strategic "
                "rationale and expected outcomes."
            ),
            "qa": (
                "Ask a clarifying question about the " "proposal. Focus on understanding " "implications and risks."
            ),
            "objection": (
                "Raise any objections or concerns about " "the proposal. Be specific about your " "concerns."
            ),
            "rebuttal": (
                "Address the objections raised. Provide " "counter-arguments or acknowledge valid " "concerns."
            ),
            "vote": "Cast your vote on the proposal.",
        }
        instruction = base.get(phase, "Participate in the discussion.")

        # Look for a role-specific overlay
        role_lower = (agent_role or "").lower()
        for (p, role_key), overlay in self._ROLE_OVERLAYS.items():
            if p == phase and role_key in role_lower:
                instruction = overlay
                break

        return instruction
