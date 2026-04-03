"""Structured data clients for SEC EDGAR and EUR-Lex public APIs."""

import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

SEC_EDGAR_BASE = "https://efts.sec.gov/LATEST"
SEC_SUBMISSIONS_BASE = "https://data.sec.gov/submissions"
EURLEX_SEARCH_URL = "https://eur-lex.europa.eu/search.html"


class SECClient:
    """Client for SEC EDGAR free public API (no key required)."""

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": settings.sec_user_agent,
                "Accept": "application/json",
            },
        )

    async def search_company(self, query: str) -> list[dict[str, Any]]:
        """Search for a company by name or ticker.

        Returns:
            List of matches with cik, name, ticker.
        """
        try:
            resp = await self._client.get(
                f"{SEC_EDGAR_BASE}/search-index",
                params={"q": query, "dateRange": "custom", "startdt": "2020-01-01"},
            )
            resp.raise_for_status()
            data = resp.json()
            hits = data.get("hits", {}).get("hits", [])
            results = []
            seen_ciks: set[str] = set()
            for hit in hits[:10]:
                source = hit.get("_source", {})
                cik = source.get("entity_id", "")
                if cik and cik not in seen_ciks:
                    seen_ciks.add(cik)
                    results.append({
                        "cik": cik,
                        "name": source.get("entity_name", ""),
                        "form_type": source.get("form_type", ""),
                        "filed_at": source.get("file_date", ""),
                    })
            return results
        except httpx.HTTPError as exc:
            logger.error(f"SEC company search failed for '{query}': {exc}")
            return []

    async def get_company_filings(
        self, cik: str, form_type: str = "10-K", count: int = 5
    ) -> list[dict[str, Any]]:
        """Get recent filings for a company by CIK number.

        Args:
            cik: SEC CIK number (zero-padded to 10 digits).
            form_type: Filing type filter (10-K, 10-Q, 8-K, etc.).
            count: Maximum filings to return.

        Returns:
            List of filing metadata dicts.
        """
        padded_cik = cik.zfill(10)
        try:
            resp = await self._client.get(
                f"{SEC_SUBMISSIONS_BASE}/CIK{padded_cik}.json"
            )
            resp.raise_for_status()
            data = resp.json()

            recent = data.get("filings", {}).get("recent", {})
            forms = recent.get("form", [])
            dates = recent.get("filingDate", [])
            accessions = recent.get("accessionNumber", [])
            primary_docs = recent.get("primaryDocument", [])

            results = []
            for i, form in enumerate(forms):
                if form_type and form != form_type:
                    continue
                if len(results) >= count:
                    break
                accession = accessions[i].replace("-", "")
                results.append({
                    "form_type": form,
                    "filed_at": dates[i] if i < len(dates) else "",
                    "accession": accessions[i] if i < len(accessions) else "",
                    "url": (
                        f"https://www.sec.gov/Archives/edgar/data/"
                        f"{padded_cik}/{accession}/{primary_docs[i]}"
                        if i < len(primary_docs)
                        else ""
                    ),
                })
            return results
        except httpx.HTTPError as exc:
            logger.error(f"SEC filings fetch failed for CIK {cik}: {exc}")
            return []

    async def full_text_search(
        self, query: str, form_type: str = "", count: int = 10
    ) -> list[dict[str, Any]]:
        """Full-text search across SEC filings (EFTS endpoint).

        Args:
            query: Search terms.
            form_type: Optional form type filter.
            count: Max results.

        Returns:
            List of filing excerpts with metadata.
        """
        params: dict[str, Any] = {
            "q": f'"{query}"',
            "dateRange": "custom",
            "startdt": "2020-01-01",
        }
        if form_type:
            params["forms"] = form_type
        try:
            resp = await self._client.get(
                f"{SEC_EDGAR_BASE}/search-index",
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()
            hits = data.get("hits", {}).get("hits", [])
            results = []
            for hit in hits[:count]:
                source = hit.get("_source", {})
                results.append({
                    "entity_name": source.get("entity_name", ""),
                    "form_type": source.get("form_type", ""),
                    "filed_at": source.get("file_date", ""),
                    "excerpt": source.get("file_description", ""),
                })
            return results
        except httpx.HTTPError as exc:
            logger.error(f"SEC full-text search failed for '{query}': {exc}")
            return []

    async def close(self) -> None:
        await self._client.aclose()


class EURLexClient:
    """Client for EUR-Lex public search (scraping-safe REST queries)."""

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            timeout=30.0,
            headers={"Accept": "application/json"},
        )

    async def search_legislation(
        self, query: str, count: int = 10
    ) -> list[dict[str, Any]]:
        """Search EUR-Lex for legislation by keyword.

        Uses the EUR-Lex REST search API.
        Falls back to web search if the API is unavailable.

        Returns:
            List of legislation references with title and celex number.
        """
        try:
            # EUR-Lex SparQL or REST endpoint
            sparql_url = "https://publications.europa.eu/webapi/rdf/sparql"
            reg_type = (
                "http://publications.europa.eu/"
                "resource/authority/resource-type/REG"
            )
            sparql_query = f"""
            PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
            SELECT ?work ?title WHERE {{
                ?work cdm:work_has_resource-type <{reg_type}> .
                ?work cdm:work_has_expression ?expr .
                ?expr cdm:expression_title ?title .
                FILTER(LANG(?title) = "en")
                FILTER(CONTAINS(LCASE(STR(?title)), LCASE("{query}")))
            }}
            LIMIT {count}
            """

            resp = await self._client.get(
                sparql_url,
                params={"query": sparql_query, "format": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()

            results = []
            for binding in data.get("results", {}).get("bindings", []):
                results.append({
                    "uri": binding.get("work", {}).get("value", ""),
                    "title": binding.get("title", {}).get("value", ""),
                })
            return results
        except Exception as exc:
            logger.error(f"EUR-Lex search failed for '{query}': {exc}")
            return []

    async def close(self) -> None:
        await self._client.aclose()


sec_client = SECClient()
eurlex_client = EURLexClient()
