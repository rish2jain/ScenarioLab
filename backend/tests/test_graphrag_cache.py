"""GraphRAG singleton must track Neo4j client lifecycle (no stale closed drivers)."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.graph.router import get_graphrag, reset_graphrag_cache


@pytest.fixture(autouse=True)
def _clear_graphrag_cache():
    reset_graphrag_cache()
    yield
    reset_graphrag_cache()


def test_get_graphrag_recreates_when_neo4j_instance_changes():
    client_a = MagicMock()
    client_a.is_connected = True
    client_b = MagicMock()
    client_b.is_connected = True
    llm = MagicMock()

    with patch("app.graph.router.get_llm_provider", return_value=llm):
        with patch("app.graph.router.get_neo4j_client", return_value=client_a):
            g1 = get_graphrag()
            assert g1.db is client_a

        with patch("app.graph.router.get_neo4j_client", return_value=client_b):
            g2 = get_graphrag()
            assert g2.db is client_b
            assert g2 is not g1


def test_get_graphrag_raises_503_when_driver_disconnected():
    neo4j = MagicMock()
    neo4j.is_connected = True
    llm = MagicMock()

    with patch("app.graph.router.get_llm_provider", return_value=llm):
        with patch("app.graph.router.get_neo4j_client", return_value=neo4j):
            g1 = get_graphrag()
            assert g1.db is neo4j

        neo4j.is_connected = False
        with patch("app.graph.router.get_neo4j_client", return_value=neo4j):
            with pytest.raises(HTTPException) as exc_info:
                get_graphrag()
            assert exc_info.value.status_code == 503


def test_get_graphrag_raises_when_neo4j_unavailable():
    with patch("app.graph.router.get_neo4j_client", return_value=None):
        with patch("app.graph.router.get_llm_provider", return_value=MagicMock()):
            with pytest.raises(HTTPException) as exc_info:
                get_graphrag()
            assert exc_info.value.status_code == 503
