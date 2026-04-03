"""Market Intelligence Service for real-time data integration."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.config import settings
from app.llm.database import MarketIntelligenceRepository, init_llm_tables
from app.llm.factory import get_llm_provider
from app.research.service import research_service

logger = logging.getLogger(__name__)

# In-memory store for simulation configurations
_market_configs: dict[str, dict] = {}
_market_data_cache: dict[str, dict] = {}


class MarketIntelligenceService:
    """Service for fetching and filtering market intelligence data."""

    def __init__(self):
        self.alpha_vantage_base = "https://www.alphavantage.co/query"
        self.news_api_base = "https://newsapi.org/v2"
        self._http_client = httpx.AsyncClient(timeout=30.0)
        self._repo = MarketIntelligenceRepository()
        self._initialized = False

    async def _ensure_initialized(self):
        """Ensure tables are initialized."""
        if not self._initialized:
            try:
                await init_llm_tables()
                self._initialized = True
            except Exception as e:
                logger.warning(f"Failed to init LLM tables: {e}")

    async def fetch_stock_data(
        self, symbols: list[str], period: str = "1d"
    ) -> dict[str, Any]:
        """Fetch stock data from Alpha Vantage API.

        Args:
            symbols: List of stock symbols to fetch.
            period: Time period (not used directly, Alpha Vantage returns daily).

        Returns:
            Dictionary with stock data per symbol.
        """
        if not settings.alpha_vantage_api_key:
            logger.warning("Alpha Vantage API key not set, returning mock data")
            return self._get_mock_stock_data(symbols)

        results = {}
        for symbol in symbols:
            try:
                response = await self._http_client.get(
                    self.alpha_vantage_base,
                    params={
                        "function": "TIME_SERIES_DAILY",
                        "symbol": symbol,
                        "apikey": settings.alpha_vantage_api_key,
                    },
                )
                response.raise_for_status()
                data = response.json()

                # Extract latest prices
                time_series = data.get("Time Series (Daily)", {})
                if time_series:
                    latest_date = sorted(time_series.keys(), reverse=True)[0]
                    latest = time_series[latest_date]
                    prev_date = sorted(time_series.keys(), reverse=True)[1] if len(time_series) > 1 else latest_date
                    prev = time_series.get(prev_date, latest)

                    results[symbol] = {
                        "symbol": symbol,
                        "price": float(latest.get("4. close", 0)),
                        "change": float(latest.get("4. close", 0)) - float(prev.get("4. close", 0)),
                        "change_percent": (
                            (float(latest.get("4. close", 0)) - float(prev.get("4. close", 0)))
                            / float(prev.get("4. close", 1))
                            * 100
                        ),
                        "volume": int(latest.get("5. volume", 0)),
                        "date": latest_date,
                    }
                else:
                    results[symbol] = {"error": "No data available", "symbol": symbol}

            except httpx.HTTPError as e:
                logger.error(f"Failed to fetch stock data for {symbol}: {e}")
                results[symbol] = {"error": str(e), "symbol": symbol}

        return results

    def _get_mock_stock_data(self, symbols: list[str]) -> dict[str, Any]:
        """Generate mock stock data for testing."""
        import random

        base_prices = {"AAPL": 175.0, "MSFT": 375.0, "GOOGL": 140.0, "AMZN": 145.0}
        results = {}
        for symbol in symbols:
            base = base_prices.get(symbol, random.uniform(50, 200))
            change = random.uniform(-5, 5)
            results[symbol] = {
                "symbol": symbol,
                "price": round(base, 2),
                "change": round(change, 2),
                "change_percent": round(change / base * 100, 2),
                "volume": random.randint(1000000, 50000000),
                "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "mock": True,
            }
        return results

    async def fetch_news(
        self, query: str, days_back: int = 7
    ) -> list[dict[str, Any]]:
        """Fetch news articles from NewsAPI.

        Args:
            query: Search query for news.
            days_back: Number of days to look back.

        Returns:
            List of news articles with relevance scores.
        """
        if not settings.news_api_key:
            logger.warning("News API key not set, returning mock news")
            return self._get_mock_news(query)

        try:
            from_date = (
                datetime.now(timezone.utc) - timedelta(days=days_back)
            ).strftime("%Y-%m-%d")

            response = await self._http_client.get(
                f"{self.news_api_base}/everything",
                params={
                    "q": query,
                    "from": from_date,
                    "sortBy": "publishedAt",
                    "apiKey": settings.news_api_key,
                    "pageSize": 20,
                },
            )
            response.raise_for_status()
            data = response.json()

            articles = []
            for article in data.get("articles", []):
                articles.append({
                    "title": article.get("title", ""),
                    "description": article.get("description", ""),
                    "source": article.get("source", {}).get("name", "Unknown"),
                    "url": article.get("url", ""),
                    "published_at": article.get("publishedAt", ""),
                    "relevance_score": 0.5,  # Default, will be filtered later
                })

            return articles

        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch news: {e}")
            return self._get_mock_news(query)

    def _get_mock_news(self, query: str) -> list[dict[str, Any]]:
        """Generate mock news for testing."""
        mock_articles = [
            {
                "title": f"Market Analysis: {query} Sector Shows Growth",
                "description": f"Recent analysis indicates positive trends in the {query} sector as companies adapt to changing market conditions.",
                "source": "Market Watch",
                "url": "https://example.com/news/1",
                "published_at": datetime.now(timezone.utc).isoformat(),
                "relevance_score": 0.8,
            },
            {
                "title": f"Regulatory Update Affects {query} Industry",
                "description": f"New regulations could impact how {query} companies operate in the coming quarters.",
                "source": "Business Journal",
                "url": "https://example.com/news/2",
                "published_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
                "relevance_score": 0.75,
            },
            {
                "title": f"Executive Interview: Strategic Vision for {query}",
                "description": f"Industry leaders discuss their outlook and strategic priorities for the {query} market.",
                "source": "Finance Daily",
                "url": "https://example.com/news/3",
                "published_at": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
                "relevance_score": 0.6,
            },
        ]
        return mock_articles

    async def filter_relevance(
        self, items: list[dict], scenario_context: str
    ) -> list[dict]:
        """Filter items by relevance to the scenario using LLM.

        Args:
            items: List of items (news or market data) to filter.
            scenario_context: Context of the simulation scenario.

        Returns:
            Filtered list with relevance scores.
        """
        if not items:
            return []

        try:
            llm = get_llm_provider()
            filtered_items = []

            for item in items:
                # Create prompt for relevance scoring
                prompt = f"""Score the relevance of this item to the given scenario context.
