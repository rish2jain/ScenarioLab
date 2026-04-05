"""Tests for ontology label normalization helpers."""

from app.graph.ontology_generator import _to_upper_snake


def test_to_upper_snake_emptyish_inputs_fallback():
    assert _to_upper_snake("") == "UNKNOWN_RELATION"
    assert _to_upper_snake("---") == "UNKNOWN_RELATION"
    assert _to_upper_snake("___") == "UNKNOWN_RELATION"


def test_to_upper_snake_normal():
    assert _to_upper_snake("foo-bar") == "FOO_BAR"
    assert _to_upper_snake("Owns Share") == "OWNS_SHARE"
