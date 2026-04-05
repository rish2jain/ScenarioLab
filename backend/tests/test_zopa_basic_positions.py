"""Tests for ZOPA heuristic (_extract_basic_positions) behavior."""

import pytest

from app.simulation.models import (
    AgentConfig,
    AgentState,
    EnvironmentType,
    RoundState,
    SimulationConfig,
    SimulationMessage,
    SimulationState,
    SimulationStatus,
)
from app.simulation.zopa import ZOPAAnalyzer


def _state_with_negotiation_message(content: str) -> SimulationState:
    """Boardroom env + no LLM forces heuristic extraction."""
    agent_id = "agent-1"
    config = SimulationConfig(
        name="t",
        environment_type=EnvironmentType.BOARDROOM,
        agents=[AgentConfig(id=agent_id, name="Buyer", archetype_id="buyer")],
    )
    agents = [
        AgentState(
            id=agent_id,
            name="Buyer",
            archetype_id="buyer",
            persona_prompt="p",
            current_stance="x",
        )
    ]
    rounds = [
        RoundState(
            round_number=1,
            phase="p",
            messages=[
                SimulationMessage(
                    round_number=1,
                    phase="p",
                    agent_id=agent_id,
                    agent_name="Buyer",
                    agent_role="buyer",
                    content=content,
                )
            ],
        )
    ]
    return SimulationState(
        config=config,
        status=SimulationStatus.COMPLETED,
        agents=agents,
        rounds=rounds,
    )


@pytest.mark.asyncio
async def test_red_lines_dedupe_multi_keyword_same_sentence() -> None:
    """Multiple keywords in one sentence must not duplicate the same span."""
    content = "We will not go below 10 and cannot accept less than that."
    analyzer = ZOPAAnalyzer(llm_provider=None)
    state = _state_with_negotiation_message(content)
    positions = await analyzer.extract_positions(state)
    assert len(positions) == 1
    red = positions[0].red_lines
    assert len(red) == 1


@pytest.mark.asyncio
async def test_basic_red_lines_cap_at_three_unique() -> None:
    """At most three unique red-line spans after deduplication."""
    parts = [
        "First we will not move on clause A.",
        "Second this is non-negotiable for us.",
        "Third a deal breaker would be exclusivity.",
        "Fourth we refuse to waive liability.",
    ]
    content = " ".join(parts)
    analyzer = ZOPAAnalyzer(llm_provider=None)
    state = _state_with_negotiation_message(content)
    positions = await analyzer.extract_positions(state)
    assert len(positions) == 1
    red = positions[0].red_lines
    assert len(red) == 3
    assert len(red) == len(set(red))
