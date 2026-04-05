"""LLM-generated ontology for entity/relationship extraction (consulting vs broad)."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from pydantic import BaseModel, Field

from app.llm.factory import get_llm_provider
from app.llm.provider import LLMMessage

logger = logging.getLogger(__name__)


class OntologyEntityType(BaseModel):
    name: str
    description: str = ""
    attributes: list[dict[str, Any]] = Field(default_factory=list)


class OntologyEdgeType(BaseModel):
    name: str
    description: str = ""
    source_targets: list[dict[str, str]] = Field(default_factory=list)


class GeneratedOntology(BaseModel):
    entity_types: list[OntologyEntityType] = Field(default_factory=list)
    edge_types: list[OntologyEdgeType] = Field(default_factory=list)
    analysis_summary: str = ""


def _to_pascal_case(name: str) -> str:
    parts = re.split(r"[^a-zA-Z0-9]+", name)
    words: list[str] = []
    for part in parts:
        if not part:
            continue
        words.extend(re.sub(r"([a-z])([A-Z])", r"\1_\2", part).split("_"))
    return "".join(w.capitalize() for w in words if w) or "Entity"


def _to_upper_snake(name: str) -> str:
    """Normalize edge labels to strict UPPER_SNAKE_CASE."""
    s = re.sub(r"[^a-zA-Z0-9]+", "_", str(name))
    s = re.sub(r"_+", "_", s).strip("_")
    s = s.upper()
    return s if s else "UNKNOWN_RELATION"


async def generate_ontology(
    document_excerpt: str,
    simulation_requirement: str = "",
    *,
    mode: str = "consulting",
) -> GeneratedOntology:
    """Produce entity_types and edge_types JSON for downstream extraction."""
    llm = get_llm_provider()
    if mode == "consulting":
        system = (
            "You design knowledge-graph ontologies for strategy consulting "
            "simulations.\n"
            "Entity types must be concrete actors (people, organizations, "
            "regulators, markets), not abstract concepts.\n"
            "Output valid JSON only."
        )
        user = f"""SIMULATION OBJECTIVE:
{simulation_requirement[:4000]}

DOCUMENT EXCERPT:
{document_excerpt[:8000]}

Return JSON with entity_types (list of objects with name PascalCase,
description, attributes list) and edge_types (name UPPER_SNAKE,
source_targets list of source/target types) and analysis_summary.
Use 6-12 entity types and 4-10 edge types."""
    else:
        system = """You design ontologies for open prediction / social simulation.
Entities must be actors that can take positions or actions. JSON only."""
        user = f"""REQUIREMENT + TEXT:
{simulation_requirement[:2000]}

{document_excerpt[:8000]}

Same JSON shape as consulting mode. 8-14 entity types, 5-10 edges."""

    try:
        resp = await llm.generate(
            messages=[
                LLMMessage(role="system", content=system),
                LLMMessage(role="user", content=user),
            ],
            temperature=0.25,
            max_tokens=2500,
        )
        content = resp.content.strip()
        content = re.sub(r"^```\s*\w*\s*", "", content, flags=re.IGNORECASE)
        content = re.sub(r"```\s*$", "", content)
        data = json.loads(content.strip())
        entity_by_key: dict[str, OntologyEntityType] = {}
        for e in data.get("entity_types") or []:
            if isinstance(e, dict) and e.get("name"):
                key = _to_pascal_case(str(e["name"]))
                if key in entity_by_key:
                    continue
                entity_by_key[key] = OntologyEntityType(
                    name=key,
                    description=str(e.get("description", ""))[:200],
                    attributes=[a for a in (e.get("attributes") or []) if isinstance(a, dict)],
                )
        et = list(entity_by_key.values())
        edge_by_key: dict[str, OntologyEdgeType] = {}
        for ed in data.get("edge_types") or []:
            if isinstance(ed, dict) and ed.get("name"):
                key = _to_upper_snake(str(ed["name"]))
                if key in edge_by_key:
                    continue
                edge_by_key[key] = OntologyEdgeType(
                    name=key,
                    description=str(ed.get("description", ""))[:200],
                    source_targets=[st for st in (ed.get("source_targets") or []) if isinstance(st, dict)],
                )
        edges = list(edge_by_key.values())
        return GeneratedOntology(
            entity_types=et[:14],
            edge_types=edges[:12],
            analysis_summary=str(data.get("analysis_summary", "")),
        )
    except Exception:
        logger.exception("generate_ontology failed")
        return GeneratedOntology(
            analysis_summary="fallback: internal error occurred",
            entity_types=[
                OntologyEntityType(
                    name="Organization",
                    description="Any organization",
                ),
                OntologyEntityType(name="Person", description="Individual"),
            ],
            edge_types=[
                OntologyEdgeType(
                    name="RELATED_TO",
                    description="Generic link",
                    source_targets=[{"source": "Person", "target": "Organization"}],
                )
            ],
        )
