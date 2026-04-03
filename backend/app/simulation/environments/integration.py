"""Integration environment for M&A and organizational integration."""

import logging

from app.simulation.agent import SimulationAgent
from app.simulation.environments.base import BaseEnvironment
from app.simulation.models import EnvironmentType, RoundState
from app.simulation.turn_rules import TurnManager
from app.simulation.visibility import VisibilityManager

logger = logging.getLogger(__name__)


class IntegrationEnvironment(BaseEnvironment):
    """
    Integration environment for M&A and organizational integration planning.

    Phases:
    - current_state_mapping: Document current organizational states
    - future_state_vision: Define the desired future state
    - gap_analysis: Identify gaps between current and future
    - initiative_prioritization: Prioritize integration initiatives
    - resource_allocation: Allocate budget and resources (CFO veto power)

    Features:
    - Parallel workstreams with sync points
    - Priority matrix scoring (impact x effort)
    - CFO veto on budget exceedance
    """

    env_type = EnvironmentType.INTEGRATION
    phases = [
        "current_state_mapping",
        "future_state_vision",
        "gap_analysis",
        "initiative_prioritization",
        "resource_allocation",
    ]

    def __init__(self):
        super().__init__()
        self._budget_total = 100  # Million dollars placeholder
        self._budget_allocated = 0
        self._cfo_veto_used = False
        self._initiatives: list[dict] = []

    async def run_phase(
        self,
        phase: str,
        round_number: int,
        agents: list[SimulationAgent],
        visibility: VisibilityManager,
        turn_manager: TurnManager,
        round_state: RoundState,
    ) -> RoundState:
        """Execute a single phase of an integration round."""
        logger.info(
            f"Running integration phase: {phase} (round {round_number})"
        )

        speaking_order = turn_manager.get_speaking_order(phase, round_number)
        participants = turn_manager.get_phase_participants(phase)

        if phase == "current_state_mapping":
            await self._run_current_state_mapping(
                agents, speaking_order, participants, round_state, visibility
            )
        elif phase == "future_state_vision":
            await self._run_future_state_vision(
                agents, speaking_order, participants, round_state, visibility
            )
        elif phase == "gap_analysis":
            await self._run_gap_analysis(
                agents, speaking_order, participants, round_state, visibility
            )
        elif phase == "initiative_prioritization":
            await self._run_initiative_prioritization(
                agents, speaking_order, participants, round_state, visibility
            )
        elif phase == "resource_allocation":
            await self._run_resource_allocation(
                agents, speaking_order, round_state, visibility
            )

        round_state.phase = phase
        round_state.phase_complete = True

        return round_state

    async def _run_current_state_mapping(
        self,
        agents: list[SimulationAgent],
        speaking_order: list[str],
        participants: list[str],
        round_state: RoundState,
        visibility: VisibilityManager,
    ):
        """Run current state mapping phase."""
        agent_map = {a.id: a for a in agents}

        for agent_id in speaking_order:
            if agent_id not in participants:
                continue

            agent = agent_map.get(agent_id)
            if not agent:
                continue

            message = await self._process_agent_turn(
                agent=agent,
                phase="current_state_mapping",
                round_number=round_state.round_number,
                visibility=visibility,
                round_state=round_state,
                context="Document the current state of your functional area.",
            )
            if message:
                round_state.messages.append(message)

    async def _run_future_state_vision(
        self,
        agents: list[SimulationAgent],
        speaking_order: list[str],
        participants: list[str],
        round_state: RoundState,
        visibility: VisibilityManager,
    ):
        """Run future state vision phase."""
        agent_map = {a.id: a for a in agents}

        for agent_id in speaking_order:
            if agent_id not in participants:
                continue

            agent = agent_map.get(agent_id)
            if not agent:
                continue

            message = await self._process_agent_turn(
                agent=agent,
                phase="future_state_vision",
                round_number=round_state.round_number,
                visibility=visibility,
                round_state=round_state,
                context="Describe the desired future state for your area.",
            )
            if message:
                round_state.messages.append(message)

    async def _run_gap_analysis(
        self,
        agents: list[SimulationAgent],
        speaking_order: list[str],
        participants: list[str],
        round_state: RoundState,
        visibility: VisibilityManager,
    ):
        """Run gap analysis phase."""
        agent_map = {a.id: a for a in agents}

        for agent_id in speaking_order:
            if agent_id not in participants:
                continue

            agent = agent_map.get(agent_id)
            if not agent:
                continue

            message = await self._process_agent_turn(
                agent=agent,
                phase="gap_analysis",
                round_number=round_state.round_number,
                visibility=visibility,
                round_state=round_state,
                context=(
                    "Identify gaps between current and future state "
                    "in your area."
                ),
            )
            if message:
                round_state.messages.append(message)

    async def _run_initiative_prioritization(
        self,
        agents: list[SimulationAgent],
        speaking_order: list[str],
        participants: list[str],
        round_state: RoundState,
        visibility: VisibilityManager,
    ):
        """Run initiative prioritization phase."""
        agent_map = {a.id: a for a in agents}

        for agent_id in speaking_order:
            if agent_id not in participants:
                continue

            agent = agent_map.get(agent_id)
            if not agent:
                continue

            message = await self._process_agent_turn(
                agent=agent,
                phase="initiative_prioritization",
                round_number=round_state.round_number,
                visibility=visibility,
                round_state=round_state,
                context=(
                    "Propose integration initiatives and prioritize by "
                    "impact and effort (High/Medium/Low for each)."
                ),
            )
            if message:
                round_state.messages.append(message)

                # Try to extract initiative info
                content = message.content
                initiative = {
                    "proposed_by": agent.name,
                    "description": content[:200],
                    "impact": self._extract_impact_level(content),
                    "effort": self._extract_effort_level(content),
                }
                self._initiatives.append(initiative)

    async def _run_resource_allocation(
        self,
        agents: list[SimulationAgent],
        speaking_order: list[str],
        round_state: RoundState,
        visibility: VisibilityManager,
    ):
        """Run resource allocation phase - CFO has veto power."""
        agent_map = {a.id: a for a in agents}

        # Find CFO
        cfo = None
        for agent in agents:
            if agent.archetype.id == "cfo":
                cfo = agent
                break

        # First, let executives propose allocations
        allocators = [
            aid for aid in speaking_order
            if aid in [a.id for a in agents
                       if a.archetype.id in ["ceo", "operations_head"]]
        ]

        for agent_id in allocators[:2]:
            agent = agent_map.get(agent_id)
            if not agent:
                continue

            message = await self._process_agent_turn(
                agent=agent,
                phase="resource_allocation",
                round_number=round_state.round_number,
                visibility=visibility,
                round_state=round_state,
                context="Propose resource allocation across initiatives.",
            )
            if message:
                round_state.messages.append(message)

        # CFO reviews and can veto
        if cfo:
            message = await self._process_agent_turn(
                agent=cfo,
                phase="resource_allocation",
                round_number=round_state.round_number,
                visibility=visibility,
                round_state=round_state,
                context=(
                    "Review proposed allocations. You have veto power "
                    "if budget is exceeded."
                ),
            )
            if message:
                round_state.messages.append(message)

                # Check for veto
                if ("veto" in message.content.lower()
                        or "exceed" in message.content.lower()):
                    self._cfo_veto_used = True

        round_state.decisions.append({
            "type": "resource_allocation",
            "cfo_veto_used": self._cfo_veto_used,
            "initiatives_count": len(self._initiatives),
        })

    def _extract_impact_level(self, content: str) -> str:
        """Extract impact level from content."""
        content_lower = content.lower()
        if "high impact" in content_lower or "high" in content_lower:
            return "high"
        elif "low impact" in content_lower or "low" in content_lower:
            return "low"
        return "medium"

    def _extract_effort_level(self, content: str) -> str:
        """Extract effort level from content."""
        content_lower = content.lower()
        if "high effort" in content_lower or "difficult" in content_lower:
            return "high"
        elif "low effort" in content_lower or "easy" in content_lower:
            return "low"
        return "medium"

    async def evaluate_round(self, round_state: RoundState) -> dict:
        """Evaluate integration round outcomes."""
        evaluation = {
            "round_number": round_state.round_number,
            "phase": round_state.phase,
            "message_count": len(round_state.messages),
            "initiatives_proposed": len(self._initiatives),
            "cfo_veto_used": self._cfo_veto_used,
            "budget_status": {
                "total": self._budget_total,
                "allocated": self._budget_allocated,
                "remaining": self._budget_total - self._budget_allocated,
            },
        }

        # Categorize initiatives by impact/effort
        quick_wins = [
            i for i in self._initiatives
            if i["impact"] == "high" and i["effort"] == "low"
        ]
        major_projects = [
            i for i in self._initiatives
            if i["impact"] == "high" and i["effort"] == "high"
        ]
        fill_ins = [
            i for i in self._initiatives
            if i["impact"] == "low"
        ]

        evaluation["priority_matrix"] = {
            "quick_wins": len(quick_wins),
            "major_projects": len(major_projects),
            "fill_ins": len(fill_ins),
        }

        return evaluation

    def get_phase_instruction(self, phase: str, agent_role: str) -> str:
        """Get phase-specific instruction for an agent."""
        instructions = {
            "current_state_mapping": (
                "Document the current state of your functional area. "
                "Be specific about processes, systems, and people."
            ),
            "future_state_vision": (
                "Describe the desired future state. What should this "
                "area look like post-integration?"
            ),
            "gap_analysis": (
                "Identify specific gaps between current and future state. "
                "What needs to change?"
            ),
            "initiative_prioritization": (
                "Propose integration initiatives. Rate each by impact "
                "(High/Medium/Low) and effort (High/Medium/Low)."
            ),
            "resource_allocation": (
                "Propose budget and resource allocation. If you're the CFO, "
                "you can veto if the total exceeds budget."
            ),
        }
        default = "Contribute to the integration planning."
        return instructions.get(phase, default)
