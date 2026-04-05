"""War Room environment for crisis response simulations."""

import logging

from app.simulation.agent import SimulationAgent
from app.simulation.environments.base import BaseEnvironment
from app.simulation.models import EnvironmentType, RoundState
from app.simulation.objectives import build_round_agenda_line
from app.simulation.turn_rules import TurnManager
from app.simulation.visibility import VisibilityManager

logger = logging.getLogger(__name__)


class WarRoomEnvironment(BaseEnvironment):
    """
    War Room environment for crisis response and threat assessment.

    Phases:
    - intel_briefing: Share intelligence and situational awareness
    - threat_assessment: CRO and executives assess threats
    - response_options: Generate and evaluate response options
    - decision: Leadership makes decisions
    - action_assignment: Assign actions to teams

    Features:
    - Dynamic turn-taking based on authority/urgency
    - CRO escalation for compliance issues
    - Time-boxed consensus (limited responses per phase)
    """

    env_type = EnvironmentType.WAR_ROOM
    phases = [
        "intel_briefing",
        "threat_assessment",
        "response_options",
        "decision",
        "action_assignment",
    ]

    def __init__(self):
        super().__init__()
        self._threat_level = "medium"
        self._compliance_flag = False

    async def run_phase(
        self,
        phase: str,
        round_number: int,
        agents: list[SimulationAgent],
        visibility: VisibilityManager,
        turn_manager: TurnManager,
        round_state: RoundState,
    ) -> RoundState:
        """Execute a single phase of a war room round."""
        logger.info(f"Running war room phase: {phase} (round {round_number})")

        speaking_order = turn_manager.get_speaking_order(phase, round_number)
        participants = turn_manager.get_phase_participants(phase)

        if phase == "intel_briefing":
            await self._run_intel_briefing(agents, speaking_order, round_state, visibility)
        elif phase == "threat_assessment":
            await self._run_threat_assessment(agents, speaking_order, participants, round_state, visibility)
        elif phase == "response_options":
            await self._run_response_options(agents, speaking_order, participants, round_state, visibility)
        elif phase == "decision":
            await self._run_decision_phase(agents, speaking_order, round_state, visibility)
        elif phase == "action_assignment":
            await self._run_action_assignment(agents, speaking_order, round_state, visibility)

        round_state.phase = phase
        round_state.phase_complete = True

        return round_state

    async def _run_intel_briefing(
        self,
        agents: list[SimulationAgent],
        speaking_order: list[str],
        round_state: RoundState,
        visibility: VisibilityManager,
    ):
        """Run intelligence briefing phase."""
        agent_map = {a.id: a for a in agents}

        for agent_id in speaking_order[:5]:  # Limit to 5 briefings
            agent = agent_map.get(agent_id)
            if not agent:
                continue

            message = await self._process_agent_turn(
                agent=agent,
                phase="intel_briefing",
                round_number=round_state.round_number,
                visibility=visibility,
                round_state=round_state,
                context=self._resolve_phase_instruction("intel_briefing", agent.archetype.role),
            )
            if message:
                round_state.messages.append(message)

    async def _run_threat_assessment(
        self,
        agents: list[SimulationAgent],
        speaking_order: list[str],
        participants: list[str],
        round_state: RoundState,
        visibility: VisibilityManager,
    ):
        """Run threat assessment phase - CRO has priority."""
        agent_map = {a.id: a for a in agents}

        # CRO goes first if present
        cro_first_order = []
        others = []

        for agent_id in speaking_order:
            agent = agent_map.get(agent_id)
            if not agent:
                continue
            if agent.archetype.id == "cro":
                cro_first_order.append(agent_id)
            elif agent_id in participants:
                others.append(agent_id)

        ordered = cro_first_order + others

        for agent_id in ordered[:4]:  # Limit responses
            agent = agent_map.get(agent_id)
            if not agent:
                continue

            message = await self._process_agent_turn(
                agent=agent,
                phase="threat_assessment",
                round_number=round_state.round_number,
                visibility=visibility,
                round_state=round_state,
                context=self._resolve_phase_instruction("threat_assessment", agent.archetype.role),
            )
            if message:
                round_state.messages.append(message)
                # Check for compliance flag
                if "compliance" in message.content.lower():
                    self._compliance_flag = True

    async def _run_response_options(
        self,
        agents: list[SimulationAgent],
        speaking_order: list[str],
        participants: list[str],
        round_state: RoundState,
        visibility: VisibilityManager,
    ):
        """Run response options generation phase."""
        agent_map = {a.id: a for a in agents}

        for agent_id in speaking_order[:4]:  # Limit responses
            if agent_id not in participants:
                continue

            agent = agent_map.get(agent_id)
            if not agent:
                continue

            message = await self._process_agent_turn(
                agent=agent,
                phase="response_options",
                round_number=round_state.round_number,
                visibility=visibility,
                round_state=round_state,
                context=self._resolve_phase_instruction("response_options", agent.archetype.role),
            )
            if message:
                round_state.messages.append(message)

    async def _run_decision_phase(
        self,
        agents: list[SimulationAgent],
        speaking_order: list[str],
        round_state: RoundState,
        visibility: VisibilityManager,
    ):
        """Run decision phase - leadership makes call."""
        agent_map = {a.id: a for a in agents}

        # Only key decision makers
        decision_makers = [
            aid for aid in speaking_order if aid in [a.id for a in agents if a.archetype.id in ["ceo", "cfo", "cro"]]
        ]

        for agent_id in decision_makers[:3]:
            agent = agent_map.get(agent_id)
            if not agent:
                continue

            message = await self._process_agent_turn(
                agent=agent,
                phase="decision",
                round_number=round_state.round_number,
                visibility=visibility,
                round_state=round_state,
                context=self._resolve_phase_instruction("decision", agent.archetype.role),
            )
            if message:
                round_state.messages.append(message)

        # Record the decision
        round_state.decisions.append(
            {
                "type": "decision",
                "makers": decision_makers,
                "compliance_escalation": self._compliance_flag,
            }
        )

    async def _run_action_assignment(
        self,
        agents: list[SimulationAgent],
        speaking_order: list[str],
        round_state: RoundState,
        visibility: VisibilityManager,
    ):
        """Run action assignment phase."""
        agent_map = {a.id: a for a in agents}

        # Operations and functional heads
        assigners = [
            aid
            for aid in speaking_order
            if aid in [a.id for a in agents if a.archetype.id in ["operations_head", "hr_head", "strategy_vp"]]
        ]

        for agent_id in assigners[:3]:
            agent = agent_map.get(agent_id)
            if not agent:
                continue

            message = await self._process_agent_turn(
                agent=agent,
                phase="action_assignment",
                round_number=round_state.round_number,
                visibility=visibility,
                round_state=round_state,
                context=self._resolve_phase_instruction("action_assignment", agent.archetype.role),
            )
            if message:
                round_state.messages.append(message)

    async def evaluate_round(self, round_state: RoundState) -> dict:
        """Evaluate war room round outcomes."""
        evaluation = {
            "round_number": round_state.round_number,
            "phase": round_state.phase,
            "message_count": len(round_state.messages),
            "compliance_flag": self._compliance_flag,
            "decisions": [],
        }

        # Extract key themes from messages
        threat_keywords = ["risk", "threat", "danger", "critical", "urgent"]
        threat_count = sum(
            1 for msg in round_state.messages if any(kw in msg.content.lower() for kw in threat_keywords)
        )

        evaluation["threat_mentions"] = threat_count

        if threat_count > 3:
            evaluation["threat_level"] = "high"
        elif threat_count > 1:
            evaluation["threat_level"] = "medium"
        else:
            evaluation["threat_level"] = "low"

        # Check for decisions made
        for decision in round_state.decisions:
            evaluation["decisions"].append(decision)

        return evaluation

    def get_phase_instruction(
        self,
        _phase: str,
        _agent_role: str,
        *,
        round_number: int = 1,
    ) -> str:
        """War-room agenda line only.

        ``_phase`` and ``_agent_role`` match the base ``SimulationEnvironment.get_phase_instruction``
        signature for protocol consistency but are intentionally unused here: phase-specific copy is
        passed separately as ``context`` from ``_resolve_phase_instruction``. Only ``round_number``
        and ``build_round_agenda_line(self._sim_config.parameters)`` shape this return value.
        """
        line = build_round_agenda_line(
            round_number,
            getattr(self._sim_config, "parameters", None) or {},
        )
        if line:
            return f"Round focus (objective hypothesis): {line}"
        return ""

    def _resolve_phase_instruction(self, phase: str, _agent_role: str) -> str:
        """Phase-specific copy for ``_process_agent_turn`` ``context`` (and shared instruction text source)."""
        instructions = {
            "intel_briefing": ("Share relevant intelligence or situational updates. " "Be concise and factual."),
            "threat_assessment": (
                "Assess the severity of threats. If you're the CRO, " "escalate compliance issues immediately."
            ),
            "response_options": (
                "Propose concrete response options. Consider feasibility " "and resource requirements."
            ),
            "decision": ("Make a clear decision on the response strategy. " "Consider risks and benefits."),
            "action_assignment": ("Assign specific actions with clear owners and timelines."),
        }
        return instructions.get(phase, "Contribute to the discussion.")
