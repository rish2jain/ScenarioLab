"""Tests for Neo4j client identifier validation and app singleton helpers."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.graph.neo4j_client import (
    _validate_identifier,
    get_application_neo4j_client,
    is_application_neo4j_registered,
    register_application_neo4j_client,
    unregister_application_neo4j_client,
)


@pytest.fixture(autouse=True)
def _reset_application_neo4j_singleton():
    unregister_application_neo4j_client()
    yield
    unregister_application_neo4j_client()


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


class TestApplicationNeo4jSingleton:
    def test_unregister_awaits_close_when_client_registered(self):
        client = MagicMock()
        client.close = AsyncMock()
        register_application_neo4j_client(client)
        unregister_application_neo4j_client()
        client.close.assert_awaited_once()
        assert get_application_neo4j_client() is None
        assert is_application_neo4j_registered() is False

    def test_unregister_no_op_when_not_registered(self):
        unregister_application_neo4j_client()
        assert get_application_neo4j_client() is None
        assert is_application_neo4j_registered() is False

    def test_unregister_logs_and_clears_on_close_failure(self, caplog):
        client = MagicMock()

        async def boom():
            raise RuntimeError("close failed")

        client.close = boom
        register_application_neo4j_client(client)
        with caplog.at_level("WARNING"):
            unregister_application_neo4j_client()
        assert "Failed to close Neo4j client during unregister" in caplog.text
        assert get_application_neo4j_client() is None
        assert is_application_neo4j_registered() is False
