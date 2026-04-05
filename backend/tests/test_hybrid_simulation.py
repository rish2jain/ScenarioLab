"""Integration tests for hybrid inference wiring."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.llm.inference_router import InferenceRouter
from app.llm.provider import LLMMessage, LLMResponse
from app.personas.archetypes import (
    ArchetypeDefinition,
    DecisionSpeed,
    IncentiveType,
    InformationBias,
    RiskTolerance,
)
from app.simulation import engine as sim_engine_module
from app.simulation.agent import SimulationAgent
from app.simulation.engine import SimulationEngine
from app.simulation.models import (
    AgentConfig,
    EnvironmentType,
    SimulationConfig,
    SimulationState,
    SimulationStatus,
)
from app.simulation.monte_carlo import MonteCarloConfig, MonteCarloRunner


def _mock_archetype() -> ArchetypeDefinition:
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
        system_prompt_template="You are a CEO.\n\nROLE: {role}\n\n{seed_context}",
    )


@pytest.fixture
def engine():
    return SimulationEngine()


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


@pytest.mark.asyncio
class TestCreateSimulationInjectedRouter:
    @patch("app.simulation.engine.InferenceRouter.create", new_callable=AsyncMock)
    @patch("app.simulation.engine.get_local_llm_provider", return_value=None)
    @patch("app.simulation.engine._get_llm_provider", return_value=MagicMock())
    @patch("app.simulation.engine.get_archetype", return_value=_mock_archetype())
    @patch("app.simulation.engine.SeedProcessor")
    async def test_skips_inference_router_create_when_injected(
        self,
        mock_seed_cls,
        _mock_arch,
        _mock_llm,
        _mock_local,
        mock_ir_create,
        engine,
        minimal_config,
    ):
        mock_seed_cls.return_value.get_seed = AsyncMock(return_value=None)
        engine._repo.save = AsyncMock()
        cloud = MagicMock()
        prebuilt = InferenceRouter(cloud, None, "cloud", 1)

        sim_state = await engine.create_simulation(
            minimal_config,
            inference_router=prebuilt,
        )

        mock_ir_create.assert_not_called()
        sim_id = sim_state.config.id
        agents = engine._agents[sim_id]
        assert len(agents) == 1
        assert agents[0].router is prebuilt


@pytest.mark.asyncio
class TestLocalProviderIgnoresCloudModelOverride:
    @patch("app.simulation.engine.InferenceRouter.create", new_callable=AsyncMock)
    @patch("app.simulation.engine.get_local_llm_provider", return_value=MagicMock())
    @patch("app.simulation.engine._get_llm_provider", return_value=MagicMock())
    @patch("app.simulation.engine.get_archetype", return_value=_mock_archetype())
    @patch("app.simulation.engine.SeedProcessor")
    async def test_wizard_cloud_model_not_passed_to_local(
        self,
        mock_seed_cls,
        _mock_arch,
        _mock_llm,
        mock_get_local,
        mock_ir_create,
        engine,
        minimal_config,
    ):
        """parameters.model selects the cloud LLM; local tier must use LOCAL_LLM_* only."""
        mock_seed_cls.return_value.get_seed = AsyncMock(return_value=None)
        engine._repo.save = AsyncMock()
        mock_ir_create.return_value = InferenceRouter(MagicMock(), MagicMock(), "hybrid", 1)
        minimal_config.parameters = {
            "model": "gpt-4o-2024-08-06",
            "inference_mode": "hybrid",
        }

        await engine.create_simulation(minimal_config)

        mock_get_local.assert_called_once_with()


def _ok_llm_response() -> LLMResponse:
    return LLMResponse(content="ok", model="m", provider="t", usage=None)


@pytest.mark.asyncio
class TestAgentExemplarInjection:
    """Spec 9.1: exemplar message position for hybrid vs cloud."""

    async def test_agent_injects_exemplars(self):
        cloud = MagicMock()
        cloud.provider_name = "cloud"
        cloud.generate = AsyncMock(return_value=_ok_llm_response())
        local = MagicMock()
        local.provider_name = "local"
        local.generate = AsyncMock(return_value=_ok_llm_response())

        router = InferenceRouter(cloud, local, "hybrid", cloud_rounds=1)
        router.store_exemplar("a1", [], stance_text="Calibrated stance.")

        agent = SimulationAgent(
            AgentConfig(id="a1", name="CEO", archetype_id="ceo"),
            _mock_archetype(),
            router,
        )
        messages = [
            LLMMessage(role="system", content="system prompt"),
            LLMMessage(role="user", content="context"),
        ]
        await agent._throttled_generate(list(messages), round_number=2, task_type="response")

        local.generate.assert_awaited()
        out = local.generate.await_args.kwargs["messages"]
        assert out[0].role == "system"
        assert "STYLE CALIBRATION" in out[1].content
        assert out[1].role == "user"

    async def test_agent_no_exemplars_in_cloud_mode(self):
        cloud = MagicMock()
        cloud.provider_name = "cloud"
        cloud.generate = AsyncMock(return_value=_ok_llm_response())
        router = InferenceRouter(cloud, None, "cloud", cloud_rounds=1)
        router.store_exemplar("a1", [], stance_text="ignored in cloud")

        agent = SimulationAgent(
            AgentConfig(id="a1", name="CEO", archetype_id="ceo"),
            _mock_archetype(),
            router,
        )
        messages = [
            LLMMessage(role="system", content="system prompt"),
            LLMMessage(role="user", content="context"),
        ]
        await agent._throttled_generate(list(messages), round_number=2, task_type="response")

        cloud.generate.assert_awaited()
        out = cloud.generate.await_args.kwargs["messages"]
        assert not any("STYLE CALIBRATION" in m.content for m in out)

    async def test_agent_exemplar_uses_only_exemplars_when_messages_empty(self):
        cloud = MagicMock()
        local = MagicMock()
        local.generate = AsyncMock(return_value=_ok_llm_response())

        router = InferenceRouter(cloud, local, "hybrid", cloud_rounds=1)
        router.store_exemplar("a1", [], stance_text="Calibrated stance.")

        agent = SimulationAgent(
            AgentConfig(id="a1", name="CEO", archetype_id="ceo"),
            _mock_archetype(),
            router,
        )
        await agent._throttled_generate([], round_number=2, task_type="response")

        local.generate.assert_awaited()
        out = local.generate.await_args.kwargs["messages"]
        assert len(out) == 1
        assert "STYLE CALIBRATION" in out[0].content

    async def test_agent_exemplar_prepends_when_first_not_system(self):
        cloud = MagicMock()
        local = MagicMock()
        local.generate = AsyncMock(return_value=_ok_llm_response())

        router = InferenceRouter(cloud, local, "hybrid", cloud_rounds=1)
        router.store_exemplar("a1", [], stance_text="Calibrated stance.")

        agent = SimulationAgent(
            AgentConfig(id="a1", name="CEO", archetype_id="ceo"),
            _mock_archetype(),
            router,
        )
        messages = [
            LLMMessage(role="user", content="unexpected first"),
            LLMMessage(role="user", content="rest"),
        ]
        await agent._throttled_generate(list(messages), round_number=2, task_type="response")

        local.generate.assert_awaited()
        out = local.generate.await_args.kwargs["messages"]
        assert "STYLE CALIBRATION" in out[0].content
        assert out[0].role == "user"
        assert out[1].content == "unexpected first"


@pytest.mark.asyncio
class TestHybridSimulationEndToEnd:
    """Spec 9.2: mock cloud + local; round 1 cloud, round 2+ local with exemplars."""

    async def test_hybrid_simulation_end_to_end(self):
        cloud = MagicMock()
        cloud.provider_name = "cloud"
        cloud.generate = AsyncMock(return_value=_ok_llm_response())
        local = MagicMock()
        local.provider_name = "local"
        local.generate = AsyncMock(return_value=_ok_llm_response())

        router = InferenceRouter(cloud, local, "hybrid", cloud_rounds=1)
        router.store_exemplar("a1", [], stance_text="voice anchor")

        agent = SimulationAgent(
            AgentConfig(id="a1", name="CEO", archetype_id="ceo"),
            _mock_archetype(),
            router,
        )
        msgs = [
            LLMMessage(role="system", content="sys"),
            LLMMessage(role="user", content="u"),
        ]

        await agent._throttled_generate(list(msgs), round_number=1, task_type="response")
        cloud.generate.assert_awaited()
        local.generate.assert_not_awaited()
        cloud.reset_mock()
        local.reset_mock()

        await agent._throttled_generate(list(msgs), round_number=2, task_type="response")
        local.generate.assert_awaited()
        injected = local.generate.await_args.kwargs["messages"]
        assert "STYLE CALIBRATION" in injected[1].content


@pytest.mark.asyncio
class TestCloudOnlyBackwardCompat:
    """Spec 9.2: default config keeps cloud-only InferenceRouter mode."""

    @patch("app.simulation.engine.InferenceRouter.create", new_callable=AsyncMock)
    @patch("app.simulation.engine.get_local_llm_provider", return_value=None)
    @patch("app.simulation.engine._get_llm_provider", return_value=MagicMock())
    @patch("app.simulation.engine.get_archetype", return_value=_mock_archetype())
    @patch("app.simulation.engine.SeedProcessor")
    async def test_cloud_only_backward_compat(
        self,
        mock_seed_cls,
        _mock_arch,
        _mock_llm,
        _mock_local,
        mock_ir_create,
        engine,
        minimal_config,
        monkeypatch,
    ):
        monkeypatch.setattr(sim_engine_module.settings, "inference_mode", "cloud")
        mock_seed_cls.return_value.get_seed = AsyncMock(return_value=None)
        engine._repo.save = AsyncMock()
        cloud = MagicMock()
        mock_ir_create.return_value = InferenceRouter(cloud, None, "cloud", 1)

        await engine.create_simulation(minimal_config)

        mock_ir_create.assert_called_once()
        args, _kwargs = mock_ir_create.call_args
        assert args[2] == "cloud"


@pytest.mark.asyncio
class TestMonteCarloExemplarSharing:
    """Spec 9.2: iteration 2+ receives preloaded hybrid router from copy 1."""

    async def test_monte_carlo_exemplar_sharing(self):
        base = SimulationConfig(
            name="MC",
            description="",
            environment_type=EnvironmentType.BOARDROOM,
            agents=[AgentConfig(name="CEO", archetype_id="ceo")],
            total_rounds=1,
            parameters={"inference_mode": "hybrid"},
        )
        mc = MonteCarloConfig(base_config=base, iterations=2)

        cloud = MagicMock()
        local = MagicMock()
        hybrid_r = InferenceRouter(cloud, local, "hybrid", cloud_rounds=1)
        fake_agent = MagicMock()
        fake_agent.router = hybrid_r

        create_calls: list[InferenceRouter | None] = []

        engine = MagicMock()
        engine._agents = {}

        def get_agent_router(sim_id, agent_index=0):
            ag = engine._agents.get(sim_id)
            if ag is None or len(ag) <= agent_index:
                return None
            return ag[agent_index].router

        engine.get_agent_router = get_agent_router

        async def create_simulation(cfg, graph_memory_manager=None, *, inference_router=None):
            create_calls.append(inference_router)
            return SimulationState(
                config=cfg,
                status=SimulationStatus.COMPLETED,
                agents=[],
                rounds=[],
            )

        async def run_simulation(simulation_id: str):
            engine._agents[simulation_id] = [fake_agent]

        engine.create_simulation = AsyncMock(side_effect=create_simulation)
        engine.run_simulation = AsyncMock(side_effect=run_simulation)
        engine.get_simulation = AsyncMock(
            return_value=SimulationState(
                config=base,
                status=SimulationStatus.COMPLETED,
                agents=[],
                rounds=[],
            )
        )
        engine.delete_simulation = AsyncMock()

        runner = MonteCarloRunner(engine)
        runner.analytics_agent = MagicMock()
        runner.analytics_agent.analyze_simulation = AsyncMock(
            return_value=MagicMock(
                simulation_id="sim",
                compliance_violation_rate=0.0,
                time_to_consensus=1,
                policy_adoption_rate=0.5,
            )
        )

        await runner.run(mc)

        assert create_calls[0] is None
        assert create_calls[1] is not None
        assert create_calls[1].cloud_rounds == 0
        assert create_calls[1].get_provider(1, "response") is local
