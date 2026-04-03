"""Shared test fixtures."""

import pytest


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
