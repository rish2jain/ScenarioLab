"""Per-simulation LLM usage tracking."""

from app.llm.usage_tracker import track_simulation_usage, usage_tracker


def test_usage_tracker_records_under_context():
    usage_tracker.clear("sim-usage-1")
    with track_simulation_usage("sim-usage-1"):
        usage_tracker.record_current(
            {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            provider="openai",
        )
        usage_tracker.record_current(
            {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5},
            provider="openai",
        )

    totals = usage_tracker.get("sim-usage-1")
    assert totals["prompt_tokens"] == 13
    assert totals["completion_tokens"] == 7
    assert totals["total_tokens"] == 20
    assert totals["calls"] == 2
    assert totals["by_provider"]["openai"] == 20


def test_usage_tracker_ignores_without_context():
    before = usage_tracker.get("sim-none")
    usage_tracker.record_current(
        {"prompt_tokens": 100, "completion_tokens": 0, "total_tokens": 100},
        provider="openai",
    )
    assert usage_tracker.get("sim-none") == before
