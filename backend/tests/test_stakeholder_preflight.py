"""Tests for stakeholder preflight research and objective models."""

from unittest.mock import patch

import pytest
from pydantic import ValidationError

from app.research.stakeholder_research import (
    EvidencePack,
    StakeholderResearchOrchestrator,
    _normalize_entity_type,
)
from app.simulation.objectives import ParsedSimulationObjective


@pytest.mark.asyncio
async def test_preflight_gather_continues_on_one_task_failure():
    """One failing research_one must not cancel siblings (gather with return_exceptions)."""
    orch = StakeholderResearchOrchestrator()

    async def fake_discover(**kwargs):
        return [
            {"name": "A", "type": "company"},
            {"name": "B", "type": "company"},
        ]

    async def fake_research_one(cand):
        if cand["name"] == "A":
            raise RuntimeError("simulated failure")
        return EvidencePack(entity_name=cand["name"], entity_type="company")

    with patch("app.research.stakeholder_research.settings") as s:
        s.tavily_api_key = "x"
        orch.discover_candidates = fake_discover  # type: ignore[method-assign]
        orch.research_one = fake_research_one  # type: ignore[method-assign]
        packs, ok, msg = await orch.run_preflight(seed_texts=["x"], max_entities=2)

    assert ok is True
    assert msg == "ok"
    assert len(packs) == 1
    assert packs[0].entity_name == "B"


@pytest.mark.asyncio
async def test_preflight_no_tavily_returns_empty():
    orch = StakeholderResearchOrchestrator()
    with patch("app.research.stakeholder_research.settings") as s:
        s.tavily_api_key = ""
        packs, ok, msg = await orch.run_preflight(
            seed_texts=["hello world"],
            simulation_requirement="test",
            max_entities=3,
        )
    assert ok is False
    assert packs == []
    assert "TAVILY" in msg


def test_evidence_pack_model_dump():
    p = EvidencePack(
        entity_name="Acme",
        entity_type="company",
        synthesis={"x": 1},
        citations=[],
    )
    d = p.model_dump()
    assert d["entity_name"] == "Acme"


def test_evidence_pack_invalid_entity_type_raises():
    with pytest.raises(ValidationError):
        EvidencePack.model_validate({"entity_name": "x", "entity_type": "not-a-valid-type"})


def test_normalize_entity_type():
    assert _normalize_entity_type(" Company ") == "company"
    assert _normalize_entity_type("unknown_label") == "generic"


def test_parsed_objective_defaults():
    o = ParsedSimulationObjective(raw_text="")
    assert o.key_actors == []
