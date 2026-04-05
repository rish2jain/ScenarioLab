"""Persona designer refresh: no fallback trait overwrite; no-op refresh timestamp."""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.personas.designer import (
    Citation,
    CustomPersonaConfig,
    PersonaDesigner,
    ResearchRefreshError,
    persona_designer,
)
from app.personas.interview_extractor import ExtractedPersona, InterviewExtractor


def _dt_equal_iso(a: str | None, b: str | None) -> bool:
    """Compare ISO timestamps allowing Z vs +00:00 from JSON serialization."""

    def _parse(x: str | None) -> datetime | None:
        if x is None:
            return None
        s = x.strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)

    return _parse(a) == _parse(b)


@pytest.mark.asyncio
async def test_research_persona_reraises_when_allow_fallback_false() -> None:
    """Designer refresh passes allow_fallback=False so traits are not replaced with LLM defaults."""
    with patch("app.personas.interview_extractor.research_service") as svc:
        svc.research_executive = AsyncMock(side_effect=RuntimeError("network"))
        ext = InterviewExtractor(llm_provider=None)
        with pytest.raises(RuntimeError, match="network"):
            await ext.research_persona("Jane Doe", role="CEO", allow_fallback=False)


@pytest.mark.asyncio
async def test_refresh_no_op_does_not_bump_last_researched_at() -> None:
    """When merged evidence/traits match snapshot, return without updating last_researched_at."""
    pid = "p-noop"
    stale_ts = "2020-01-01T00:00:00+00:00"
    raw_hit = {"title": "t", "url": "u", "content": "x"}
    cites_row = Citation(
        source=raw_hit["title"],
        url=raw_hit["url"],
        note=(raw_hit["content"] or "")[:400],
    )
    persona = CustomPersonaConfig(
        id=pid,
        name="Test Exec",
        role="CFO",
        evidence_summary="same",
        citations=[cites_row],
        last_researched_at=stale_ts,
    )
    designer = PersonaDesigner()
    designer._initialized = True
    designer._personas[pid] = persona

    res = {
        "raw_results": [raw_hit],
        "synthesis": "same",
    }

    with (
        patch.object(
            designer,
            "_ensure_loaded",
            new=AsyncMock(),
        ),
        patch(
            "app.personas.designer.research_service.research_executive",
            new=AsyncMock(return_value=res),
        ),
        patch.object(
            InterviewExtractor,
            "research_persona",
            new=AsyncMock(side_effect=RuntimeError("skip traits")),
        ),
        patch(
            "app.personas.designer._persist_custom_persona",
            new=AsyncMock(),
        ) as persist,
    ):
        out = await designer.refresh_research_for_persona(pid)

    assert _dt_equal_iso(out.get("last_researched_at"), stale_ts)
    persist.assert_not_called()


@pytest.mark.asyncio
async def test_refresh_no_op_when_traits_match_extracted_even_if_extraction_succeeds() -> None:
    """Identical extracted traits + unchanged evidence must not persist or bump timestamp."""
    pid = "p-traits-noop"
    stale_ts = "2020-01-01T00:00:00+00:00"
    raw_hit = {"title": "t", "url": "u", "content": "x"}
    cites_row = Citation(
        source=raw_hit["title"],
        url=raw_hit["url"],
        note=(raw_hit["content"] or "")[:400],
    )
    persona = CustomPersonaConfig(
        id=pid,
        name="Test Exec",
        role="CFO",
        evidence_summary="same",
        citations=[cites_row],
        last_researched_at=stale_ts,
        risk_tolerance="moderate",
        information_bias="balanced",
        decision_speed="moderate",
        authority_level=5,
        coalition_tendencies=0.5,
        incentive_structure=[],
        behavioral_axioms=[],
    )
    designer = PersonaDesigner()
    designer._initialized = True
    designer._personas[pid] = persona

    res = {
        "raw_results": [raw_hit],
        "synthesis": "same",
    }

    matching_traits = ExtractedPersona(
        name="Test Exec",
        role="CFO",
        risk_tolerance="moderate",
        information_bias="balanced",
        decision_speed="moderate",
        authority_level=5,
        coalition_tendencies=0.5,
        incentive_structure=[],
        behavioral_axioms=[],
        extraction_confidence=0.6,
    )

    with (
        patch.object(
            designer,
            "_ensure_loaded",
            new=AsyncMock(),
        ),
        patch(
            "app.personas.designer.research_service.research_executive",
            new=AsyncMock(return_value=res),
        ),
        patch.object(
            InterviewExtractor,
            "research_persona",
            new=AsyncMock(return_value=matching_traits),
        ),
        patch(
            "app.personas.designer._persist_custom_persona",
            new=AsyncMock(),
        ) as persist,
    ):
        out = await designer.refresh_research_for_persona(pid)

    assert _dt_equal_iso(out.get("last_researched_at"), stale_ts)
    persist.assert_not_called()


def test_refresh_research_503_includes_retry_after_seconds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def boom(pid: str) -> None:
        raise ResearchRefreshError(
            "Research service failed",
            retry_after_seconds=42,
        )

    monkeypatch.setattr(persona_designer, "refresh_research_for_persona", boom)

    with TestClient(app) as client:
        r = client.post("/api/personas/designer/x/refresh-research")
    assert r.status_code == 503
    assert r.json()["detail"] == "Research service failed"
    assert r.headers.get("retry-after") == "42"


def test_refresh_research_503_retry_after_from_upstream_cause(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    req = httpx.Request("POST", "https://api.example/search")
    resp = httpx.Response(429, request=req, headers={"Retry-After": "120"})
    upstream = httpx.HTTPStatusError("rate limited", request=req, response=resp)

    async def boom(pid: str) -> None:
        raise ResearchRefreshError("Research service failed") from upstream

    monkeypatch.setattr(persona_designer, "refresh_research_for_persona", boom)

    with TestClient(app) as client:
        r = client.post("/api/personas/designer/x/refresh-research")
    assert r.status_code == 503
    assert r.headers.get("retry-after") == "120"


def test_refresh_research_503_no_retry_after_without_hint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def boom(pid: str) -> None:
        raise ResearchRefreshError("No research results returned.")

    monkeypatch.setattr(persona_designer, "refresh_research_for_persona", boom)

    with TestClient(app) as client:
        r = client.post("/api/personas/designer/x/refresh-research")
    assert r.status_code == 503
    assert r.headers.get("retry-after") is None
