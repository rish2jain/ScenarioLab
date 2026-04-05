"""Web search client using Tavily REST API via httpx."""

import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

TAVILY_SEARCH_URL = "https://api.tavily.com/search"


class WebSearchClient:
    """Thin wrapper around Tavily search API."""

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(timeout=30.0)

    async def search(
        self,
        query: str,
        *,
        search_depth: str = "advanced",
        max_results: int = 10,
        include_domains: list[str] | None = None,
        exclude_domains: list[str] | None = None,
        topic: str = "general",
    ) -> list[dict[str, Any]]:
        """Run a web search and return results.

        Args:
            query: Search query string.
            search_depth: "basic" or "advanced".
            max_results: Maximum number of results.
            include_domains: Only include results from these domains.
            exclude_domains: Exclude results from these domains.
            topic: "general" or "news".

        Returns:
            List of result dicts with keys: title, url, content, score.
        """
        if not settings.tavily_api_key:
            logger.warning("TAVILY_API_KEY not set, returning empty results")
            return []

        payload: dict[str, Any] = {
            "api_key": settings.tavily_api_key,
            "query": query,
            "search_depth": search_depth,
            "max_results": max_results,
            "include_answer": True,
            "topic": topic,
        }
        if include_domains:
            payload["include_domains"] = include_domains
        if exclude_domains:
            payload["exclude_domains"] = exclude_domains

        try:
            resp = await self._client.post(TAVILY_SEARCH_URL, json=payload)
            resp.raise_for_status()
            data = resp.json()

            results: list[dict[str, Any]] = []
            for item in data.get("results", []):
                results.append(
                    {
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "content": item.get("content", ""),
                        "score": item.get("score", 0.0),
                    }
                )

            answer = data.get("answer")
            if answer:
                results.insert(
                    0,
                    {
                        "title": "Tavily Summary",
                        "url": "",
                        "content": answer,
                        "score": 1.0,
                    },
                )

            return results

        except httpx.HTTPError as exc:
            logger.error(f"Web search failed for '{query}': {exc}")
            return []

    async def close(self) -> None:
        await self._client.aclose()


web_search_client = WebSearchClient()
