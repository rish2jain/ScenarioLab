"""Resume / DB reload: runtime SimulationAgent.state must match persisted AgentState."""

from unittest.mock import MagicMock

import pytest

from app.llm.inference_router import InferenceRouter
from app.personas.library import get_archetype
from app.simulation.agent import SimulationAgent
from app.simulation.engine import SimulationEngine
from app.simulation.models import (
    AgentConfig,
    AgentState,
    EnvironmentType,
    SimulationConfig,
    SimulationState,
    SimulationStatus,
)


@pytest.fixture
def engine() -> SimulationEngine:
    return SimulationEngine()


def test_bind_runtime_merges_persisted_agent_state(engine: SimulationEngine):
    archetype = get_archetype("ceo")
    assert archetype is not None

    cfg = AgentConfig(name="CEO", archetype_id="ceo")
    cloud = MagicMock()
    router = InferenceRouter(cloud, None, "cloud", 1)
    agent = SimulationAgent(
        config=cfg,
        archetype=archetype,
        inference_router=router,
        memory_manager=None,
    )
    assert agent.state.current_stance == ""

    sim_config = SimulationConfig(
        name="S",
        environment_type=EnvironmentType.BOARDROOM,
        agents=[cfg],
        total_rounds=3,
    )
    persisted = AgentState(
        id=agent.id,
        name=agent.name,
        archetype_id=agent.archetype.id,
        persona_prompt="ignored for this test",
        current_stance="Persisted from round 2",
        coalition_members=["ally-1"],
        vote_history=[{"vote": "for"}],
    )
    sim_state = SimulationState(
        config=sim_config,
        status=SimulationStatus.PAUSED,
        agents=[persisted],
        current_round=2,
    )

    engine._bind_runtime_agents_to_simulation_state(sim_state, [agent])

    assert agent.state.current_stance == "Persisted from round 2"
    assert agent.state.coalition_members == ["ally-1"]
    assert agent.state.vote_history == [{"vote": "for"}]
    assert sim_state.agents == [agent.state]
    assert sim_state.agents[0] is agent.state


def test_restore_hybrid_exemplars_from_snapshot(engine: SimulationEngine):
    """Pause/resume reload: exemplar snapshot repopulates the inference router."""
    archetype = get_archetype("ceo")
    assert archetype is not None

    cfg = AgentConfig(name="CEO", archetype_id="ceo")
    cloud = MagicMock()
    router = InferenceRouter(cloud, MagicMock(), "hybrid", cloud_rounds=1)
    router.store_exemplar(
        cfg.id,
        [],
        stance_text="primed stance",
    )
    snap = router.snapshot_exemplars()

    agent = SimulationAgent(
        config=cfg,
        archetype=archetype,
        inference_router=router,
        memory_manager=None,
    )

    sim_config = SimulationConfig(
        name="S",
        environment_type=EnvironmentType.BOARDROOM,
        agents=[cfg],
        total_rounds=3,
        parameters={"inference_mode": "hybrid"},
    )
    sim_state = SimulationState(
        config=sim_config,
        status=SimulationStatus.PAUSED,
        agents=[agent.state],
        hybrid_exemplar_snapshot=snap,
    )

    fresh = InferenceRouter(cloud, MagicMock(), "hybrid", cloud_rounds=1)
    assert not fresh.has_exemplars()
    fresh_agent = SimulationAgent(
        config=cfg,
        archetype=archetype,
        inference_router=fresh,
        memory_manager=None,
    )

    engine._restore_hybrid_exemplars_after_rehydrate(sim_state, [fresh_agent])
    assert fresh.has_exemplars()
    assert fresh.should_inject_exemplars(cfg.id, 2, "response") is True
