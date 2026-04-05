"""Tests for cost and duration estimation."""

import pytest

from app.config import settings
from app.cost_estimator import CostEstimator


@pytest.fixture
def estimator() -> CostEstimator:
    return CostEstimator()


def test_cli_provider_uses_cli_duration_when_billing_key_is_openai(
    estimator: CostEstimator, monkeypatch: pytest.MonkeyPatch
):
    """Wizard maps cli-* to a cloud family for pricing; wall-clock must stay CLI."""
    monkeypatch.setattr(settings, "llm_provider", "openai")
    api = estimator.estimate(4, 10, 1, "openai")
    monkeypatch.setattr(settings, "llm_provider", "cli-chatgpt")
    cli = estimator.estimate(4, 10, 1, "openai")
    assert cli.estimated_duration_minutes > api.estimated_duration_minutes
    assert cli.duration_breakdown["post_run_report_minutes"] > api.duration_breakdown["post_run_report_minutes"]


def test_cli_claude_duration_uses_cli_tier_with_anthropic_cost_key(
    estimator: CostEstimator, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "llm_provider", "anthropic")
    api = estimator.estimate(3, 8, 1, "anthropic")
    monkeypatch.setattr(settings, "llm_provider", "cli-claude")
    cli = estimator.estimate(3, 8, 1, "anthropic")
    assert cli.estimated_duration_minutes > api.estimated_duration_minutes


def test_estimate_defaults_include_report_and_analytics(estimator: CostEstimator):
    e = estimator.estimate(4, 10, 1, "openai")
    assert e.total_estimated_tokens > 0
    assert e.breakdown["report_generation"]["tokens"] > 0
    assert e.breakdown["analytics"]["tokens"] > 0
    assert e.estimated_duration_minutes > 0


def test_estimate_disables_report_and_analytics(estimator: CostEstimator):
    e = estimator.estimate(4, 10, 1, "openai", include_report=False, include_analytics=False)
    assert e.breakdown["report_generation"]["tokens"] == 0
    assert e.breakdown["analytics"]["tokens"] == 0
    assert e.total_estimated_cost_usd < estimator.estimate(4, 10, 1, "openai").total_estimated_cost_usd


def test_extended_seed_context_increases_agent_bucket(estimator: CostEstimator):
    base = estimator.estimate(4, 10, 1, "openai", include_report=False, include_analytics=False)
    ext = estimator.estimate(
        4,
        10,
        1,
        "openai",
        include_report=False,
        include_analytics=False,
        extended_seed_context=True,
    )
    assert ext.breakdown["agent_reasoning"]["tokens"] > base.breakdown["agent_reasoning"]["tokens"]


def test_monte_carlo_zero_means_single_pass_like_one(estimator: CostEstimator):
    """Batch uses MC=0 for one run per scenario; cost must not zero out work."""
    z = estimator.estimate(2, 5, 0, "ollama")
    one = estimator.estimate(2, 5, 1, "ollama")
    assert z.total_estimated_tokens == one.total_estimated_tokens
    assert z.breakdown["agent_reasoning"]["tokens"] == one.breakdown["agent_reasoning"]["tokens"]
    assert z.breakdown["report_generation"]["tokens"] == one.breakdown["report_generation"]["tokens"]


def test_batch_single_scenario_default_mc_matches_single_estimate(estimator: CostEstimator):
    """Batch with scenario_count=1 and MC=0 should match a single-run estimate."""
    batch = estimator.estimate_batch_cost(
        scenario_count=1,
        agent_count=3,
        rounds=4,
        monte_carlo_iterations=0,
        provider="ollama",
        parallelism_factor=1.0,
    )
    single = estimator.estimate(3, 4, 0, "ollama")
    assert batch.total_estimated_tokens == single.total_estimated_tokens
    assert batch.total_estimated_cost_usd == single.total_estimated_cost_usd
    assert batch.estimated_duration_minutes == pytest.approx(single.estimated_duration_minutes, rel=1e-6)


def test_monte_carlo_multiplies_core_work(estimator: CostEstimator):
    single = estimator.estimate(2, 5, 1, "ollama")
    multi = estimator.estimate(2, 5, 10, "ollama")
    single_ar = single.breakdown["agent_reasoning"]["tokens"]
    multi_ar = multi.breakdown["agent_reasoning"]["tokens"]
    # Monte Carlo should scale agent work ~linearly with iterations; allow slack for
    # rounding or future per-iteration overhead.
    assert multi_ar >= single_ar * 9
    assert multi_ar == pytest.approx(single_ar * 10, rel=0.05)


def test_estimate_single_run_parallelism_factor_is_one(estimator: CostEstimator):
    e = estimator.estimate(3, 5, 1, "openai")
    assert e.parallelism_factor == 1.0


def test_batch_duration_scales_with_scenario_count_over_parallelism(estimator: CostEstimator):
    """Duration uses scenario_count / parallelism_factor; tokens still scale with scenarios."""
    serial = estimator.estimate_batch_cost(
        scenario_count=4,
        agent_count=2,
        rounds=3,
        monte_carlo_iterations=1,
        provider="ollama",
        parallelism_factor=1.0,
    )
    parallel = estimator.estimate_batch_cost(
        scenario_count=4,
        agent_count=2,
        rounds=3,
        monte_carlo_iterations=1,
        provider="ollama",
        parallelism_factor=2.0,
    )
    assert serial.total_estimated_tokens == parallel.total_estimated_tokens
    assert serial.estimated_duration_minutes == pytest.approx(parallel.estimated_duration_minutes * 2.0, rel=1e-6)
    assert serial.parallelism_factor == 1.0
    assert parallel.parallelism_factor == 2.0


def test_batch_parallelism_factor_invalid_raises(estimator: CostEstimator):
    with pytest.raises(ValueError, match="parallelism_factor"):
        estimator.estimate_batch_cost(
            2,
            2,
            2,
            1,
            "ollama",
            parallelism_factor=0.0,
        )
