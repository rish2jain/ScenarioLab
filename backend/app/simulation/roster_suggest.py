"""Suggest agent roster counts from extracted entities + playbook."""

from __future__ import annotations

import logging
from typing import Any

from app.graph.entity_extractor import EntityExtractor
from app.llm.factory import get_llm_provider
from app.playbooks.manager import get_playbook

logger = logging.getLogger(__name__)


async def suggest_roster_from_text(
    text: str,
    playbook_id: str | None,
    *,
    max_roles: int = 12,
    ontology: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Extract entities, map to playbook roles, return suggested agentConfigs."""
    llm = get_llm_provider()
    extractor = EntityExtractor(llm)
    extraction = await extractor.extract_from_text(text[:20000], ontology=ontology)

    playbook = get_playbook(playbook_id) if playbook_id else None
    roster_roles = [r.role for r in (playbook.agent_roster if playbook else [])]

    # Rank person-like and org-like entities (sets for O(1) membership in "other")
    people: list[str] = []
    orgs: list[str] = []
    people_names: set[str] = set()
    org_names: set[str] = set()
    for e in extraction.entities:
        t = getattr(e, "entity_type", "")
        if t == "person":
            people.append(e.name)
            people_names.add(e.name)
        elif t == "organization":
            orgs.append(e.name)
            org_names.add(e.name)
    excluded = people_names | org_names
    other = [e.name for e in extraction.entities if e.name not in excluded]
    ranked = (people + orgs + other)[:max_roles]

    # Default: one agent per playbook role if we have a playbook
    agent_configs: dict[str, int] = {}
    if roster_roles:
        for role in roster_roles:
            agent_configs[role] = 1
    else:
        # Generic roles from entities
        for name in ranked[:max_roles]:
            key = name[:40] or "stakeholder"
            agent_configs[key] = agent_configs.get(key, 0) + 1

    return {
        "agent_configs": agent_configs,
        "entity_names": [e.name for e in extraction.entities],
        "highlighted_stakeholders": ranked,
        "playbook_id": playbook_id,
    }
