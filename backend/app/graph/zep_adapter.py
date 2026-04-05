"""Optional Zep Cloud graph adapter (upstream parity stub).

Requires ``zep`` package and ``ZEP_API_KEY`` when enabled.
"""

from __future__ import annotations

import logging
import threading
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


class ZepGraphAdapter:
    """Lazy Zep client; methods no-op or raise if unavailable."""

    def __init__(self) -> None:
        self._client: Any = None
        self._enabled = bool(settings.zep_api_key)
        self._init_lock = threading.Lock()

    def _ensure_client(self) -> Any:
        if not self._enabled:
            raise RuntimeError("Zep Cloud disabled: set ZEP_API_KEY in .env to enable graph sync")
        if self._client is not None:
            return self._client
        with self._init_lock:
            if self._client is None:
                try:
                    from zep_cloud.client import Zep

                    self._client = Zep(api_key=settings.zep_api_key)
                except ImportError as e:
                    raise RuntimeError("zep-cloud package not installed; pip install zep-cloud") from e
        return self._client

    async def health(self) -> dict[str, Any]:
        """Return configuration status (no network call)."""
        return {
            "zep_configured": self._enabled,
            "message": ("Ready" if self._enabled else "Set ZEP_API_KEY and install zep-cloud to use Zep graphs"),
        }

    def create_graph_placeholder(self, name: str) -> str:
        """Reserved for full GraphBuilder port from upstream ScenarioLab."""
        _ = self._ensure_client()
        logger.info("Zep graph creation requested: %s (stub)", name)
        raise NotImplementedError(
            "Full Zep graph build pipeline not yet ported; " "use local Neo4j + EntityExtractor for now."
        )


zep_graph_adapter = ZepGraphAdapter()
