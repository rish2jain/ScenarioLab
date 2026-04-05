"""Route LLM calls between cloud and local providers (hybrid inference)."""

from __future__ import annotations

import asyncio
import logging

from app.inference_modes import InferenceMode, normalize_inference_mode
from app.llm.provider import LLMMessage, LLMProvider

logger = logging.getLogger(__name__)

# Exemplar text caps (characters) — spec §5.2
_EXEMPLAR_RESPONSE_MAX = 500
_EXEMPLAR_VOTE_MAX = 300
_EXEMPLAR_STANCE_MAX = 200


class InferenceRouter:
    """Holds cloud + local providers and routes by mode, round, and task type."""

    def __init__(
        self,
        cloud: LLMProvider,
        local: LLMProvider | None,
        mode: str,
        cloud_rounds: int = 1,
        *,
        exemplars: dict[str, dict] | None = None,
    ) -> None:
        self.cloud = cloud
        self.local = local
        self.mode = mode
        self.cloud_rounds = max(0, int(cloud_rounds))
        # agent_id -> {response, vote_reasoning, stance}
        self._exemplars: dict[str, dict] = exemplars if exemplars is not None else {}

    @classmethod
    async def create(
        cls,
        cloud: LLMProvider,
        local: LLMProvider | None,
        mode: str,
        cloud_rounds: int = 1,
    ) -> InferenceRouter:
        """Build router; probe local when hybrid/local; degrade hybrid to cloud if unreachable."""
        m = normalize_inference_mode(mode)
        cr = max(0, int(cloud_rounds))

        if m == InferenceMode.LOCAL.value:
            if local is None:
                raise ValueError("inference_mode=local requires a configured local LLM provider")
            try:
                await asyncio.wait_for(local.test_connection(), timeout=5.0)
            except (TimeoutError, asyncio.CancelledError) as e:
                raise ValueError("Local LLM unreachable; fix LOCAL_LLM_* or use inference_mode=cloud") from e
            except Exception as e:
                raise ValueError(f"Local LLM connection failed: {e}") from e
            return cls(cloud=cloud, local=local, mode=InferenceMode.LOCAL.value, cloud_rounds=cr)

        if m == InferenceMode.HYBRID.value:
            if local is None:
                logger.warning("Hybrid inference requested but no local provider; using cloud only")
                return cls(
                    cloud=cloud,
                    local=None,
                    mode=InferenceMode.CLOUD.value,
                    cloud_rounds=cr,
                )
            try:
                await asyncio.wait_for(local.test_connection(), timeout=5.0)
            except Exception as e:
                logger.warning(
                    "Hybrid inference: local LLM unreachable (%s); using cloud only",
                    e,
                )
                return cls(
                    cloud=cloud,
                    local=None,
                    mode=InferenceMode.CLOUD.value,
                    cloud_rounds=cr,
                )
            return cls(
                cloud=cloud,
                local=local,
                mode=InferenceMode.HYBRID.value,
                cloud_rounds=cr,
            )

        # cloud (default)
        return cls(cloud=cloud, local=local, mode=InferenceMode.CLOUD.value, cloud_rounds=cr)

    def get_provider(self, round_number: int, task_type: str) -> LLMProvider:
        """Return the provider for this round and task."""
        tt = (task_type or "response").strip().lower()

        if self.mode == InferenceMode.CLOUD.value:
            return self.cloud

        if self.mode == InferenceMode.LOCAL.value:
            if self.local is None:
                return self.cloud
            return self.local

        # hybrid
        if tt in ("analytics", "report"):
            return self.cloud
        if round_number <= self.cloud_rounds:
            return self.cloud
        if self.local is not None:
            return self.local
        return self.cloud

    def should_inject_exemplars(
        self,
        agent_id: str,
        round_number: int,
        task_type: str,
    ) -> bool:
        if self.mode != InferenceMode.HYBRID.value or self.local is None:
            return False
        tt = (task_type or "response").strip().lower()
        if tt in ("analytics", "report"):
            return False
        if round_number <= self.cloud_rounds:
            return False
        return bool(self._exemplars.get(agent_id))

    def store_exemplar(
        self,
        agent_id: str,
        messages: list[object],
        stance_text: str | None = None,
    ) -> None:
        """Store round exemplars for an agent (response, vote, stance)."""
        response_text = ""
        vote_text = ""
        stance = (stance_text or "").strip()

        for msg in messages:
            if getattr(msg, "agent_id", None) != agent_id:
                continue
            mt = (getattr(msg, "message_type", None) or "").lower()
            content = getattr(msg, "content", None) or ""
            if mt == "vote":
                vote_text = content
            elif mt == "error":
                continue
            else:
                # Prefer latest substantive response as style exemplar
                response_text = content

        self._exemplars[agent_id] = {
            "response": response_text[:_EXEMPLAR_RESPONSE_MAX],
            "vote": vote_text[:_EXEMPLAR_VOTE_MAX],
            "stance": stance[:_EXEMPLAR_STANCE_MAX],
        }

    def build_exemplar_messages(self, agent_id: str) -> list[LLMMessage]:
        """Build 0–1 user messages with STYLE CALIBRATION for local hybrid calls.

        The heading references ``cloud_rounds`` (the last cloud round used to capture
        exemplars), or a generic phrase when ``cloud_rounds`` is 0 (e.g. Monte Carlo
        follow-up routers that preload exemplars from an earlier run).
        """
        if self.mode != InferenceMode.HYBRID.value:
            return []
        data = self._exemplars.get(agent_id)
        if not data:
            return []

        r = data.get("response") or ""
        v = data.get("vote") or ""
        s = data.get("stance") or ""

        if not (r or v or s):
            return []

        # Exemplars are captured at the last cloud round (engine: round_num == cloud_rounds).
        # Monte Carlo follow-up uses cloud_rounds=0 with copied exemplars — no single round label.
        if self.cloud_rounds > 0:
            calib_header = f"STYLE CALIBRATION (from your Round {self.cloud_rounds} " "performance):\n\n"
        else:
            calib_header = "STYLE CALIBRATION (from your prior performance):\n\n"

        body = (
            calib_header
            + f'Your response style:\n"{r}"\n\n'
            + f'Your voting style:\n"{v}"\n\n'
            + f'Your stance summary:\n"{s}"\n\n'
            + "Maintain this voice, reasoning depth, and perspective."
        )
        # Rough 600-token budget: ~2400 chars
        cap = 2400
        if len(body) > cap:
            body = body[: cap - 3] + "..."

        return [LLMMessage(role="user", content=body)]

    def with_preloaded_exemplars(self) -> InferenceRouter:
        """Monte Carlo copies 2+: all rounds local, shared exemplars from copy 1.

        Shallow-copies the agent-id map only; per-agent exemplar dicts (response / vote /
        stance) are the same objects as in ``self``. Mutating them affects this router too
        unless callers deep-copy first — see :meth:`exemplars_shared_with`.
        """
        return InferenceRouter(
            cloud=self.cloud,
            local=self.local,
            mode=InferenceMode.HYBRID.value,
            cloud_rounds=0,
            exemplars=dict(self._exemplars),
        )

    def snapshot_exemplars(self) -> dict[str, dict[str, str]]:
        """Serialize exemplars for persistence (resume after pause / DB reload)."""
        out: dict[str, dict[str, str]] = {}
        for aid, d in self._exemplars.items():
            out[aid] = {
                "response": str(d.get("response") or ""),
                "vote": str(d.get("vote") or ""),
                "stance": str(d.get("stance") or ""),
            }
        return out

    def restore_exemplars(self, snapshot: dict[str, dict[str, str]] | None) -> None:
        """Restore exemplars from :meth:`snapshot_exemplars` after cold rehydration."""
        if not snapshot:
            return
        self._exemplars.clear()
        for aid, d in snapshot.items():
            self._exemplars[aid] = {
                "response": (d.get("response") or "")[:_EXEMPLAR_RESPONSE_MAX],
                "vote": (d.get("vote") or "")[:_EXEMPLAR_VOTE_MAX],
                "stance": (d.get("stance") or "")[:_EXEMPLAR_STANCE_MAX],
            }

    def has_exemplars(self) -> bool:
        """Return True if any per-agent exemplar payload has been stored."""
        return bool(self._exemplars)

    def exemplars_shared_with(self, other: InferenceRouter) -> bool:
        """Return True if ``other`` references the same per-agent exemplar dicts as ``self``.

        A follow-up router from :meth:`with_preloaded_exemplars` shallow-copies the
        mapping; inner dicts remain shared with the source router.
        """
        if other is self:
            return True
        if set(self._exemplars) != set(other._exemplars):
            return False
        return all(self._exemplars[k] is other._exemplars[k] for k in self._exemplars)
