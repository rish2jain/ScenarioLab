"""Stakeholder preflight research: candidates → typed research → EvidencePacks."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
from collections import OrderedDict
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.config import settings
from app.llm.factory import get_llm_provider
from app.llm.provider import LLMMessage
from app.research.service import research_service

logger = logging.getLogger(__name__)

# Strip markdown fences around LLM JSON (optional language token after opening fence).
_JSON_FENCE_LEAD = re.compile(r"^\s*```(?:\s*\S+)?\s*", re.I)
_JSON_FENCE_TAIL = re.compile(r"\s*```\s*$", re.I)

EntityType = Literal["company", "person", "regulation", "industry", "event", "generic"]

_CANONICAL_ENTITY_TYPE: dict[str, EntityType] = {
    "company": "company",
    "person": "person",
    "regulation": "regulation",
    "industry": "industry",
    "event": "event",
    "generic": "generic",
}


def _normalize_entity_type(value: str) -> EntityType:
    """Map free-form / LLM output to a supported EvidencePack entity_type."""
    return _CANONICAL_ENTITY_TYPE.get(value.strip().lower(), "generic")


class EvidenceCitation(BaseModel):
    """A single source reference."""

    title: str = ""
    url: str = ""
    snippet: str = ""


class EvidencePack(BaseModel):
    """Structured research bundle for one entity."""

    entity_name: str
    entity_type: EntityType
    synthesis: dict[str, Any] = Field(default_factory=dict)
    citations: list[EvidenceCitation] = Field(default_factory=list)
    error: str | None = None


def _cache_key(entity: str, mode: str) -> str:
    return hashlib.sha256(f"{entity}|{mode}".encode()).hexdigest()


# Cap in-memory evidence packs per process (LRU by access + insertion order).
_SESSION_CACHE_MAXSIZE = 256


class _BoundedEvidenceLRU:
    """LRU cache with a fixed max size; oldest entries evicted when full."""

    __slots__ = ("_maxsize", "_data", "_lock")

    def __init__(self, maxsize: int) -> None:
        if maxsize < 1:
            raise ValueError("maxsize must be >= 1")
        self._maxsize = maxsize
        self._data: OrderedDict[str, EvidencePack] = OrderedDict()
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> EvidencePack | None:
        async with self._lock:
            if key not in self._data:
                return None
            self._data.move_to_end(key)
            return self._data[key]

    async def set(self, key: str, value: EvidencePack) -> None:
        async with self._lock:
            if key in self._data:
                del self._data[key]
            self._data[key] = value
            while len(self._data) > self._maxsize:
                self._data.popitem(last=False)

    async def clear(self) -> None:
        async with self._lock:
            self._data.clear()


class StakeholderResearchOrchestrator:
    """Discover candidates from seeds + objective, run typed research, cache results."""

    def __init__(self) -> None:
        self._session_cache = _BoundedEvidenceLRU(_SESSION_CACHE_MAXSIZE)

    async def clear_cache(self) -> None:
        await self._session_cache.clear()

    async def discover_candidates(
        self,
        *,
        seed_text: str,
        simulation_requirement: str = "",
        max_entities: int = 8,
    ) -> list[dict[str, Any]]:
        """LLM lists researchable entities (name, type, optional company/role)."""
        llm = get_llm_provider()
        combined = f"{simulation_requirement}\n\n---\n\n{seed_text}"[:12000]
        prompt = f"""From the simulation objective and seed text below, list key
stakeholders and named entities to ground with external (web) research.

OBJECTIVE + SEED:
{combined}

Return JSON array only, max {max_entities} items:
[{{"name": "string", "type": "company|person|regulation|industry|event|generic",
  "company": "optional for person", "role": "optional for person",
  "jurisdiction": "optional for regulation"}}]
