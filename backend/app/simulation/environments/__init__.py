"""Simulation environments package."""

from app.simulation.environments.base import BaseEnvironment
from app.simulation.environments.boardroom import BoardroomEnvironment
from app.simulation.environments.integration import IntegrationEnvironment
from app.simulation.environments.negotiation import NegotiationEnvironment
from app.simulation.environments.war_room import WarRoomEnvironment
from app.simulation.models import EnvironmentType

# Environment registry
ENVIRONMENTS = {
    EnvironmentType.BOARDROOM: BoardroomEnvironment,
    EnvironmentType.WAR_ROOM: WarRoomEnvironment,
    EnvironmentType.NEGOTIATION: NegotiationEnvironment,
    EnvironmentType.INTEGRATION: IntegrationEnvironment,
}


def get_environment(env_type: EnvironmentType) -> type[BaseEnvironment]:
    """Get environment class by type."""
    return ENVIRONMENTS.get(env_type, BoardroomEnvironment)


__all__ = [
    "BaseEnvironment",
    "BoardroomEnvironment",
    "WarRoomEnvironment",
    "NegotiationEnvironment",
    "IntegrationEnvironment",
    "get_environment",
    "ENVIRONMENTS",
]
