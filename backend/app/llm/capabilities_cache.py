"""TTL cache for GET /api/llm/capabilities (hybrid inference probe)."""

from __future__ import annotations

import asyncio
import time
from typing import Any

CapabilitiesPayload = dict[str, Any]


class CapabilitiesCache:
    """Holds cached capabilities payload, TTL, and an asyncio lock for refresh."""

    def __init__(self, ttl_sec: float = 60.0) -> None:
        self._ttl_sec = ttl_sec
        self._lock = asyncio.Lock()
        self._entry: tuple[CapabilitiesPayload | None, float] = (None, 0.0)

    @property
    def ttl_sec(self) -> float:
        return self._ttl_sec

    @property
    def lock(self) -> asyncio.Lock:
        return self._lock

    def peek_valid(self, now: float) -> CapabilitiesPayload | None:
        """Return cached dict if ``now`` is within TTL (no lock)."""
        cached, ts = self._entry
        if cached is not None and (now - ts) < self._ttl_sec:
            return cached
        return None

    async def get_cached(self) -> CapabilitiesPayload | None:
        """Fast path + double-check under lock when the first peek misses."""
        now = time.monotonic()
        first = self.peek_valid(now)
        if first is not None:
            return first
        async with self._lock:
            return self.peek_valid(time.monotonic())

    async def set_cached(self, value: CapabilitiesPayload) -> None:
        """Store payload; acquires ``self.lock`` (for tests / external callers)."""
        async with self._lock:
            self._entry = (value, time.monotonic())

    def set_cached_locked(self, value: CapabilitiesPayload) -> None:
        """Store payload; caller must already hold ``self.lock``."""
        assert self.lock.locked(), "set_cached_locked must be called while holding self.lock"
        self._entry = (value, time.monotonic())
