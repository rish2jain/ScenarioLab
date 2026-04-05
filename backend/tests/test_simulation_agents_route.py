"""GET /api/simulations/{id}/agents — role vs name semantics."""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.simulation.models import (
    AgentConfig,
    AgentState,
    EnvironmentType,
    SimulationConfig,
    SimulationState,
    SimulationStatus,
)


def test_agents_endpoint_role_is_archetype_not_display_name():
    """`role` is the archetype job title; `name` is the user-facing display name."""
    sim_id = "sim-agents-route-test"
    cfg = AgentConfig(
        id="agent-1",
        name="Jordan Lee — Custom Label",
        archetype_id="ceo",
    )
    state = SimulationState(
        config=SimulationConfig(
            id=sim_id,
            name="Sim",
            playbook_id=None,
            environment_type=EnvironmentType.BOARDROOM,
            agents=[cfg],
            total_rounds=1,
        ),
        status=SimulationStatus.COMPLETED,
        agents=[
            AgentState(
                id="agent-1",
                name="Jordan Lee — Custom Label",
                archetype_id="ceo",
                persona_prompt="...",
            )
        ],
    )
    with patch(
        "app.simulation.router.simulation_engine.get_simulation",
        new=AsyncMock(return_value=state),
    ):
        with TestClient(app) as client:
            r = client.get(f"/api/simulations/{sim_id}/agents")

    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["name"] == "Jordan Lee — Custom Label"
    assert body[0]["role"] == "CEO"
    assert body[0]["archetype"] == "ceo"
