"""Tests for simulation data models."""

import pytest

from app.simulation.models import (
    AgentConfig,
    AgentState,
    EnvironmentType,
    RoundState,
    SimulationConfig,
    SimulationCreateRequest,
    SimulationMessage,
    SimulationState,
    SimulationStatus,
    SimulationSummary,
    SimulationUpdateRequest,
    VoteResult,
)


class TestSimulationStatus:
    def test_enum_values(self):
        assert SimulationStatus.CONFIGURING == "configuring"
        assert SimulationStatus.READY == "ready"
        assert SimulationStatus.RUNNING == "running"
        assert SimulationStatus.PAUSED == "paused"
        assert SimulationStatus.COMPLETED == "completed"
        assert SimulationStatus.FAILED == "failed"


class TestEnvironmentType:
    def test_enum_values(self):
        assert EnvironmentType.BOARDROOM == "boardroom"
        assert EnvironmentType.WAR_ROOM == "war_room"
        assert EnvironmentType.NEGOTIATION == "negotiation"
        assert EnvironmentType.INTEGRATION == "integration"


class TestAgentConfig:
    def test_auto_generates_id(self):
        config = AgentConfig(name="CEO", archetype_id="ceo")
        assert config.id != ""
        assert len(config.id) == 36  # UUID format

    def test_preserves_provided_id(self):
        config = AgentConfig(id="custom-id", name="CEO", archetype_id="ceo")
        assert config.id == "custom-id"

    def test_default_customization(self):
        config = AgentConfig(name="CEO", archetype_id="ceo")
        assert config.customization == {}

    def test_customization(self):
        config = AgentConfig(
            name="CEO",
            archetype_id="ceo",
            customization={"style": "aggressive"},
        )
        assert config.customization["style"] == "aggressive"


class TestSimulationConfig:
    def test_auto_generates_id(self):
        config = SimulationConfig(name="Test Sim")
        assert config.id != ""

    def test_defaults(self):
        config = SimulationConfig(name="Test Sim")
        assert config.environment_type == EnvironmentType.BOARDROOM
        assert config.total_rounds == 10
        assert config.agents == []
        assert config.parameters == {}
        assert config.playbook_id is None
        assert config.seed_id is None

    def test_with_agents(self):
        config = SimulationConfig(
            name="Test Sim",
            agents=[
                AgentConfig(name="CEO", archetype_id="ceo"),
                AgentConfig(name="CFO", archetype_id="analyst"),
            ],
        )
        assert len(config.agents) == 2


class TestSimulationMessage:
    def test_auto_generates_id_and_timestamp(self):
        msg = SimulationMessage(
            round_number=1,
            phase="debate",
            agent_id="a1",
            agent_name="CEO",
            agent_role="Executive",
            content="I propose...",
        )
        assert msg.id != ""
        assert msg.timestamp != ""

    def test_default_values(self):
        msg = SimulationMessage(
            round_number=1,
            phase="debate",
            agent_id="a1",
            agent_name="CEO",
            agent_role="Executive",
            content="test",
        )
        assert msg.message_type == "statement"
        assert msg.visibility == "public"
        assert msg.target_agents == []


class TestRoundState:
    def test_defaults(self):
        state = RoundState(round_number=1, phase="opening")
        assert state.messages == []
        assert state.decisions == []
        assert state.phase_complete is False


class TestSimulationState:
    def test_auto_generates_timestamps(self):
        config = SimulationConfig(name="Test")
        state = SimulationState(config=config)
        assert state.created_at != ""
        assert state.updated_at != ""
        assert state.status == SimulationStatus.CONFIGURING
        assert state.current_round == 0
        assert state.rounds == []
        assert state.results_summary == {}


class TestSimulationCreateRequest:
    def test_minimal(self):
        req = SimulationCreateRequest(name="My Sim")
        assert req.name == "My Sim"
        assert req.environment_type == EnvironmentType.BOARDROOM
        assert req.total_rounds == 10

    def test_full(self):
        req = SimulationCreateRequest(
            name="Full Sim",
            description="A full test",
            playbook_id="pb-1",
            environment_type=EnvironmentType.WAR_ROOM,
            total_rounds=15,
            seed_id="seed-1",
            parameters={"temperature": 0.8},
        )
        assert req.playbook_id == "pb-1"
        assert req.parameters["temperature"] == 0.8


class TestSimulationUpdateRequest:
    def test_all_optional(self):
        req = SimulationUpdateRequest()
        assert req.name is None
        assert req.description is None
        assert req.agents is None
        assert req.total_rounds is None
        assert req.parameters is None


class TestVoteResult:
    def test_creation(self):
        vote = VoteResult(
            agent_id="a1",
            agent_name="CEO",
            vote="for",
            reasoning="I support this proposal",
        )
        assert vote.vote == "for"


class TestSimulationSummary:
    def test_creation(self):
        summary = SimulationSummary(
            id="sim-1",
            name="Test",
            status=SimulationStatus.COMPLETED,
            environment_type=EnvironmentType.BOARDROOM,
            current_round=10,
            total_rounds=10,
            agent_count=4,
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T01:00:00",
        )
        assert summary.status == SimulationStatus.COMPLETED