Return only a number between 0 and 1, where 1 is highly relevant.

Scenario Context: {scenario_context}

Item:
Title: {item.get('title', '')}
Description: {item.get('description', '')}

Relevance Score:"""

                try:
                    response = await llm.generate(prompt, max_tokens=10)
                    score_text = response.strip()
                    # Extract number from response
                    import re
                    match = re.search(r"[\d.]+", score_text)
                    score = float(match.group()) if match else 0.5
                    score = max(0.0, min(1.0, score))
                except Exception:
                    score = 0.5

                item["relevance_score"] = score
                if score >= 0.5:
                    filtered_items.append(item)

            # Sort by relevance
            filtered_items.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
            return filtered_items

        except Exception as e:
            logger.error(f"Failed to filter relevance: {e}")
            # Return all items with default score
            for item in items:
                item["relevance_score"] = 0.5
            return items

    async def update_agent_worldview(
        self, simulation_id: str, market_data: dict
    ) -> dict[str, Any]:
        """Inject market intelligence into agent context.

        Args:
            simulation_id: ID of the simulation.
            market_data: Market data to inject.

        Returns:
            Summary of what was injected.
        """
        config = _market_configs.get(simulation_id, {})

        summary = {
            "simulation_id": simulation_id,
            "injected_at": datetime.now(timezone.utc).isoformat(),
            "stock_data_points": len(market_data.get("stocks", {})),
            "news_articles": len(market_data.get("news", [])),
            "sources_configured": {
                "stock_symbols": config.get("stock_symbols", []),
                "news_queries": config.get("news_queries", []),
            },
        }

        # Store in cache for retrieval
        _market_data_cache[simulation_id] = {
            "data": market_data,
            "injected_at": summary["injected_at"],
        }

        # Persist to DB
        try:
            await self._ensure_initialized()
            await self._repo.save_cache(
                simulation_id, _market_data_cache[simulation_id]
            )
        except Exception as e:
            logger.warning(f"Failed to persist market cache: {e}")

        return summary

    async def auto_research_company(self, company_name: str) -> dict[str, Any]:
        """Fetch company research via autoresearch and format for market feed.

        Args:
            company_name: Name of the company to research.

        Returns:
            Dictionary with company research data compatible with market feed structure.
        """
        try:
            result = await research_service.research_company(company_name)
            synthesis = result.get("synthesis", {})
            return {
                "type": "company_research",
                "company_name": company_name,
                "synthesis": synthesis,
                "filings": result.get("filings", []),
                "raw_web_results": result.get("raw_web_results", []),
                "raw_news": result.get("raw_news", []),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.error(f"Auto-research failed for company '{company_name}': {e}")
            return {
                "type": "company_research",
                "company_name": company_name,
                "error": str(e),
                "synthesis": {},
                "filings": [],
                "raw_web_results": [],
                "raw_news": [],
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }

    async def auto_research_industry(self, industry: str) -> dict[str, Any]:
        """Fetch industry research via autoresearch and format for market feed.

        Args:
            industry: Name of the industry to research.

        Returns:
            Dictionary with industry research data compatible with market feed structure.
        """
        try:
            result = await research_service.research_industry(industry)
            synthesis = result.get("synthesis", {})
            return {
                "type": "industry_research",
                "industry": industry,
                "synthesis": synthesis,
                "raw_results": result.get("raw_results", []),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.error(f"Auto-research failed for industry '{industry}': {e}")
            return {
                "type": "industry_research",
                "industry": industry,
                "error": str(e),
                "synthesis": {},
                "raw_results": [],
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }

    async def configure_sources(
        self, simulation_id: str, config: dict
    ) -> dict[str, Any]:
        """Configure data sources for a simulation.

        Args:
            simulation_id: ID of the simulation.
            config: Configuration with stock_symbols, news_queries, refresh_interval.

        Returns:
            Configuration confirmation.
        """
        _market_configs[simulation_id] = {
            "stock_symbols": config.get("stock_symbols", []),
            "news_queries": config.get("news_queries", []),
            "auto_research_queries": config.get("auto_research_queries", []),
            "refresh_interval": config.get("refresh_interval", 300),
            "configured_at": datetime.now(timezone.utc).isoformat(),
        }

        # Persist to DB
        try:
            await self._ensure_initialized()
            await self._repo.save_config(
                simulation_id, _market_configs[simulation_id]
            )
        except Exception as e:
            logger.warning(f"Failed to persist market config: {e}")

        return {
            "simulation_id": simulation_id,
            "status": "configured",
            "config": _market_configs[simulation_id],
        }

    async def get_market_feed(self, simulation_id: str) -> dict[str, Any]:
        """Get the latest market data feed for a simulation.

        Args:
            simulation_id: ID of the simulation.

        Returns:
            Market data feed.
        """
        # Try in-memory first
        config = _market_configs.get(simulation_id)

        # Fall back to DB
        if not config:
            try:
                await self._ensure_initialized()
                config = await self._repo.get_config(simulation_id)
                if config:
                    _market_configs[simulation_id] = config
            except Exception as e:
                logger.warning(f"Failed to get market config from DB: {e}")

        if not config:
            return {"error": "Simulation not configured for market intelligence"}

        # Fetch fresh data
        stocks = {}
        if config.get("stock_symbols"):
            stocks = await self.fetch_stock_data(config["stock_symbols"])

        news = []
        for query in config.get("news_queries", []):
            articles = await self.fetch_news(query)
            news.extend(articles)

        # Fetch auto-research data when configured
        auto_research: list[dict[str, Any]] = []
        for query in config.get("auto_research_queries", []):
            query_type = query.get("type", "company") if isinstance(query, dict) else "company"
            query_name = query.get("name", query) if isinstance(query, dict) else query
            try:
                if query_type == "industry":
                    result = await self.auto_research_industry(query_name)
                else:
                    result = await self.auto_research_company(query_name)
                auto_research.append(result)
            except Exception as e:
                logger.error(f"Auto-research query failed for '{query_name}': {e}")

        return {
            "simulation_id": simulation_id,
            "stocks": stocks,
            "news": news[:20],  # Limit to 20 articles
            "auto_research": auto_research,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }


# Global instance
market_intelligence_service = MarketIntelligenceService()
