"""Accumulate LLM token usage per simulation (ContextVar + in-memory totals)."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Iterator

_current_simulation_id: ContextVar[str | None] = ContextVar(
    "llm_usage_simulation_id",
    default=None,
)


@dataclass
class SimulationUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    calls: int = 0
    by_provider: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "calls": self.calls,
            "by_provider": dict(self.by_provider),
        }


class UsageTracker:
    """Process-local usage totals keyed by simulation id."""

    def __init__(self) -> None:
        self._by_sim: dict[str, SimulationUsage] = {}

    def record(
        self,
        simulation_id: str | None,
        usage: dict[str, Any] | None,
        *,
        provider: str = "",
    ) -> None:
        if not simulation_id or not usage:
            return
        prompt = int(usage.get("prompt_tokens") or 0)
        completion = int(usage.get("completion_tokens") or 0)
        total = int(usage.get("total_tokens") or (prompt + completion))
        bucket = self._by_sim.setdefault(simulation_id, SimulationUsage())
        bucket.prompt_tokens += prompt
        bucket.completion_tokens += completion
        bucket.total_tokens += total
        bucket.calls += 1
        if provider:
            bucket.by_provider[provider] = bucket.by_provider.get(provider, 0) + total

    def record_current(self, usage: dict[str, Any] | None, *, provider: str = "") -> None:
        self.record(_current_simulation_id.get(), usage, provider=provider)

    def get(self, simulation_id: str) -> dict[str, Any]:
        bucket = self._by_sim.get(simulation_id)
        return bucket.to_dict() if bucket else SimulationUsage().to_dict()

    def clear(self, simulation_id: str) -> None:
        self._by_sim.pop(simulation_id, None)


usage_tracker = UsageTracker()


@contextmanager
def track_simulation_usage(simulation_id: str) -> Iterator[None]:
    """Bind LLM usage recording to ``simulation_id`` for the current task."""
    token = _current_simulation_id.set(simulation_id)
    try:
        yield
    finally:
        _current_simulation_id.reset(token)
