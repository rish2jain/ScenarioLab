"""Tests for Monte Carlo / batch / rounds input caps."""

import pytest
from pydantic import ValidationError

from app.config import Settings
from app.simulation.batch import BatchConfig, BatchScenario
from app.simulation.models import (
    EnvironmentType,
    SimulationConfig,
    SimulationCreateRequest,
)
from app.simulation.monte_carlo import MonteCarloConfig


def _base_config() -> SimulationConfig:
    return SimulationConfig(
        name="cap-test",
        environment_type=EnvironmentType.BOARDROOM,
        agents=[],
        total_rounds=5,
    )


def test_monte_carlo_iterations_rejects_over_cap(monkeypatch: pytest.MonkeyPatch):
    s = Settings(_env_file=None)
    s.monte_carlo_max_iterations = 10
    monkeypatch.setattr("app.simulation.monte_carlo.settings", s)

    with pytest.raises(ValidationError):
        MonteCarloConfig(base_config=_base_config(), iterations=11)


def test_monte_carlo_iterations_accepts_at_cap(monkeypatch: pytest.MonkeyPatch):
    s = Settings(_env_file=None)
    s.monte_carlo_max_iterations = 10
    monkeypatch.setattr("app.simulation.monte_carlo.settings", s)

    cfg = MonteCarloConfig(base_config=_base_config(), iterations=10)
    assert cfg.iterations == 10


def test_batch_scenarios_rejects_over_cap(monkeypatch: pytest.MonkeyPatch):
    s = Settings(_env_file=None)
    s.batch_max_scenarios = 2
    monkeypatch.setattr("app.simulation.batch.settings", s)

    scenarios = [BatchScenario(id=f"s{i}", name=f"S{i}", config=_base_config()) for i in range(3)]
    with pytest.raises(ValidationError):
        BatchConfig(scenarios=scenarios)


def test_total_rounds_rejects_over_cap(monkeypatch: pytest.MonkeyPatch):
    s = Settings(_env_file=None)
    s.simulation_max_rounds = 20
    monkeypatch.setattr("app.simulation.models.settings", s)

    with pytest.raises(ValidationError):
        SimulationCreateRequest(name="x", total_rounds=21)


def test_total_rounds_rejects_zero(monkeypatch: pytest.MonkeyPatch):
    s = Settings(_env_file=None)
    monkeypatch.setattr("app.simulation.models.settings", s)

    with pytest.raises(ValidationError):
        SimulationCreateRequest(name="x", total_rounds=0)
