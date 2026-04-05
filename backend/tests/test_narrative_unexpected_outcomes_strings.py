"""Tests for string validation of LLM unexpected-outcomes JSON lists."""

import logging

import pytest

from app.reports.narrative import _collect_string_outcomes_from_llm_list


def test_collect_string_outcomes_keeps_stripped_strings() -> None:
    root = ["  a  ", "b"]
    assert _collect_string_outcomes_from_llm_list(
        root,
        parsed=root,
        raw_preview="preview",
    ) == ["a", "b"]


def test_collect_string_outcomes_skips_empty_after_strip() -> None:
    root = ["ok", "   ", "\t"]
    assert _collect_string_outcomes_from_llm_list(
        root,
        parsed=root,
        raw_preview="preview",
    ) == ["ok"]


def test_collect_string_outcomes_skips_non_strings_and_warns(
    caplog: pytest.LogCaptureFixture,
) -> None:
    root = ["ok", 42, {"nested": True}]
    with caplog.at_level(logging.WARNING):
        out = _collect_string_outcomes_from_llm_list(
            root,
            parsed=root,
            raw_preview="raw-preview",
        )
    assert out == ["ok"]
    assert "skipped non-string outcome item" in caplog.text
    assert "raw-preview" in caplog.text
