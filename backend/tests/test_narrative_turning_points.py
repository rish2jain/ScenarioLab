"""Tests for LLM turning-point JSON sanitization in narrative generation."""

from app.reports.narrative import _sanitize_turning_points_from_llm


def test_sanitize_turning_points_non_list_returns_empty() -> None:
    assert _sanitize_turning_points_from_llm({}) == []
    assert _sanitize_turning_points_from_llm("not a list") == []


def test_sanitize_turning_points_keeps_valid_dicts() -> None:
    raw = [
        {"round": 1, "description": "Shift in tone", "significance": "major"},
        {"round": 2.0, "description": "Minor wobble", "significance": "minor"},
        {"round": "3", "description": "Late pivot", "significance": "major"},
    ]
    out = _sanitize_turning_points_from_llm(raw)
    assert out == [
        {"round": 1, "description": "Shift in tone", "significance": "major"},
        {"round": 2, "description": "Minor wobble", "significance": "minor"},
        {"round": 3, "description": "Late pivot", "significance": "major"},
    ]


def test_sanitize_turning_points_filters_invalid() -> None:
    raw = [
        "not a dict",
        {"round": 0, "description": "bad round", "significance": "major"},
        {"round": "3.5", "description": "float string", "significance": "major"},
        {"round": 1, "description": "", "significance": "major"},
        {"round": 1, "description": "ok", "significance": "x"},
        {"description": "missing round", "significance": "major"},
    ]
    out = _sanitize_turning_points_from_llm(raw)
    assert out == [{"round": 1, "description": "ok", "significance": "x"}]


def test_sanitize_turning_points_caps_at_five_valid() -> None:
    raw = [{"round": i, "description": f"d{i}", "significance": "minor"} for i in range(1, 10)]
    out = _sanitize_turning_points_from_llm(raw)
    assert len(out) == 5
    assert out[0]["round"] == 1
    assert out[-1]["round"] == 5


def test_sanitize_turning_points_scans_past_invalid_prefix() -> None:
    """Invalid leading items must not cap the count below five valid entries."""
    raw = ["not a dict", {"round": 0, "description": "x", "significance": "y"}] + [
        {"round": i, "description": f"d{i}", "significance": "minor"} for i in range(1, 10)
    ]
    out = _sanitize_turning_points_from_llm(raw)
    assert len(out) == 5
    assert out[0]["round"] == 1
    assert out[-1]["round"] == 5
