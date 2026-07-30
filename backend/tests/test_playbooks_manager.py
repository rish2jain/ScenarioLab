"""Smoke tests for playbook manager (no LLM / Neo4j)."""

from app.playbooks.manager import (
    PlaybookManager,
    get_all_playbooks,
    get_playbook,
    prefill_roster,
    validate_playbook_config,
)


def test_manager_loads_bundled_templates():
    mgr = PlaybookManager()
    ids = mgr.get_playbook_ids()
    assert len(ids) >= 1
    assert "boardroom-rehearsal" in ids


def test_get_playbook_and_summary_fields():
    pb = get_playbook("boardroom-rehearsal")
    assert pb is not None
    assert pb.name
    assert pb.environment == "boardroom"
    assert len(pb.agent_roster) >= 1

    summaries = get_all_playbooks()
    match = next(s for s in summaries if s.id == "boardroom-rehearsal")
    assert match.agent_count == sum(e.count for e in pb.agent_roster)
    assert match.min_rounds == pb.typical_duration_rounds[0]
    assert match.max_rounds == pb.typical_duration_rounds[1]


def test_get_playbook_missing_returns_none():
    assert get_playbook("does-not-exist-xyz") is None


def test_prefill_roster_returns_entries():
    roster = prefill_roster("boardroom-rehearsal")
    assert roster is not None
    assert len(roster) >= 1
    assert roster[0].archetype_id


def test_prefill_roster_missing_returns_none():
    assert prefill_roster("missing-playbook") is None


def test_validate_playbook_config_accepts_loaded_template():
    pb = get_playbook("boardroom-rehearsal")
    assert pb is not None
    ok, errors = validate_playbook_config(pb.model_dump())
    assert ok is True
    assert errors == []


def test_validate_playbook_config_rejects_bad_duration():
    pb = get_playbook("boardroom-rehearsal")
    assert pb is not None
    bad = pb.model_dump()
    bad["typical_duration_rounds"] = [10, 2]
    ok, errors = validate_playbook_config(bad)
    assert ok is False
    assert len(errors) >= 1


def test_get_playbooks_by_category():
    mgr = PlaybookManager()
    governance = mgr.get_playbooks_by_category("Governance")
    assert any(p.id == "boardroom-rehearsal" for p in governance)
    assert mgr.get_playbooks_by_category("NoSuchCategory") == []
