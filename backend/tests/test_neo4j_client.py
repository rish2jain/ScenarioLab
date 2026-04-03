"""Tests for Neo4j client identifier validation."""

import pytest

from app.graph.neo4j_client import _validate_identifier


class TestValidateIdentifier:
    def test_valid_simple(self):
        assert _validate_identifier("Entity") == "Entity"

    def test_valid_with_underscore(self):
        assert _validate_identifier("WORKS_FOR") == "WORKS_FOR"

    def test_valid_with_numbers(self):
        assert _validate_identifier("Node123") == "Node123"

    def test_valid_underscore_prefix(self):
        assert _validate_identifier("_internal") == "_internal"

    def test_rejects_empty(self):
        with pytest.raises(ValueError, match="Invalid Cypher"):
            _validate_identifier("")

    def test_rejects_starts_with_number(self):
        with pytest.raises(ValueError, match="Invalid Cypher"):
            _validate_identifier("123Node")

    def test_rejects_spaces(self):
        with pytest.raises(ValueError, match="Invalid Cypher"):
            _validate_identifier("My Node")

    def test_rejects_special_chars(self):
        with pytest.raises(ValueError, match="Invalid Cypher"):
            _validate_identifier("node-type")

    def test_rejects_cypher_injection(self):
        with pytest.raises(ValueError, match="Invalid Cypher"):
            _validate_identifier("KNOWS}) DETACH DELETE (n")

    def test_rejects_braces(self):
        with pytest.raises(ValueError, match="Invalid Cypher"):
            _validate_identifier("Node{}")

    def test_rejects_semicolon(self):
        with pytest.raises(ValueError, match="Invalid Cypher"):
            _validate_identifier("Node; DROP")
