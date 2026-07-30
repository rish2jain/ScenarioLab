"""Smoke tests for simulation environment registry and phase helpers."""

import pytest

from app.simulation.environments import (
    ENVIRONMENTS,
    BoardroomEnvironment,
    IntegrationEnvironment,
    NegotiationEnvironment,
    WarRoomEnvironment,
    get_environment,
)
from app.simulation.models import EnvironmentType, RoundState


@pytest.mark.parametrize(
    ("env_type", "expected_cls", "first_phase"),
    [
        (EnvironmentType.BOARDROOM, BoardroomEnvironment, "presentation"),
        (EnvironmentType.WAR_ROOM, WarRoomEnvironment, "intel_briefing"),
        (EnvironmentType.NEGOTIATION, NegotiationEnvironment, "position_statements"),
        (EnvironmentType.INTEGRATION, IntegrationEnvironment, "current_state_mapping"),
    ],
)
def test_get_environment_registry(env_type, expected_cls, first_phase):
    cls = get_environment(env_type)
    assert cls is expected_cls
    env = cls()
    assert env.env_type == env_type
    assert env.phases[0] == first_phase
    assert env.get_first_phase() == first_phase
    assert env.get_next_phase(first_phase) == env.phases[1]
    assert env.is_final_phase(env.phases[-1]) is True
    assert env.is_final_phase(first_phase) is False


def test_get_environment_unknown_falls_back_to_boardroom():
    assert get_environment("not-a-valid-environment") is BoardroomEnvironment  # type: ignore[arg-type]
    assert EnvironmentType.BOARDROOM in ENVIRONMENTS


def test_boardroom_phase_instruction_defaults():
    env = BoardroomEnvironment()
    text = env.get_phase_instruction("presentation", "CEO")
    assert "Present" in text or "present" in text.lower()


@pytest.mark.asyncio
async def test_boardroom_evaluate_round_with_vote():
    env = BoardroomEnvironment()
    state = RoundState(round_number=1, phase="vote")
    state.decisions.append(
        {
            "type": "vote",
            "result": {"result": "passed", "for": 3, "against": 1},
        }
    )
    evaluation = await env.evaluate_round(state)
    assert evaluation["message_count"] == 0
    assert evaluation["outcome"] == "accepted"
    assert evaluation["vote_result"]["result"] == "passed"


@pytest.mark.asyncio
async def test_war_room_evaluate_round_smoke():
    env = WarRoomEnvironment()
    state = RoundState(round_number=2, phase="decision")
    evaluation = await env.evaluate_round(state)
    assert evaluation["round_number"] == 2
    assert "message_count" in evaluation
