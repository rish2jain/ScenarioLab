"""Turn-taking management for simulation environments."""

import logging

from app.simulation.models import AgentState, EnvironmentType

logger = logging.getLogger(__name__)


class TurnManager:
    """Manages turn-taking order based on environment type."""

    def __init__(
        self,
        environment_type: EnvironmentType,
        agents: list[AgentState],
    ):
        self.env_type = environment_type
        self.agents = agents
        self._agent_map = {agent.id: agent for agent in agents}
        self._round_counter = 0

    def get_speaking_order(
        self,
        phase: str,
        round_number: int,
    ) -> list[str]:
        """Determine speaking order for current phase."""
        if self.env_type == EnvironmentType.BOARDROOM:
            return self._boardroom_order(phase, round_number)
        elif self.env_type == EnvironmentType.WAR_ROOM:
            return self._war_room_order(phase, round_number)
        elif self.env_type == EnvironmentType.NEGOTIATION:
            return self._negotiation_order(phase, round_number)
        elif self.env_type == EnvironmentType.INTEGRATION:
            return self._integration_order(phase, round_number)
        else:
            # Default: simple rotation
            return self._default_order(phase, round_number)

    def get_phase_participants(self, phase: str) -> list[str]:
        """Get agents who participate in this phase."""
        if self.env_type == EnvironmentType.BOARDROOM:
            return self._boardroom_participants(phase)
        elif self.env_type == EnvironmentType.WAR_ROOM:
            return self._war_room_participants(phase)
        elif self.env_type == EnvironmentType.NEGOTIATION:
            return self._negotiation_participants(phase)
        elif self.env_type == EnvironmentType.INTEGRATION:
            return self._integration_participants(phase)
        else:
            # Default: all agents participate
            return [agent.id for agent in self.agents]

    def _boardroom_order(self, phase: str, round_number: int) -> list[str]:
        """Formal rotation by authority (boardroom)."""
        # Sort by authority level (highest first)
        sorted_agents = sorted(
            self.agents,
            key=lambda a: self._get_authority_level(a),
            reverse=True,
        )

        if phase == "presentation":
            # CEO/proposer goes first
            return [a.id for a in sorted_agents]
        elif phase == "qa":
            # Strict rotation starting from highest authority
            return [a.id for a in sorted_agents]
        elif phase == "objection":
            # Anyone can raise objections
            return [a.id for a in sorted_agents]
        elif phase == "rebuttal":
            # Proposer addresses objections (assume first agent is proposer)
            return [sorted_agents[0].id] if sorted_agents else []
        elif phase == "vote":
            # All vote in authority order
            return [a.id for a in sorted_agents]
        else:
            return [a.id for a in sorted_agents]

    def _war_room_order(self, phase: str, round_number: int) -> list[str]:
        """Dynamic turn-taking based on authority/urgency (war room)."""

        # Priority: CRO for compliance, then by authority
        def priority_key(agent: AgentState) -> tuple:
            authority = self._get_authority_level(agent)
            # CRO gets priority in threat assessment
            if phase == "threat_assessment" and agent.archetype_id == "cro":
                return (0, -authority)  # Highest priority
            # CEO gets priority in decision
            if phase == "decision" and agent.archetype_id == "ceo":
                return (0, -authority)
            return (1, -authority)

        sorted_agents = sorted(self.agents, key=priority_key)
        return [a.id for a in sorted_agents]

    def _negotiation_order(self, phase: str, round_number: int) -> list[str]:
        """Bilateral exchanges (negotiation)."""
        # In negotiation, parties alternate
        parties = [a for a in self.agents if a.archetype_id != "mediator"]
        mediator = [a for a in self.agents if a.archetype_id == "mediator"]

        if phase == "position_statements":
            # Each party states position
            return [a.id for a in parties]
        elif phase == "private_caucus":
            # Mediator can talk to each party
            if mediator:
                return [mediator[0].id]
            return []
        elif phase == "counter_proposal":
            # Alternating proposals
            result = []
            for i in range(len(parties)):
                result.append(parties[i % len(parties)].id)
            return result
        elif phase == "red_line_identification":
            return [a.id for a in parties]
        elif phase == "agreement_check":
            return [a.id for a in parties]
        else:
            return [a.id for a in self.agents]

    def _integration_order(self, phase: str, round_number: int) -> list[str]:
        """Parallel workstreams with sync points (integration)."""
        # Group by functional area
        workstream_leads = [a for a in self.agents if a.archetype_id in ["hr_head", "operations_head", "cfo"]]
        execs = [a for a in self.agents if a.archetype_id in ["ceo", "strategy_vp"]]

        if phase in ["current_state_mapping", "gap_analysis"]:
            # Workstream leads provide input
            return [a.id for a in workstream_leads + execs]
        elif phase in ["future_state_vision", "initiative_prioritization"]:
            # Execs lead vision, workstream leads contribute
            return [a.id for a in execs + workstream_leads]
        elif phase == "resource_allocation":
            # CFO has veto power - goes last
            others = [a for a in self.agents if a.archetype_id != "cfo"]
            cfo = [a for a in self.agents if a.archetype_id == "cfo"]
            return [a.id for a in others + cfo]
        else:
            return [a.id for a in self.agents]

    def _default_order(self, phase: str, round_number: int) -> list[str]:
        """Default simple rotation."""
        # Rotate starting position each round
        agent_ids = [a.id for a in self.agents]
        if round_number > 0:
            start_idx = (round_number - 1) % len(agent_ids)
            return agent_ids[start_idx:] + agent_ids[:start_idx]
        return agent_ids

    def _boardroom_participants(self, phase: str) -> list[str]:
        """Get participants for boardroom phases."""
        if phase == "rebuttal":
            # Only proposer (assume CEO or first agent)
            for agent in self.agents:
                if agent.archetype_id == "ceo":
                    return [agent.id]
            return [self.agents[0].id] if self.agents else []
        elif phase == "vote":
            # Board members and executives vote
            return [a.id for a in self.agents if a.archetype_id in ["board_member", "ceo", "cfo", "activist_investor"]]
        else:
            return [a.id for a in self.agents]

    def _war_room_participants(self, phase: str) -> list[str]:
        """Get participants for war room phases."""
        if phase == "intel_briefing":
            # All participants
            return [a.id for a in self.agents]
        elif phase == "threat_assessment":
            # CRO and relevant executives
            return [a.id for a in self.agents if a.archetype_id in ["cro", "ceo", "cfo", "general_counsel"]]
        elif phase == "response_options":
            # Strategy and operations
            return [a.id for a in self.agents if a.archetype_id in ["strategy_vp", "operations_head", "ceo", "cfo"]]
        elif phase == "decision":
            # Decision makers
            return [a.id for a in self.agents if a.archetype_id in ["ceo", "cfo", "cro"]]
        elif phase == "action_assignment":
            # Operations and function heads
            return [a.id for a in self.agents if a.archetype_id in ["operations_head", "hr_head", "strategy_vp"]]
        else:
            return [a.id for a in self.agents]

    def _negotiation_participants(self, phase: str) -> list[str]:
        """Get participants for negotiation phases."""
        if phase == "private_caucus":
            # Only mediator participates actively
            mediators = [a for a in self.agents if a.archetype_id == "mediator"]
            return [m.id for m in mediators]
        else:
            # All parties participate
            return [a.id for a in self.agents]

    def _integration_participants(self, phase: str) -> list[str]:
        """Get participants for integration phases."""
        if phase == "current_state_mapping":
            # Workstream leads
            return [a.id for a in self.agents if a.archetype_id in ["hr_head", "operations_head", "cfo", "strategy_vp"]]
        elif phase == "future_state_vision":
            # Executives and strategy
            return [a.id for a in self.agents if a.archetype_id in ["ceo", "strategy_vp", "board_member"]]
        elif phase == "gap_analysis":
            # All functional leads
            return [
                a.id
                for a in self.agents
                if a.archetype_id in ["hr_head", "operations_head", "cfo", "strategy_vp", "general_counsel"]
            ]
        elif phase == "initiative_prioritization":
            # Strategy and executives
            return [a.id for a in self.agents if a.archetype_id in ["ceo", "strategy_vp", "operations_head"]]
        elif phase == "resource_allocation":
            # CFO and executives
            return [a.id for a in self.agents if a.archetype_id in ["cfo", "ceo", "operations_head"]]
        else:
            return [a.id for a in self.agents]

    def _get_authority_level(self, agent: AgentState) -> int:
        """Get authority level for an agent."""
        # Authority levels from archetypes (1-10)
        authority_map = {
            "ceo": 10,
            "cfo": 9,
            "board_member": 9,
            "cro": 8,
            "general_counsel": 8,
            "regulator": 8,
            "activist_investor": 7,
            "strategy_vp": 7,
            "operations_head": 7,
            "competitor_exec": 6,
            "hr_head": 6,
            "union_rep": 5,
            "media_stakeholder": 4,
        }
        return authority_map.get(agent.archetype_id, 5)

    def get_next_speaker(
        self,
        phase: str,
        round_number: int,
        current_speaker_id: str | None = None,
    ) -> str | None:
        """Get the next speaker in the sequence."""
        order = self.get_speaking_order(phase, round_number)

        if not order:
            return None

        if current_speaker_id is None:
            return order[0]

        try:
            current_idx = order.index(current_speaker_id)
            next_idx = current_idx + 1
            if next_idx < len(order):
                return order[next_idx]
            return None  # End of turn order
        except ValueError:
            return order[0]

    def is_phase_complete(
        self,
        phase: str,
        round_number: int,
        speakers_completed: list[str],
    ) -> bool:
        """Check if all participants have spoken in this phase."""
        participants = self.get_phase_participants(phase)
        return all(p in speakers_completed for p in participants)
