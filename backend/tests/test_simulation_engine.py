"""Tests for the simulation engine (SimulationEngine).

All heavy dependencies (LLM provider, DB, SeedProcessor, archetypes)
are mocked so tests run fully offline.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.llm.inference_router import InferenceRouter
from app.personas.archetypes import (
    ArchetypeDefinition,
    DecisionSpeed,
    IncentiveType,
    InformationBias,
    RiskTolerance,
)
from app.simulation.engine import SimulationEngine
from app.simulation.models import (
    AgentConfig,
    EnvironmentType,
    RoundState,
    SimulationConfig,
    SimulationState,
    SimulationStatus,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def minimal_config():
    return SimulationConfig(
        name="Test Simulation",
        description="Unit test sim",
        environment_type=EnvironmentType.BOARDROOM,
        agents=[
            AgentConfig(name="CEO", archetype_id="ceo"),
        ],
        total_rounds=3,
    )


@pytest.fixture
def engine():
    return SimulationEngine()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_archetype() -> ArchetypeDefinition:
    """Return a real ArchetypeDefinition so Pydantic validation inside SimulationAgent passes."""
    return ArchetypeDefinition(
        id="ceo",
        name="CEO",
        role="Chief Executive Officer",
        description="CEO archetype for testing",
        authority_level=10,
        risk_tolerance=RiskTolerance.AGGRESSIVE,
        information_bias=InformationBias.BALANCED,
        decision_speed=DecisionSpeed.FAST,
        coalition_tendencies=0.7,
        incentive_structure=[IncentiveType.FINANCIAL, IncentiveType.REPUTATIONAL],
        behavioral_axioms=["Maximize shareholder value", "Act decisively"],
        system_prompt_template=("You are a CEO.\n\nROLE: {role}\n\n{seed_context}"),
    )


def _mock_llm_provider():
    provider = MagicMock()
    provider.generate = AsyncMock(return_value="Mock LLM response")
    return provider


# ---------------------------------------------------------------------------
# get_agent_router
# ---------------------------------------------------------------------------


class TestGetAgentRouter:
    def test_returns_none_when_simulation_missing(self, engine):
        assert engine.get_agent_router("unknown-id") is None

    def test_returns_none_when_agent_list_empty(self, engine):
        engine._agents["s1"] = []
        assert engine.get_agent_router("s1") is None

    def test_returns_none_when_index_out_of_range(self, engine):
        agent = MagicMock()
        agent.router = MagicMock()
        engine._agents["s1"] = [agent]
        assert engine.get_agent_router("s1", agent_index=1) is None

    def test_returns_router_for_agent_index(self, engine):
        r0 = MagicMock(spec=InferenceRouter)
        r1 = MagicMock(spec=InferenceRouter)
        a0 = MagicMock()
        a0.router = r0
        a1 = MagicMock()
        a1.router = r1
        engine._agents["s1"] = [a0, a1]
        assert engine.get_agent_router("s1", 0) is r0
        assert engine.get_agent_router("s1", 1) is r1


# ---------------------------------------------------------------------------
# create_simulation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestCreateSimulation:

    @patch("app.simulation.engine._get_llm_provider", return_value=MagicMock())
    @patch("app.simulation.engine.get_archetype", return_value=_mock_archetype())
    @patch("app.simulation.engine.SeedProcessor")
    async def test_creates_simulation_in_memory(self, mock_seed_cls, _mock_arch, _mock_llm, engine, minimal_config):
        mock_seed_cls.return_value.get_seed = AsyncMock(return_value=None)
        engine._repo.save = AsyncMock()

        sim = await engine.create_simulation(minimal_config)

        assert sim.config.id == minimal_config.id
        assert sim.status == SimulationStatus.READY
        assert sim.config.id in engine.simulations

    @patch("app.simulation.engine._get_llm_provider", return_value=MagicMock())
    @patch("app.simulation.engine.get_archetype", return_value=_mock_archetype())
    @patch("app.simulation.engine.SeedProcessor")
    async def test_persists_to_repo(self, mock_seed_cls, _mock_arch, _mock_llm, engine, minimal_config):
        mock_seed_cls.return_value.get_seed = AsyncMock(return_value=None)
        engine._repo.save = AsyncMock()

        await engine.create_simulation(minimal_config)

        engine._repo.save.assert_called_once()

    @patch("app.simulation.engine._get_llm_provider", return_value=MagicMock())
    @patch("app.simulation.engine.get_archetype", return_value=_mock_archetype())
    @patch("app.simulation.engine.SeedProcessor")
    async def test_syncs_description_from_parameters_simulation_requirement(
        self, mock_seed_cls, _mock_arch, _mock_llm, engine
    ):
        """Wizard / API clients often send the objective only in parameters."""
        mock_seed_cls.return_value.get_seed = AsyncMock(return_value=None)
        engine._repo.save = AsyncMock()
        cfg = SimulationConfig(
            name="Test Simulation",
            description="",
            environment_type=EnvironmentType.BOARDROOM,
            agents=[AgentConfig(name="CEO", archetype_id="ceo")],
            total_rounds=3,
            parameters={"simulation_requirement": "Win the market in Q3"},
        )
        sim = await engine.create_simulation(cfg)
        assert sim.config.description.strip() == "Win the market in Q3"

    @patch("app.simulation.engine._get_llm_provider", return_value=MagicMock())
    @patch("app.simulation.engine.get_archetype", return_value=None)  # archetype not found
    @patch("app.simulation.engine.SeedProcessor")
    async def test_skips_agent_when_archetype_missing(
        self, mock_seed_cls, _mock_arch, _mock_llm, engine, minimal_config
    ):
        mock_seed_cls.return_value.get_seed = AsyncMock(return_value=None)
        engine._repo.save = AsyncMock()

        sim = await engine.create_simulation(minimal_config)

        # Agent is skipped, sim still created
        assert sim.config.id in engine.simulations
        assert engine._agents[sim.config.id] == []

    @patch("app.simulation.engine._get_llm_provider", return_value=MagicMock())
    @patch("app.simulation.engine.get_archetype", return_value=_mock_archetype())
    @patch("app.simulation.engine.SeedProcessor")
    async def test_cleans_up_memory_when_repo_save_fails(
        self, mock_seed_cls, _mock_arch, _mock_llm, engine, minimal_config
    ):
        mock_seed_cls.return_value.get_seed = AsyncMock(return_value=None)
        engine._repo.save = AsyncMock(side_effect=RuntimeError("disk full"))
        engine._repo.delete = AsyncMock(return_value=True)

        with pytest.raises(RuntimeError, match="disk full"):
            await engine.create_simulation(minimal_config)

        assert minimal_config.id not in engine.simulations
        assert minimal_config.id not in engine._agents
        engine._repo.delete.assert_called()

    @patch("app.simulation.engine._get_llm_provider", return_value=MagicMock())
    @patch("app.simulation.engine.get_archetype", return_value=_mock_archetype())
    @patch("app.simulation.engine.SeedProcessor")
    @patch("app.simulation.engine.SimulationMemoryManager")
    async def test_cleans_up_when_memory_manager_init_fails(
        self, mock_mm_cls, mock_seed_cls, _mock_arch, _mock_llm, engine, minimal_config
    ):
        mock_seed_cls.return_value.get_seed = AsyncMock(return_value=None)
        engine._repo.save = AsyncMock()
        mock_mm_cls.side_effect = RuntimeError("OOM")
        engine._repo.delete = AsyncMock(return_value=True)

        with pytest.raises(RuntimeError, match="OOM"):
            await engine.create_simulation(minimal_config)

        assert minimal_config.id not in engine.simulations
        engine._repo.delete.assert_called_once()


# ---------------------------------------------------------------------------
# _load_seed_context
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestLoadSeedContext:

    @patch("app.simulation.engine.SeedProcessor")
    async def test_returns_empty_when_no_seeds(self, mock_seed_cls, engine, minimal_config):
        minimal_config.seed_ids = []
        minimal_config.seed_id = None
        mock_seed_cls.return_value.get_seed = AsyncMock(return_value=None)

        result = await engine._load_seed_context(minimal_config)
        assert result == ""

    @patch("app.simulation.engine.SeedProcessor")
    async def test_returns_inline_seed_material_fallback(self, mock_seed_cls, engine, minimal_config):
        minimal_config.seed_ids = []
        minimal_config.seed_id = None
        minimal_config.parameters = {"seed_material": "inline context"}
        mock_seed_cls.return_value.get_seed = AsyncMock(return_value=None)

        result = await engine._load_seed_context(minimal_config)
        assert result == "inline context"

    @patch("app.simulation.engine.SeedProcessor")
    async def test_concatenates_multiple_seeds(self, mock_seed_cls, engine, minimal_config):
        seed1 = MagicMock()
        seed1.filename = "doc1.pdf"
        seed1.processed_content = "Content A"
        seed1.raw_content = ""

        seed2 = MagicMock()
        seed2.filename = "doc2.pdf"
        seed2.processed_content = "Content B"
        seed2.raw_content = ""

        minimal_config.seed_ids = ["id1", "id2"]
        minimal_config.seed_id = None
        mock_seed_cls.return_value.get_seed = AsyncMock(side_effect=[seed1, seed2])

        result = await engine._load_seed_context(minimal_config)
        assert "Content A" in result
        assert "Content B" in result
        assert "doc1.pdf" in result

    @patch("app.simulation.engine.SeedProcessor")
    async def test_skips_missing_seed(self, mock_seed_cls, engine, minimal_config):
        minimal_config.seed_ids = ["missing-id"]
        minimal_config.seed_id = None
        mock_seed_cls.return_value.get_seed = AsyncMock(return_value=None)
        minimal_config.parameters = {}

        result = await engine._load_seed_context(minimal_config)
        assert result == ""


# ---------------------------------------------------------------------------
# get_simulation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestGetSimulation:

    @patch("app.simulation.engine._get_llm_provider", return_value=MagicMock())
    @patch("app.simulation.engine.get_archetype", return_value=_mock_archetype())
    @patch("app.simulation.engine.SeedProcessor")
    async def test_returns_in_memory_sim(self, mock_seed_cls, _arch, _llm, engine, minimal_config):
        mock_seed_cls.return_value.get_seed = AsyncMock(return_value=None)
        engine._repo.save = AsyncMock()
        sim = await engine.create_simulation(minimal_config)

        result = await engine.get_simulation(sim.config.id)
        assert result is sim

    async def test_fallback_to_db(self, engine):
        engine._repo.get = AsyncMock(return_value=None)
        result = await engine.get_simulation("nonexistent")
        assert result is None


# ---------------------------------------------------------------------------
# pause / resume
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestPauseResume:

    async def test_pause_clears_running_flag_and_updates_status(self, engine, minimal_config):
        sim = SimulationState(config=minimal_config, status=SimulationStatus.RUNNING)
        engine.simulations["sim-1"] = sim
        engine.running_tasks["sim-1"] = True
        engine._repo.save = AsyncMock()

        await engine.pause_simulation("sim-1")

        assert engine.running_tasks["sim-1"] is False
        assert sim.status == SimulationStatus.PAUSED
        engine._repo.save.assert_called_once()

    async def test_resume_raises_if_not_paused(self, engine, minimal_config):
        sim = SimulationState(config=minimal_config, status=SimulationStatus.RUNNING)
        engine.simulations["sim-1"] = sim

        with pytest.raises(ValueError, match="not paused"):
            await engine.resume_simulation("sim-1")

    async def test_resume_raises_if_not_found(self, engine):
        with pytest.raises(ValueError, match="not found"):
            await engine.resume_simulation("nonexistent")

    @patch("app.simulation.engine._get_llm_provider", return_value=MagicMock())
    @patch("app.simulation.engine.get_archetype", return_value=_mock_archetype())
    @patch("app.simulation.engine.SeedProcessor")
    async def test_persists_after_each_completed_round(self, mock_seed_cls, _arch, _llm, engine, minimal_config):
        """Regression: save after every round must not be gated on running_tasks
        or pause/resume can lose the last completed round in the DB."""
        mock_seed_cls.return_value.get_seed = AsyncMock(return_value=None)
        engine._repo.save = AsyncMock()

        async def fake_run_round(sim_state, round_number, **kwargs):
            sim_state.rounds.append(RoundState(round_number=round_number, phase="done", messages=[]))

        minimal_config.total_rounds = 2
        sim = await engine.create_simulation(minimal_config)
        sid = sim.config.id

        for agent in engine._agents[sid]:
            agent.update_stance = AsyncMock()

        engine._memory_managers[sid].record_round = AsyncMock()
        engine._run_round = AsyncMock(side_effect=fake_run_round)

        await engine.run_simulation(sid)

        assert sim.status == SimulationStatus.COMPLETED
        assert len(sim.rounds) == 2
        # create + after round 1 + after round 2 + completed
        assert engine._repo.save.call_count >= 4


# ---------------------------------------------------------------------------
# stop_simulation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestStopSimulation:

    async def test_stop_marks_cancelled_even_with_rounds(self, engine, minimal_config):
        """User stop is an abort — never COMPLETED (that is only natural run finish)."""
        sim = SimulationState(config=minimal_config, status=SimulationStatus.RUNNING)
        sim.rounds.append(RoundState(round_number=1, phase="done", messages=[]))
        engine.simulations["sim-1"] = sim
        engine.running_tasks["sim-1"] = True
        engine._repo.save = AsyncMock()

        result = await engine.stop_simulation("sim-1")

        assert result is True
        assert engine.running_tasks["sim-1"] is False
        assert sim.status == SimulationStatus.CANCELLED
        engine._repo.save.assert_called_once()

    async def test_stop_populates_results_summary_if_none(self, engine, minimal_config):
        sim = SimulationState(config=minimal_config, status=SimulationStatus.RUNNING)
        sim.rounds.append(RoundState(round_number=1, phase="done", messages=[]))
        sim.results_summary = None
        engine.simulations["sim-1"] = sim
        engine.running_tasks["sim-1"] = True
        engine._repo.save = AsyncMock()

        # Partial results compiled on stop; status remains cancelled (user abort)
        await engine.stop_simulation("sim-1")
        assert sim.status == SimulationStatus.CANCELLED
        assert sim.results_summary is not None
        assert "simulation_id" in sim.results_summary

    async def test_stop_returns_false_for_nonexistent(self, engine):
        engine._repo.get = AsyncMock(return_value=None)
        result = await engine.stop_simulation("nonexistent")
        assert result is False

    async def test_stop_before_any_run_marks_cancelled(self, engine, minimal_config):
        """End on a never-started sim must not mark completed."""
        sim = SimulationState(config=minimal_config, status=SimulationStatus.READY)
        engine.simulations["sim-1"] = sim
        engine.running_tasks["sim-1"] = False
        engine._repo.save = AsyncMock()

        result = await engine.stop_simulation("sim-1")

        assert result is True
        assert sim.status == SimulationStatus.CANCELLED
        assert sim.results_summary == {}
        engine._repo.save.assert_called_once()

    async def test_stop_running_without_rounds_marks_cancelled(self, engine, minimal_config):
        """Stopping immediately after start (no round persisted) is not 'completed'."""
        sim = SimulationState(config=minimal_config, status=SimulationStatus.RUNNING)
        engine.simulations["sim-1"] = sim
        engine.running_tasks["sim-1"] = True
        engine._repo.save = AsyncMock()

        result = await engine.stop_simulation("sim-1")

        assert result is True
        assert sim.status == SimulationStatus.CANCELLED
        assert sim.results_summary == {}


@pytest.mark.asyncio
class TestRunSimulationStopPreservesCancelled:
    """Cooperative stop must not be overwritten by PAUSED or COMPLETED."""

    @patch("app.simulation.engine._get_llm_provider", return_value=MagicMock())
    @patch("app.simulation.engine.get_archetype", return_value=_mock_archetype())
    @patch("app.simulation.engine.SeedProcessor")
    async def test_next_round_does_not_overwrite_cancelled_with_paused(
        self, mock_seed_cls, _arch, _llm, engine, minimal_config
    ):
        mock_seed_cls.return_value.get_seed = AsyncMock(return_value=None)
        engine._repo.save = AsyncMock()
        minimal_config.total_rounds = 2
        sim = await engine.create_simulation(minimal_config)
        sid = sim.config.id

        async def fake_round(**kwargs):
            sim_state = kwargs["sim_state"]
            rn = kwargs["round_number"]
            sim_state.rounds.append(RoundState(round_number=rn, phase="discussion", messages=[]))
            if rn == 1:
                await engine.stop_simulation(sid)

        engine._run_round = fake_round
        engine._memory_managers[sid] = None
        for ag in engine._agents[sid]:
            ag.update_stance = AsyncMock()

        await engine.run_simulation(sid)

        assert engine.simulations[sid].status == SimulationStatus.CANCELLED

    @patch("app.simulation.engine._get_llm_provider", return_value=MagicMock())
    @patch("app.simulation.engine.get_archetype", return_value=_mock_archetype())
    @patch("app.simulation.engine.SeedProcessor")
    async def test_final_round_stop_not_marked_completed(self, mock_seed_cls, _arch, _llm, engine, minimal_config):
        mock_seed_cls.return_value.get_seed = AsyncMock(return_value=None)
        engine._repo.save = AsyncMock()
        minimal_config.total_rounds = 1
        sim = await engine.create_simulation(minimal_config)
        sid = sim.config.id

        async def fake_round(**kwargs):
            sim_state = kwargs["sim_state"]
            rn = kwargs["round_number"]
            sim_state.rounds.append(RoundState(round_number=rn, phase="discussion", messages=[]))
            await engine.stop_simulation(sid)

        engine._run_round = fake_round
        engine._memory_managers[sid] = None
        for ag in engine._agents[sid]:
            ag.update_stance = AsyncMock()

        await engine.run_simulation(sid)

        assert engine.simulations[sid].status == SimulationStatus.CANCELLED


# ---------------------------------------------------------------------------
# delete_simulation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestDeleteSimulation:

    @patch("app.simulation.engine._get_llm_provider", return_value=MagicMock())
    @patch("app.simulation.engine.get_archetype", return_value=_mock_archetype())
    @patch("app.simulation.engine.SeedProcessor")
    async def test_delete_removes_from_memory(self, mock_seed_cls, _arch, _llm, engine, minimal_config):
        mock_seed_cls.return_value.get_seed = AsyncMock(return_value=None)
        engine._repo.save = AsyncMock()
        engine._repo.delete = AsyncMock(return_value=True)

        sim = await engine.create_simulation(minimal_config)
        sid = sim.config.id

        # Set up memory manager mock
        mm = MagicMock()
        mm.clear_memories = AsyncMock()
        engine._memory_managers[sid] = mm

        result = await engine.delete_simulation(sid)

        assert result is True
        assert sid not in engine.simulations
        assert sid not in engine._agents

    async def test_delete_nonexistent_returns_false(self, engine):
        engine._repo.delete = AsyncMock(return_value=False)
        result = await engine.delete_simulation("ghost-id")
        assert result is False


# ---------------------------------------------------------------------------
# _compile_results
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestCompileResults:

    async def test_results_has_required_keys(self, engine, minimal_config):
        sim = SimulationState(
            config=minimal_config,
            status=SimulationStatus.COMPLETED,
        )
        sim.current_round = 3

        results = await engine._compile_results(sim)

        for key in ("simulation_id", "name", "total_rounds", "total_messages", "agents", "rounds"):
            assert key in results, f"Missing key: {key}"

    async def test_results_total_messages_zero_when_no_rounds(self, engine, minimal_config):
        sim = SimulationState(config=minimal_config, status=SimulationStatus.COMPLETED)
        sim.current_round = 0

        results = await engine._compile_results(sim)
        assert results["total_messages"] == 0
