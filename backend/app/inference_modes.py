"""Canonical inference tier names (cloud / hybrid / local)."""

from __future__ import annotations

from enum import StrEnum


class InferenceMode(StrEnum):
    """Wizard and engine inference routing mode."""

    CLOUD = "cloud"
    HYBRID = "hybrid"
    LOCAL = "local"


DEFAULT_INFERENCE_MODE = InferenceMode.CLOUD
ALLOWED_INFERENCE_MODES: frozenset[str] = frozenset(m.value for m in InferenceMode)


def normalize_inference_mode(value: str | None) -> str:
    """Return a lowercase allowed mode, or ``DEFAULT_INFERENCE_MODE`` when empty/invalid."""
    raw = (value or "").strip().lower()
    if raw in ALLOWED_INFERENCE_MODES:
        return raw
    return DEFAULT_INFERENCE_MODE.value