"""
        try:
            resp = await llm.generate(
                messages=[
                    LLMMessage(
                        role="system",
                        content="Return valid JSON only. No markdown.",
                    ),
                    LLMMessage(role="user", content=prompt),
                ],
                temperature=0.2,
                max_tokens=800,
            )
            content = resp.content.strip()
            content = _JSON_FENCE_LEAD.sub("", content, count=1)
            content = _JSON_FENCE_TAIL.sub("", content, count=1)
            data = json.loads(content.strip())
            if isinstance(data, list):
                return data[:max_entities]
        except Exception as e:
            logger.warning("discover_candidates LLM failed: %s", e)

        # Fallback: reuse augment_text entity extraction
        try:
            aug = await research_service.augment_text(combined[:3000], purpose="stakeholder discovery")
            found = aug.get("entities_found") or []
            out: list[dict[str, Any]] = []
            for e in found[:max_entities]:
                if isinstance(e, dict):
                    out.append(
                        {
                            "name": e.get("name", ""),
                            "type": e.get("type", "generic"),
                            "company": "",
                            "role": "",
                            "jurisdiction": "",
                        }
                    )
            return [x for x in out if x.get("name")]
        except Exception as e2:
            logger.warning("augment_text fallback failed: %s", e2)
        return []

    def _raw_to_citations(self, raw: list[dict[str, Any]]) -> list[EvidenceCitation]:
        cites: list[EvidenceCitation] = []
        for r in raw[:12]:
            if not isinstance(r, dict):
                continue
            cites.append(
                EvidenceCitation(
                    title=str(r.get("title", "")),
                    url=str(r.get("url", "")),
                    snippet=str(r.get("content", r.get("snippet", "")))[:500],
                )
            )
        return cites

    def _build_evidence_pack(
        self,
        res: dict[str, Any],
        *,
        entity_name: str,
        entity_type: EntityType,
        raw: list[dict[str, Any]],
    ) -> EvidencePack:
        """Build EvidencePack from research response dict and raw hit list."""
        syn = res.get("synthesis") or {}
        synthesis = syn if isinstance(syn, dict) else {"summary": str(syn)}
        return EvidencePack(
            entity_name=entity_name,
            entity_type=entity_type,
            synthesis=synthesis,
            citations=self._raw_to_citations(raw),
        )

    async def research_one(self, cand: dict[str, Any]) -> EvidencePack:
        """Route candidate to the appropriate research_* method."""
        name = str(cand.get("name", "")).strip()
        etype = _normalize_entity_type(str(cand.get("type", "generic")))
        if not name:
            return EvidencePack(
                entity_name="",
                entity_type=etype,
                error="empty name",
            )

        ck = _cache_key(name, etype)
        cached = await self._session_cache.get(ck)
        if cached is not None:
            return cached

        if not settings.tavily_api_key:
            # Do not cache: key may be configured later; caching would serve stale errors.
            return EvidencePack(
                entity_name=name,
                entity_type=etype,
                error="TAVILY_API_KEY not configured; live research disabled",
            )

        try:
            if etype == "company":
                res = await research_service.research_company(name)
                raw = (res.get("raw_web_results") or []) + (res.get("raw_news") or [])
                pack = self._build_evidence_pack(res, entity_name=name, entity_type=etype, raw=raw)
            elif etype == "person":
                res = await research_service.research_executive(
                    name,
                    company=str(cand.get("company", "")),
                    role=str(cand.get("role", "")),
                )
                raw = res.get("raw_results") or []
                pack = self._build_evidence_pack(res, entity_name=name, entity_type=etype, raw=raw)
            elif etype == "regulation":
                res = await research_service.research_regulation(name, jurisdiction=str(cand.get("jurisdiction", "")))
                raw = res.get("raw_web_results") or []
                pack = self._build_evidence_pack(res, entity_name=name, entity_type=etype, raw=raw)
            elif etype == "industry":
                res = await research_service.research_industry(name)
                raw = res.get("raw_results") or []
                pack = self._build_evidence_pack(res, entity_name=name, entity_type=etype, raw=raw)
            else:
                res = await research_service.research_historical_case(f"{name} context stakeholders", tags=[etype])
                raw = res.get("raw_results") or []
                pack = self._build_evidence_pack(res, entity_name=name, entity_type=etype, raw=raw)
        except Exception as e:
            logger.exception("research_one failed for %s", name)
            pack = EvidencePack(entity_name=name, entity_type=etype, error=str(e))

        await self._session_cache.set(ck, pack)
        return pack

    async def run_preflight(
        self,
        *,
        seed_texts: list[str],
        simulation_requirement: str = "",
        max_entities: int = 6,
    ) -> tuple[list[EvidencePack], bool, str]:
        """Merge texts, discover candidates, run research for each candidate concurrently."""
        if not settings.tavily_api_key:
            return (
                [],
                False,
                "Live research disabled: set TAVILY_API_KEY in .env",
            )

        merged = "\n\n---\n\n".join(seed_texts)[:50000]
        candidates = await self.discover_candidates(
            seed_text=merged,
            simulation_requirement=simulation_requirement,
            max_entities=max_entities,
        )
        # Throttle: research at most 2 entities concurrently to avoid
        # overwhelming CLI-based LLM providers (each spawns a subprocess).
        sem = asyncio.Semaphore(2)

        async def _throttled(c: dict[str, Any]) -> EvidencePack:
            async with sem:
                return await self.research_one(c)

        paired = [(c, _throttled(c)) for c in candidates if isinstance(c, dict)]
        coros = [coro for _, coro in paired]
        results = await asyncio.gather(*coros, return_exceptions=True)
        packs: list[EvidencePack] = []
        for (c, _), r in zip(paired, results, strict=True):
            if isinstance(r, EvidencePack):
                packs.append(r)
                continue
            if isinstance(r, BaseException):
                logger.warning(
                    "research task failed for candidate name=%r type=%r: %s",
                    str(c.get("name", "")),
                    str(c.get("type", "")),
                    r,
                    exc_info=(type(r), r, r.__traceback__),
                )
        return packs, True, "ok"


stakeholder_research_orchestrator = StakeholderResearchOrchestrator()
