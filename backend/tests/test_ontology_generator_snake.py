"""Tests for ontology label normalization helpers."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.graph.ontology_generator import _to_upper_snake, generate_ontology


def test_to_upper_snake_emptyish_inputs_fallback():
    assert _to_upper_snake("") == "UNKNOWN_RELATION"
    assert _to_upper_snake("---") == "UNKNOWN_RELATION"
    assert _to_upper_snake("___") == "UNKNOWN_RELATION"


def test_to_upper_snake_normal():
    assert _to_upper_snake("foo-bar") == "FOO_BAR"
    assert _to_upper_snake("Owns Share") == "OWNS_SHARE"


def _minimal_ontology_json() -> str:
    return json.dumps(
        {
            "entity_types": [
                {"name": "Acme", "description": "Co", "attributes": []},
            ],
            "edge_types": [],
            "analysis_summary": "ok",
        }
    )


@pytest.mark.asyncio
async def test_generate_ontology_strips_json_language_fence():
    body = _minimal_ontology_json()
    fenced = f"```JSON\n{body}\n```"
    llm = MagicMock()
    llm.generate = AsyncMock(return_value=MagicMock(content=fenced))
    with patch("app.graph.ontology_generator.get_llm_provider", return_value=llm):
        out = await generate_ontology("doc excerpt", "objective")
    assert out.entity_types[0].name == "Acme"
    assert out.analysis_summary == "ok"


@pytest.mark.asyncio
async def test_generate_ontology_strips_plain_fence_with_trailing_whitespace():
    body = _minimal_ontology_json()
    fenced = f"```\n{body}\n```  \n"
    llm = MagicMock()
    llm.generate = AsyncMock(return_value=MagicMock(content=fenced))
    with patch("app.graph.ontology_generator.get_llm_provider", return_value=llm):
        out = await generate_ontology("doc excerpt", "objective")
    assert out.entity_types[0].name == "Acme"


@pytest.mark.parametrize("opener", ["```jsonc\n", "```JSON5\n", "```typescript\n"])
@pytest.mark.asyncio
async def test_generate_ontology_strips_various_language_fences(opener: str):
    body = _minimal_ontology_json()
    fenced = f"{opener}{body}\n```"
    llm = MagicMock()
    llm.generate = AsyncMock(return_value=MagicMock(content=fenced))
    with patch("app.graph.ontology_generator.get_llm_provider", return_value=llm):
        out = await generate_ontology("doc excerpt", "objective")
    assert out.entity_types[0].name == "Acme"
