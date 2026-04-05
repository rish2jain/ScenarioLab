"""Entity extraction prompt wiring for optional generated ontology."""

from app.graph.entity_extractor import EntityExtractor


def test_ontology_block_empty_for_none():
    ex = EntityExtractor(llm_provider=None)  # type: ignore[arg-type]
    assert ex._ontology_prompt_block(None) == ""


def test_ontology_block_includes_types():
    ex = EntityExtractor(llm_provider=None)  # type: ignore[arg-type]
    onto = {
        "entity_types": [{"name": "Regulator", "description": "Gov body"}],
        "edge_types": [{"name": "REGULATES", "description": "oversight"}],
        "analysis_summary": "EU retail focus",
    }
    block = ex._ontology_prompt_block(onto)
    assert "Regulator" in block
    assert "REGULATES" in block
    assert "EU retail focus" in block


def test_build_prompt_contains_ontology_section():
    ex = EntityExtractor(llm_provider=None)  # type: ignore[arg-type]
    onto = {"entity_types": [{"name": "Competitor", "description": "Rival firm"}]}
    prompt = ex._build_extraction_prompt("Hello world", ontology=onto)
    assert "Competitor" in prompt
    assert "Hello world" in prompt
