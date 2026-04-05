"""Base LLM provider abstraction."""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import AsyncIterator

from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Per-provider semaphores: each provider key gets its own cap (default or override).
_provider_semaphores: dict[str, asyncio.Semaphore] = {}

# Cache parsed overrides keyed by raw settings string (avoids repeated json.loads).
_concurrency_overrides_parsed_cache: tuple[str, dict[str, int]] | None = None


def _parse_concurrency_overrides() -> dict[str, int]:
    """Parse ``Settings.llm_concurrency_overrides`` JSON into provider_key -> limit."""
    from app.config import settings

    raw = (settings.llm_concurrency_overrides or "").strip()
    global _concurrency_overrides_parsed_cache
    cached = _concurrency_overrides_parsed_cache
    if cached is not None and cached[0] == raw:
        return cached[1]

    out: dict[str, int] = {}
    if not raw:
        _concurrency_overrides_parsed_cache = (raw, out)
        return out
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.warning("Invalid LLM_CONCURRENCY_OVERRIDES JSON (%s) — using no overrides", e)
        _concurrency_overrides_parsed_cache = (raw, out)
        return out
    if not isinstance(data, dict):
        _concurrency_overrides_parsed_cache = (raw, out)
        return out
    for k, v in data.items():
        if not isinstance(k, str):
            continue
        try:
            n = int(v)
        except (TypeError, ValueError):
            continue
        out[k.lower()] = max(1, n)
    _concurrency_overrides_parsed_cache = (raw, out)
    return out


def concurrency_limit_for_provider(provider_key: str) -> int:
    """Effective concurrent generate() cap for this provider (>= 1)."""
    from app.config import settings

    key = provider_key.lower()
    overrides = _parse_concurrency_overrides()
    if key in overrides:
        return overrides[key]
    return max(1, settings.llm_concurrency_default)


def get_llm_semaphore(provider_key: str) -> asyncio.Semaphore:
    """Return the asyncio semaphore for ``provider_key`` (cached).

    Cached ``asyncio.Semaphore`` objects are bound to the event loop they were
    created on; using them from a different loop can raise ``RuntimeError``.
    Call ``reset_llm_provider_semaphores()`` between event-loop changes (for
    example in pytest fixtures with ``scope="function"``), or otherwise ensure
    semaphores are recreated for each loop, so the next ``get_llm_semaphore``
    call builds instances on the active loop.
    """
    key = provider_key.lower()
    if key not in _provider_semaphores:
        _provider_semaphores[key] = asyncio.Semaphore(concurrency_limit_for_provider(key))
    return _provider_semaphores[key]


def reset_llm_provider_semaphores() -> None:
    """Clear cached semaphores (tests or hot reload)."""
    global _concurrency_overrides_parsed_cache
    _provider_semaphores.clear()
    _concurrency_overrides_parsed_cache = None


async def terminate_process_with_timeout(
    proc: asyncio.subprocess.Process,
    *,
    wait_timeout: float = 5.0,
) -> None:
    """Terminate ``proc`` and reap.

    Sends SIGKILL if the process does not exit within ``wait_timeout`` seconds.
    """
    proc.terminate()
    try:
        await asyncio.wait_for(proc.wait(), timeout=wait_timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()


MAX_TOKENS_CAP = 8192


class LLMMessage(BaseModel):
    """Standard message format for LLM interactions."""

    role: str  # "system", "user", "assistant"
    content: str


class LLMResponse(BaseModel):
    """Standard response format from LLM providers."""

    content: str
    model: str
    provider: str
    # usage: {"prompt_tokens": X, "completion_tokens": Y, "total_tokens": Z}
    usage: dict | None = None


class LLMProvider(ABC):
    """Abstract base class for all LLM providers."""

    provider_name: str

    @abstractmethod
    async def generate(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs,
    ) -> LLMResponse:
        """Generate a completion from messages."""
        pass

    @abstractmethod
    async def stream(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs,
    ) -> AsyncIterator[str]:
        """Stream a completion token by token."""
        pass

    @abstractmethod
    async def test_connection(self) -> dict:
        """Test connectivity.

        Returns {"status": "ok"/"error", "message": "...", "model": "..."}
        """
        pass
