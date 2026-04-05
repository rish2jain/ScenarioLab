"""Shared test fixtures.

This conftest also installs lightweight sys.modules stubs for heavy optional
dependencies (e.g. ``neo4j``) so that tests can run without them installed.
"""

import sys
import types

import pytest

# ---------------------------------------------------------------------------
# Stub out neo4j if it is not available in this test environment
# ---------------------------------------------------------------------------


def _make_neo4j_stub() -> types.ModuleType:
    """Return a minimal neo4j stub that satisfies import-time name lookups."""
    neo4j_mod = types.ModuleType("neo4j")
    # Classes accessed at import time in neo4j_client.py
    for name in ("AsyncDriver", "AsyncGraphDatabase", "Query"):
        setattr(neo4j_mod, name, type(name, (), {}))
    # neo4j.exceptions
    exc_mod = types.ModuleType("neo4j.exceptions")
    for name in ("ServiceUnavailable", "AuthError", "Neo4jError"):
        setattr(exc_mod, name, type(name, (Exception,), {}))
    neo4j_mod.exceptions = exc_mod
    sys.modules["neo4j"] = neo4j_mod
    sys.modules["neo4j.exceptions"] = exc_mod
    return neo4j_mod


try:
    import neo4j  # noqa: F401
except ModuleNotFoundError:
    _make_neo4j_stub()


# ---------------------------------------------------------------------------
# Original fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_agent_config():
    """Return a minimal agent config dict."""
    return {
        "name": "Test CEO",
        "archetype_id": "ceo",
        "customization": {"context": "Test simulation context"},
    }


@pytest.fixture
def sample_simulation_config(sample_agent_config):
    """Return a minimal simulation config dict."""
    return {
        "name": "Test Simulation",
        "description": "A test simulation",
        "environment_type": "boardroom",
        "agents": [sample_agent_config],
        "total_rounds": 3,
    }
