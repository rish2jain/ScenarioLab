"""Information asymmetry controls for simulation environments."""

import logging
from typing import Any

from app.simulation.models import (
    AgentState,
    EnvironmentType,
    SimulationMessage,
)

logger = logging.getLogger(__name__)


class VisibilityManager:
    """Controls information visibility based on roles and environment rules."""

    def __init__(
        self,
        environment_type: EnvironmentType,
        visibility_rules: dict | None = None,
    ):
        self.env_type = environment_type
        self.rules = visibility_rules or self._default_rules()
        self._agent_roles: dict[str, str] = {}  # agent_id -> role

    def register_agents(self, agents: list[AgentState]):
        """Register agents with their roles for visibility decisions."""
        for agent in agents:
            self._agent_roles[agent.id] = agent.archetype_id

    def filter_messages_for_agent(
        self,
        agent: AgentState,
        messages: list[SimulationMessage],
    ) -> list[SimulationMessage]:
        """Filter messages visible to a specific agent based on rules."""
        visible = []

        for msg in messages:
            # Always see own messages
            if msg.agent_id == agent.id:
                visible.append(msg)
                continue

            # Public messages visible to all
            if msg.visibility == "public":
                visible.append(msg)
                continue

            # Private messages only to targets
            if msg.visibility == "private":
                if agent.id in msg.target_agents:
                    visible.append(msg)
                continue

            # Coalition messages
            if msg.visibility == "coalition":
                if self._is_coalition_member(agent, msg.agent_id):
                    visible.append(msg)
                continue

            # Role-based filtering per environment
            if self._can_see_by_role(agent, msg):
                visible.append(msg)

        return visible

    def can_send_private(
        self,
        sender: AgentState,
        target: AgentState,
    ) -> bool:
        """Check if sender can send private messages to target."""
        # Most environments allow private messages between any agents
        # with some restrictions

        if self.env_type == EnvironmentType.NEGOTIATION:
            # In negotiations, private caucuses are allowed
            return True

        if self.env_type == EnvironmentType.BOARDROOM:
            # Boardroom allows private caucuses between rounds
            return True

        if self.env_type == EnvironmentType.WAR_ROOM:
            # War room: CRO can message anyone about compliance
            if sender.archetype_id == "cro":
                return True
            # Otherwise, need authority level check
            return True

        if self.env_type == EnvironmentType.INTEGRATION:
            # Integration: workstream leads can message within workstream
            return True

        return True

    def _is_coalition_member(
        self, agent: AgentState, other_agent_id: str
    ) -> bool:
        """Check if another agent is in the same coalition."""
        return other_agent_id in agent.coalition_members

    def _can_see_by_role(
        self,
        viewer: AgentState,
        message: SimulationMessage,
    ) -> bool:
        """Check if viewer can see message based on role-based rules."""
        viewer_role = viewer.archetype_id
        _ = self._agent_roles.get(message.agent_id, "")  # For future use

        if self.env_type == EnvironmentType.WAR_ROOM:
            # CRO sees all risk-related messages
            if viewer_role == "cro":
                return True
            # CFO sees all financial messages
            if viewer_role == "cfo":
                if ("budget" in message.content.lower()
                        or "cost" in message.content.lower()):
                    return True

        if self.env_type == EnvironmentType.NEGOTIATION:
            # Mediator sees all
            if viewer_role == "mediator":
                return True

        return False

    def _default_rules(self) -> dict[str, Any]:
        """Default visibility rules per environment type."""
        rules = {
            EnvironmentType.BOARDROOM: {
                "description": (
                    "All see same materials, private caucuses between rounds"
                ),
                "public_by_default": True,
                "private_allowed": True,
                "coalition_allowed": True,
                "role_visibility": {
                    "ceo": "all",  # CEO sees everything
                    "board_member": "all",
                },
            },
            EnvironmentType.WAR_ROOM: {
                "description": (
                    "Role-based access (CRO sees full risk, BU heads see ops)"
                ),
                "public_by_default": False,
                "private_allowed": True,
                "coalition_allowed": True,
                "role_visibility": {
                    "cro": "all",  # CRO sees all risk info
                    "cfo": "financial",  # CFO sees financial info
                    "operations_head": "operational",  # Ops sees ops info
                },
            },
            EnvironmentType.NEGOTIATION: {
                "description": "Bilateral only, mediator sees all",
                "public_by_default": False,
                "private_allowed": True,
                "coalition_allowed": False,
                "role_visibility": {
                    "mediator": "all",  # Mediator sees all
                },
            },
            EnvironmentType.INTEGRATION: {
                "description": (
                    "Workstream leads see detail, execs see summary"
                ),
                "public_by_default": False,
                "private_allowed": True,
                "coalition_allowed": True,
                "role_visibility": {
                    "ceo": "summary",  # CEO sees summary
                    "cfo": "budget",  # CFO sees budget details
                    "hr_head": "people",  # HR sees people details
                    "operations_head": "operational",  # Ops sees ops details
                },
            },
        }

        return rules.get(self.env_type, rules[EnvironmentType.BOARDROOM])

    def get_visible_context(
        self,
        agent: AgentState,
        messages: list[SimulationMessage],
    ) -> str:
        """Get a formatted context string of visible messages."""
        visible = self.filter_messages_for_agent(agent, messages)

        if not visible:
            return "No prior messages in this phase."

        context_parts = []
        for msg in visible:
            visibility_indicator = ""
            if msg.visibility == "private":
                visibility_indicator = " [private]"
            elif msg.visibility == "coalition":
                visibility_indicator = " [coalition]"

            context_parts.append(
                f"{msg.agent_name} ({msg.agent_role}){visibility_indicator}: "
                f"{msg.content}"
            )

        return "\n\n".join(context_parts)
