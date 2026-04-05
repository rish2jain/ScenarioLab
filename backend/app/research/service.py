"""Autoresearch service — orchestrates web search, structured APIs, and synthesis."""

import logging
from typing import Any

from app.research.structured import eurlex_client, sec_client
from app.research.synthesizer import research_synthesizer
from app.research.web_search import web_search_client

logger = logging.getLogger(__name__)


class ResearchService:
    """Unified research interface combining web search,
    structured APIs, and LLM synthesis."""

    def __init__(self) -> None:
        self.web = web_search_client
        self.sec = sec_client
        self.eurlex = eurlex_client
        self.synthesizer = research_synthesizer

    # ---- High-level research methods used by other modules ----

    async def research_company(self, company_name: str, *, include_filings: bool = True) -> dict[str, Any]:
        """Research a company: web search + SEC filings + synthesis.

        Returns:
            Dict with keys: summary, financials, filings, competitors, recent_news.
        """
        # Parallel-ish data gathering
        web_results = await self.web.search(
            f"{company_name} company overview financials competitors strategy",
            max_results=8,
        )

        news_results = await self.web.search(
            f"{company_name} latest news",
            topic="news",
            max_results=5,
        )

        filings: list[dict[str, Any]] = []
        if include_filings:
            sec_matches = await self.sec.search_company(company_name)
            if sec_matches:
                cik = sec_matches[0].get("cik", "")
                if cik:
                    filings = await self.sec.get_company_filings(cik, count=3)

        # Synthesize
        all_results = web_results + news_results
        synthesis = await self.synthesizer.synthesize(
            all_results,
            purpose=f"Company research profile for {company_name}",
            output_schema="""{
                "company_name": "string",
                "industry": "string",
                "market_position": "string",
                "key_competitors": ["string"],
                "recent_developments": ["string"],
                "financial_highlights": "string",
                "strategic_priorities": ["string"],
                "risks": ["string"]
            }""",
        )

        return {
            "synthesis": synthesis,
            "filings": filings,
            "raw_web_results": web_results[:5],
            "raw_news": news_results,
        }

    async def research_industry(self, industry: str) -> dict[str, Any]:
        """Research an industry sector: market size, key players, trends, regulations.

        Returns:
            Dict with keys: synthesis, raw_results.
        """
        results = await self.web.search(
            f"{industry} industry overview market size " f"key players trends regulations 2024 2025",
            max_results=10,
        )

        synthesis = await self.synthesizer.synthesize(
            results,
            purpose=f"Industry landscape analysis for {industry}",
            output_schema="""{
                "industry": "string",
                "market_size": "string",
                "growth_rate": "string",
                "key_players": ["string"],
                "trends": ["string"],
                "regulatory_landscape": "string",
                "challenges": ["string"]
            }""",
        )

        return {"synthesis": synthesis, "raw_results": results[:5]}

    async def research_regulation(self, regulation_name: str, *, jurisdiction: str = "") -> dict[str, Any]:
        """Research a regulation: text, requirements, enforcement precedent.

        Returns:
            Dict with keys: synthesis, eurlex_results, web_results.
        """
        # Web search for regulation overview and enforcement
        web_results = await self.web.search(
            f"{regulation_name} regulation requirements compliance penalties " f"{jurisdiction}".strip(),
            max_results=10,
        )

        enforcement_results = await self.web.search(
            f"{regulation_name} enforcement actions penalties fines precedent",
            max_results=5,
        )

        # EUR-Lex for EU regulations
        eurlex_results: list[dict[str, Any]] = []
        is_eu = jurisdiction.lower() in ("eu", "european union", "")
        if is_eu or "eu" in regulation_name.lower():
            eurlex_results = await self.eurlex.search_legislation(regulation_name)

        all_results = web_results + enforcement_results
        synthesis = await self.synthesizer.synthesize(
            all_results,
            purpose=f"Regulatory analysis of {regulation_name}",
            output_schema="""{
                "regulation_name": "string",
                "jurisdiction": "string",
                "key_requirements": ["string"],
                "affected_parties": ["string"],
                "compliance_deadlines": [
                    {"deadline": "string", "description": "string"}
                ],
                "penalties": [
                    {"type": "string", "severity": "string"}
                ],
                "enforcement_precedents": ["string"],
                "practical_implications": ["string"]
            }""",
        )

        return {
            "synthesis": synthesis,
            "eurlex_results": eurlex_results,
            "raw_web_results": web_results[:5],
        }

    async def research_executive(self, name: str, *, company: str = "", role: str = "") -> dict[str, Any]:
        """Research an executive's public behavior, statements, and decision patterns.

        Returns:
            Dict with keys: synthesis, raw_results.
        """
        query_parts = [name]
        if company:
            query_parts.append(company)
        if role:
            query_parts.append(role)
        query_parts.append("leadership style decisions statements interview")

        results = await self.web.search(" ".join(query_parts), max_results=8)

        earnings_results = await self.web.search(
            f"{name} {company} earnings call strategy priorities".strip(),
            max_results=5,
        )

        all_results = results + earnings_results
        synthesis = await self.synthesizer.synthesize(
            all_results,
            purpose=f"Executive behavior profile for {name} ({role} at {company})",
            output_schema="""{
                "name": "string",
                "role": "string",
                "company": "string",
                "leadership_style": "string",
                "risk_tolerance": "conservative|moderate|aggressive",
                "decision_speed": "fast|moderate|slow",
                "information_bias": "qualitative|quantitative|balanced",
                "known_priorities": ["string"],
                "notable_decisions": ["string"],
                "public_statements": ["string"],
                "coalition_tendencies": "description of alliance-building behavior"
            }""",
        )

        return {"synthesis": synthesis, "raw_results": all_results[:5]}

    async def research_historical_case(self, case_description: str, *, tags: list[str] | None = None) -> dict[str, Any]:
        """Research a historical business/regulatory case for backtesting.

        Returns:
            Dict with keys: synthesis, raw_results.
        """
        tag_str = " ".join(tags) if tags else ""
        results = await self.web.search(
            f"{case_description} outcome timeline stakeholders {tag_str}".strip(),
            max_results=10,
        )

        timeline_results = await self.web.search(
            f"{case_description} timeline chronology milestones",
            max_results=5,
        )

        all_results = results + timeline_results
        synthesis = await self.synthesizer.synthesize(
            all_results,
            purpose=f"Historical case analysis: {case_description}",
            output_schema="""{
                "case_name": "string",
                "description": "string",
                "tags": ["string"],
                "stakeholder_stances": {"stakeholder_name": "their stance and actions"},
                "timeline": {
                    "duration_description": "string",
                    "key_milestones": ["string"]
                },
                "outcome": {
                    "summary": "string",
                    "key_decisions": ["string"]
                },
                "lessons_learned": ["string"]
            }""",
        )

        return {"synthesis": synthesis, "raw_results": all_results[:5]}

    async def augment_text(self, text: str, *, purpose: str = "simulation seed material") -> dict[str, Any]:
        """Identify entities in text and research them to augment context.

        Returns:
            Dict with keys: entities_found, augmented_context, raw_results.
        """
        # First, use LLM to extract researchable entities
        import json

        from app.llm.factory import get_llm_provider
        from app.llm.provider import LLMMessage

        llm = get_llm_provider()
        extract_prompt = (
            "Extract key entities that would benefit "
            "from external research.\n\n"
            f"TEXT:\n{text[:3000]}\n\n"
            "Return a JSON array of objects:\n"
            '[{{"name": "entity name", '
            '"type": "company|person|regulation|industry|event", '
            '"search_query": "optimal search query"}}]\n\n'
            "Focus on: companies, executives, regulations, "
            "industries, and major events.\n"
            "Return 3-8 entities max. Respond with valid JSON only."
        )

        try:
            sys_msg = "Extract researchable entities. " "Respond with valid JSON only."
            response = await llm.generate(
                messages=[
                    LLMMessage(role="system", content=sys_msg),
                    LLMMessage(role="user", content=extract_prompt),
                ],
                temperature=0.2,
                max_tokens=500,
            )
            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            entities = json.loads(content.strip())
        except Exception as exc:
            logger.error(f"Entity extraction failed: {exc}")
            entities = []

        # Research each entity
        all_results: list[dict] = []
        for entity in entities[:5]:
            query = entity.get("search_query", entity.get("name", ""))
            results = await self.web.search(query, max_results=3)
            all_results.extend(results)

        # Synthesize augmented context
        summary = await self.synthesizer.summarize(
            all_results,
            purpose=f"Augmenting {purpose} with external research",
            max_words=800,
        )

        return {
            "entities_found": entities,
            "augmented_context": summary,
            "raw_results": all_results[:10],
        }


research_service = ResearchService()
