"""Unit tests for ResearchService with mocked web/SEC/synthesizer (no live APIs)."""

from unittest.mock import AsyncMock

import pytest

from app.research.service import ResearchService


@pytest.fixture
def service() -> ResearchService:
    svc = ResearchService()
    svc.web = AsyncMock()
    svc.sec = AsyncMock()
    svc.eurlex = AsyncMock()
    svc.synthesizer = AsyncMock()
    return svc


@pytest.mark.asyncio
async def test_research_company_aggregates_mocked_sources(service: ResearchService):
    service.web.search = AsyncMock(
        side_effect=[
            [{"title": "Overview", "url": "https://ex.com/a", "content": "co"}],
            [{"title": "News", "url": "https://ex.com/n", "content": "news"}],
        ]
    )
    service.sec.search_company = AsyncMock(return_value=[{"cik": "0000320193"}])
    service.sec.get_company_filings = AsyncMock(return_value=[{"form": "10-K", "accession": "x"}])
    service.synthesizer.synthesize = AsyncMock(return_value={"company_name": "Acme"})

    out = await service.research_company("Acme Corp", include_filings=True)

    assert out["synthesis"]["company_name"] == "Acme"
    assert out["filings"][0]["form"] == "10-K"
    assert len(out["raw_web_results"]) == 1
    assert len(out["raw_news"]) == 1
    assert service.web.search.await_count == 2
    service.sec.get_company_filings.assert_awaited_once()


@pytest.mark.asyncio
async def test_research_company_skips_filings_when_disabled(service: ResearchService):
    service.web.search = AsyncMock(return_value=[])
    service.synthesizer.synthesize = AsyncMock(return_value={})

    out = await service.research_company("Acme", include_filings=False)

    assert out["filings"] == []
    service.sec.search_company.assert_not_called()


@pytest.mark.asyncio
async def test_research_industry_returns_synthesis(service: ResearchService):
    service.web.search = AsyncMock(return_value=[{"title": "Sector", "content": "growth"}])
    service.synthesizer.synthesize = AsyncMock(return_value={"industry": "fintech"})

    out = await service.research_industry("fintech")

    assert out["synthesis"]["industry"] == "fintech"
    assert out["raw_results"]
    service.web.search.assert_awaited_once()


@pytest.mark.asyncio
async def test_research_regulation_queries_eurlex_for_eu(service: ResearchService):
    service.web.search = AsyncMock(return_value=[{"title": "GDPR", "content": "rules"}])
    service.eurlex.search_legislation = AsyncMock(return_value=[{"celex": "32016R0679"}])
    service.synthesizer.synthesize = AsyncMock(return_value={"regulation_name": "GDPR"})

    out = await service.research_regulation("GDPR", jurisdiction="eu")

    assert out["eurlex_results"][0]["celex"] == "32016R0679"
    service.eurlex.search_legislation.assert_awaited_once()


@pytest.mark.asyncio
async def test_research_executive_builds_profile(service: ResearchService):
    service.web.search = AsyncMock(
        side_effect=[
            [{"title": "Bio", "content": "leader"}],
            [{"title": "Earnings", "content": "call"}],
        ]
    )
    service.synthesizer.synthesize = AsyncMock(return_value={"name": "Jane Doe"})

    out = await service.research_executive("Jane Doe", company="Acme", role="CEO")

    assert out["synthesis"]["name"] == "Jane Doe"
    assert len(out["raw_results"]) == 2
    assert service.web.search.await_count == 2
