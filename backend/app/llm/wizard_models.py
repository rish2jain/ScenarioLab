"""Wizard model catalog and validation aligned with ``settings.llm_provider``.

The simulation engine always uses the **configured** provider (env) plus an optional
``parameters.model`` override. Cost estimates must use the same billing family, and
wizard-selected model ids must be compatible with that provider — otherwise the API
would send e.g. ``claude-3`` to OpenAI or ``gpt-4`` to Anthropic.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

# Cache successful Anthropic GET /v1/models results (avoid blocking every wizard poll).
_ANTHROPIC_CACHE_LOCK = threading.Lock()
_ANTHROPIC_CACHE_TTL_SEC = 3600.0
_cached_anthropic_wizard_models: tuple[list[dict[str, str]], float] | None = None

# Stable family ids (no dated snapshots) when the Models API is unavailable or has no key.
# The live wizard list prefers GET /v1/models when an API key is configured.
#
# Maintenance (no automation can pick new ids safely—review manually):
#   • Revisit after Anthropic announces new major families (e.g. Claude 4.x) or at least once
#     per calendar year; align entries with docs.anthropic.com and with what GET /v1/models
#     returns for the account used in CI/staging.
#   • Keep a balanced, a highest-quality, and a fast/cheap slot so the wizard stays usable
#     offline; update MODEL_VENDOR_PATTERNS if new id prefixes appear.
#   • Tests in test_wizard_models.py assert shape and Claude ids—adjust those when you
#     intentionally change this list.
_ANTHROPIC_WIZARD_MODELS_FALLBACK: list[dict[str, str]] = [
    {
        "id": "claude-3-5-sonnet-20241022",
        "name": "Claude 3.5 Sonnet",
        "desc": "Balanced",
    },
    {
        "id": "claude-opus-4-20250514",
        "name": "Claude Opus 4",
        "desc": "Highest quality",
    },
    {
        "id": "claude-3-5-haiku-20241022",
        "name": "Claude 3.5 Haiku",
        "desc": "Fast & cheap",
    },
]

# Substrings, prefix roots, and exact ids used to infer model vendor from public ids.
# **Maintain MODEL_VENDOR_PATTERNS when providers ship new names** so validation and
# cloud-vs-local checks stay accurate; avoid duplicating literals outside this mapping.
MODEL_VENDOR_PATTERNS: dict[str, tuple[str, ...] | frozenset[str]] = {
    "openai_substrings": (
        "gpt",
        "chatgpt",
        "davinci",
        "text-embedding",
        "ft:",
    ),
    "openai_prefixes": ("o1", "o2", "o3", "o4"),
    "anthropic_substrings": ("claude",),
    "google_substrings": ("gemini", "gemma"),
    "qwen_hosted_exact": frozenset({"qwen-turbo", "qwen-plus", "qwen-max", "qwen-long"}),
}

# First entry in :func:`wizard_model_options` for hosted API families; ``id`` "" maps to
# no per-run override (validated by :func:`validate_wizard_model_override`).
WIZARD_PROVIDER_DEFAULT_OPTION: dict[str, str] = {
    "id": "",
    "name": "Provider Default",
    "desc": "Use the provider default model",
}


def provider_family() -> str:
    """Broad family for validation, pricing, and UI."""
    p = settings.llm_provider.lower()
    if p in ("openai", "cli-chatgpt", "cli-codex"):
        return "openai"
    if p in ("anthropic", "cli-claude"):
        return "anthropic"
    if p == "google":
        return "google"
    if p == "qwen":
        return "qwen"
    if p in ("ollama", "llamacpp"):
        return "local"
    if p == "cli-gemini":
        return "google"
    logger.warning(
        "Unknown llm_provider %r; defaulting validation/pricing family to openai",
        p,
    )
    return "openai"


def cost_estimator_provider_key() -> str:
    """Key into :class:`CostEstimator.PROVIDER_COSTS` for the active server provider."""
    fam = provider_family()
    # Cost table uses "ollama" for zero local pricing; family groups ollama + llamacpp.
    return "ollama" if fam == "local" else fam


def reset_anthropic_wizard_models_cache() -> None:
    """Clear cached Anthropic model list (e.g. between tests)."""
    global _cached_anthropic_wizard_models
    with _ANTHROPIC_CACHE_LOCK:
        _cached_anthropic_wizard_models = None


def _pick_latest_anthropic_model(models: list[Any], *, needle: str) -> Any | None:
    needle_l = needle.lower()
    hits = [m for m in models if needle_l in m.id.lower()]
    if not hits:
        return None
    return max(hits, key=lambda m: m.created_at)


def _slot_from_anthropic_model_or_fallback(
    picked: Any | None,
    fallback: dict[str, str],
) -> dict[str, str]:
    if picked is not None:
        return {
            "id": picked.id,
            "name": picked.display_name,
            "desc": fallback["desc"],
        }
    return dict(fallback)


def _fetch_anthropic_wizard_models_from_api() -> list[dict[str, str]] | None:
    """Use Anthropic Models API to pick latest sonnet / opus / haiku entries."""
    raw = getattr(settings, "llm_api_key", None)
    key = raw.strip() if isinstance(raw, str) else ""
    if not key:
        return None
    try:
        from anthropic import Anthropic

        client = Anthropic(api_key=key)
        models = list(client.models.list())
    except Exception as e:
        logger.warning(
            "Anthropic model list failed; using stable wizard fallbacks: %s",
            e,
        )
        return None
    if not models:
        return None

    fb = _ANTHROPIC_WIZARD_MODELS_FALLBACK
    sonnet = _pick_latest_anthropic_model(models, needle="sonnet")
    opus = _pick_latest_anthropic_model(models, needle="opus")
    haiku = _pick_latest_anthropic_model(models, needle="haiku")
    return [
        dict(WIZARD_PROVIDER_DEFAULT_OPTION),
        _slot_from_anthropic_model_or_fallback(sonnet, fb[0]),
        _slot_from_anthropic_model_or_fallback(opus, fb[1]),
        _slot_from_anthropic_model_or_fallback(haiku, fb[2]),
    ]


def _anthropic_wizard_model_entries() -> list[dict[str, str]]:
    """Prefer live model ids from Anthropic; cache successes; else stable fallbacks."""
    global _cached_anthropic_wizard_models
    now = time.monotonic()
    with _ANTHROPIC_CACHE_LOCK:
        if _cached_anthropic_wizard_models is not None:
            entries, ts = _cached_anthropic_wizard_models
            if now - ts < _ANTHROPIC_CACHE_TTL_SEC:
                return [dict(row) for row in entries]

    fetched = _fetch_anthropic_wizard_models_from_api()
    if fetched is not None:
        with _ANTHROPIC_CACHE_LOCK:
            _cached_anthropic_wizard_models = (fetched, time.monotonic())
        return [dict(row) for row in fetched]

    fb = _ANTHROPIC_WIZARD_MODELS_FALLBACK
    return [
        dict(WIZARD_PROVIDER_DEFAULT_OPTION),
        dict(fb[0]),
        dict(fb[1]),
        dict(fb[2]),
    ]


def _looks_like_openai_model(m: str) -> bool:
    """Return True if ``m`` resembles an OpenAI-class API model id.

    Pattern lists live in :data:`MODEL_VENDOR_PATTERNS`. **Update those entries**
    when OpenAI (or compatible APIs) release new public model name families.
    """
    m = m.lower().strip()
    subs = MODEL_VENDOR_PATTERNS["openai_substrings"]
    if any(x in m for x in subs):
        return True
    prefixes = MODEL_VENDOR_PATTERNS["openai_prefixes"]
    return any(m.startswith(prefix) for prefix in prefixes)


def _looks_like_cloud_hosted_model(m: str) -> bool:
    """Ids that match hosted API vendors — invalid as Ollama/llama.cpp model tags.

    Uses :data:`MODEL_VENDOR_PATTERNS` for Anthropic/Google/Qwen heuristics.
    **Keep those patterns current** as vendors add new hosted model names.
    """
    if _looks_like_openai_model(m):
        return True
    m = m.lower().strip()
    pat = MODEL_VENDOR_PATTERNS
    if any(s in m for s in pat["anthropic_substrings"]):
        return True
    if any(s in m for s in pat["google_substrings"]):
        return True
    if m in pat["qwen_hosted_exact"]:
        return True
    return False


def validate_wizard_model_override(model_override: str | None) -> None:
    """Ensure wizard ``parameters.model`` matches the configured provider family.

    Raises:
        ValueError: If the model id is clearly wrong for the active provider.
    """
    if not model_override or not str(model_override).strip():
        return
    mo = str(model_override).strip()
    m = mo.lower()
    fam = provider_family()
    if fam == "local":
        if _looks_like_cloud_hosted_model(m):
            raise ValueError(
                f"Model '{mo}' looks like a cloud API model id, but your server uses "
                f"a local provider ({settings.llm_provider}). Use a local model tag "
                "(e.g. llama3:latest) or Provider Default."
            )
        return

    if fam == "openai":
        if not _looks_like_openai_model(m):
            raise ValueError(
                f"Model '{mo}' does not match your configured OpenAI-class provider "
                f"({settings.llm_provider}). Pick a GPT/OpenAI model from the list or "
                "use Provider Default."
            )
    elif fam == "anthropic":
        if "claude" not in m:
            raise ValueError(
                f"Model '{mo}' does not match your configured Anthropic provider "
                f"({settings.llm_provider}). Pick a Claude model or use "
                "Provider Default."
            )
    elif fam == "google":
        if "gemini" not in m and "gemma" not in m:
            raise ValueError(
                f"Model '{mo}' does not match your configured Google provider "
                f"({settings.llm_provider}). Pick a Gemini model or use "
                "Provider Default."
            )
    elif fam == "qwen":
        if "qwen" not in m:
            raise ValueError(f"Model '{mo}' does not match Qwen. Pick a Qwen model id or " "use Provider Default.")


def wizard_model_options() -> list[dict[str, str]]:
    """Return model choices for GET /api/llm/wizard-models (server-driven)."""
    fam = provider_family()
    default = dict(WIZARD_PROVIDER_DEFAULT_OPTION)
    if fam == "openai":
        return [
            default,
            {
                "id": "gpt-4o",
                "name": "GPT-4o",
                "desc": "Best balance of quality and speed",
            },
            {
                "id": "gpt-4",
                "name": "GPT-4",
                "desc": "High quality",
            },
            {
                "id": "gpt-3.5-turbo",
                "name": "GPT-3.5 Turbo",
                "desc": "Fast and economical",
            },
        ]
    if fam == "anthropic":
        return _anthropic_wizard_model_entries()
    if fam == "google":
        return [
            default,
            {
                "id": "gemini-2.0-flash",
                "name": "Gemini 2.0 Flash",
                "desc": "Fast",
            },
            {
                "id": "gemini-1.5-pro",
                "name": "Gemini 1.5 Pro",
                "desc": "Higher quality",
            },
        ]
    if fam == "qwen":
        return [
            default,
            {
                "id": "qwen-turbo",
                "name": "Qwen Turbo",
                "desc": "Fast",
            },
            {
                "id": "qwen-plus",
                "name": "Qwen Plus",
                "desc": "Balanced",
            },
        ]
    return []
