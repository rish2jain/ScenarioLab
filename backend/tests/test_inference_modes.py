"""Tests for canonical inference mode normalization."""

import pytest

from app.config import Settings
from app.inference_modes import (
    ALLOWED_INFERENCE_MODES,
    DEFAULT_INFERENCE_MODE,
    InferenceMode,
    normalize_inference_mode,
)


def test_allowed_set_matches_enum() -> None:
    assert ALLOWED_INFERENCE_MODES == frozenset(
        (InferenceMode.CLOUD.value, InferenceMode.HYBRID.value, InferenceMode.LOCAL.value)
    )


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, DEFAULT_INFERENCE_MODE.value),
        ("", DEFAULT_INFERENCE_MODE.value),
        ("  CLOUD  ", InferenceMode.CLOUD.value),
        ("Hybrid", InferenceMode.HYBRID.value),
        ("  local  ", InferenceMode.LOCAL.value),
        ("LOCAL", InferenceMode.LOCAL.value),
        ("bogus", DEFAULT_INFERENCE_MODE.value),
    ],
)
def test_normalize_inference_mode(raw: str | None, expected: str) -> None:
    assert normalize_inference_mode(raw) == expected


def test_settings_coerce_invalid_inference_mode() -> None:
    """Invalid ``inference_mode`` values map to the canonical default at validation time."""
    s = Settings.model_validate({"inference_mode": "not-a-mode"})
    assert s.inference_mode == DEFAULT_INFERENCE_MODE.value
