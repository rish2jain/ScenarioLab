"""Tests for safe CSS class mapping on report recommendation priorities."""

from app.reports.exporters.pdf_exporter import _recommendation_priority_css_class


def test_recommendation_priority_css_class_whitelist() -> None:
    assert _recommendation_priority_css_class("high") == "priority-high"
    assert _recommendation_priority_css_class("MEDIUM") == "priority-medium"
    assert _recommendation_priority_css_class(" low ") == "priority-low"


def test_recommendation_priority_css_class_unknown() -> None:
    assert _recommendation_priority_css_class("critical") == "priority-unknown"
    assert _recommendation_priority_css_class('<img onerror="x">') == "priority-unknown"
