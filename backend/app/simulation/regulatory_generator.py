"""Regulatory scenario generator for war-gaming simulations."""

import json
import logging
from typing import Any

from pydantic import BaseModel, Field

from app.llm.provider import LLMMessage, LLMProvider
from app.research.service import research_service

logger = logging.getLogger(__name__)


class RegulatoryImpact(BaseModel):
    """A single identified impact from regulation."""

    impact: str
    category: str  # operational, financial, reputational, strategic
    severity: str  # low, medium, high, critical
    confidence: float = Field(..., ge=0.0, le=1.0)
    affected_departments: list[str] = []


class RegulatoryExtraction(BaseModel):
    """Extracted regulatory information."""

    regulation_name: str
    key_requirements: list[str]
    affected_parties: list[str]
    compliance_deadlines: list[dict[str, str]]  # {deadline, description}
    penalties: list[dict[str, str]]  # {type, description, severity}


class AgentRosterEntry(BaseModel):
    """An agent entry for the simulation roster."""

    role: str
    archetype_id: str
    customization: dict[str, Any] = {}


class SimulationScenarioConfig(BaseModel):
    """Full scenario configuration ready for simulation creation."""

    name: str
    description: str
    environment_type: str = "war_room"
    regulation_summary: RegulatoryExtraction
    agent_roster: list[AgentRosterEntry]
    round_structure: dict[str, Any]
    expected_deliverables: list[str]
    parameters: dict[str, Any] = {}


class RegulatoryGeneratorResult(BaseModel):
    """Complete result from regulatory scenario generation."""

    scenario_config: SimulationScenarioConfig
    impact_assessment: list[RegulatoryImpact]
    generation_metadata: dict[str, Any] = {}


class RegulatoryScenarioGenerator:
    """Generates simulation scenarios from regulatory text."""

    # Industry-specific role mappings
    INDUSTRY_ROLES: dict[str, list[dict[str, str]]] = {
        "financial_services": [
            {"role": "Chief Compliance Officer",
             "archetype_id": "general_counsel"},
            {"role": "Head of Trading",
             "archetype_id": "operations_head"},
            {"role": "Treasury Manager", "archetype_id": "cfo"},
        ],
        "healthcare": [
            {"role": "Chief Medical Officer", "archetype_id": "cro"},
            {"role": "Patient Safety Director",
             "archetype_id": "operations_head"},
            {"role": "HIPAA Compliance Officer",
             "archetype_id": "general_counsel"},
        ],
        "technology": [
            {"role": "CTO", "archetype_id": "ceo"},
            {"role": "Data Privacy Officer", "archetype_id": "cro"},
            {"role": "Product Security Lead",
             "archetype_id": "operations_head"},
        ],
        "energy": [
            {"role": "Environmental Compliance Director",
             "archetype_id": "cro"},
            {"role": "Operations Director",
             "archetype_id": "operations_head"},
            {"role": "Government Affairs Lead",
             "archetype_id": "strategy_vp"},
        ],
        "manufacturing": [
            {"role": "Supply Chain Director",
             "archetype_id": "operations_head"},
            {"role": "Quality Assurance Head", "archetype_id": "cro"},
            {"role": "Environmental Health & Safety Manager",
             "archetype_id": "general_counsel"},
        ],
        "general": [
            {"role": "Compliance Director",
             "archetype_id": "general_counsel"},
            {"role": "Operations Lead",
             "archetype_id": "operations_head"},
        ],
    }

    # Core roles always included in regulatory scenarios
    CORE_ROLES: list[dict[str, str]] = [
        {"role": "Regulator", "archetype_id": "regulator"},
        {"role": "Chief Risk Officer", "archetype_id": "cro"},
        {"role": "General Counsel", "archetype_id": "general_counsel"},
        {"role": "CEO", "archetype_id": "ceo"},
    ]

    def __init__(self, llm_provider: LLMProvider | None = None):
        self.llm = llm_provider

    async def auto_fetch_regulation(
        self,
        regulation_name: str,
        industry: str = "general",
        jurisdiction: str = "",
    ) -> RegulatoryGeneratorResult:
        """Generate a scenario by auto-researching a regulation by name.

        Uses the research service to fetch regulation data, then builds
        a full simulation scenario from the synthesized results.

        Args:
            regulation_name: Name of the regulation to research
            industry: Industry context for role selection
            jurisdiction: Optional jurisdiction filter (e.g. "EU", "US")

        Returns:
            RegulatoryGeneratorResult with scenario config and impacts
        """
        if not self.llm:
            raise ValueError("LLM provider required for scenario generation")

        logger.info(
            f"Auto-fetching regulation: {regulation_name} "
            f"(jurisdiction={jurisdiction}, industry={industry})"
        )

        # Step 1: Research the regulation
        research_data = await research_service.research_regulation(
            regulation_name, jurisdiction=jurisdiction
        )
        synthesis = research_data.get("synthesis", {})

        # Step 2: Map synthesis to RegulatoryExtraction
        extraction = RegulatoryExtraction(
            regulation_name=synthesis.get(
                "regulation_name", regulation_name
            ),
            key_requirements=synthesis.get(
                "key_requirements", ["Compliance required"]
            ),
            affected_parties=synthesis.get(
                "affected_parties", ["Organization"]
            ),
            compliance_deadlines=synthesis.get("compliance_deadlines", []),
            penalties=synthesis.get("penalties", []),
        )

        # Step 3: Generate agent roster
        roster = self._generate_agent_roster(industry, extraction)

        # Step 4: Build scenario config
        scenario_config = self._build_scenario_config(
            extraction, roster, industry
        )

        # Step 5: Build regulatory text from synthesis for impact analysis
        synthesis_text_parts = [
            f"Regulation: {extraction.regulation_name}",
            f"Jurisdiction: {synthesis.get('jurisdiction', jurisdiction)}",
            "Key Requirements: "
            + "; ".join(extraction.key_requirements),
            "Affected Parties: "
            + ", ".join(extraction.affected_parties),
        ]
        enforcement = synthesis.get("enforcement_precedents", [])
        if enforcement:
            synthesis_text_parts.append(
                "Enforcement Precedents: " + "; ".join(enforcement)
            )
        implications = synthesis.get("practical_implications", [])
        if implications:
            synthesis_text_parts.append(
                "Practical Implications: " + "; ".join(implications)
            )
        synthesized_text = "\n".join(synthesis_text_parts)

        # Step 6: Identify impacts
        impacts = await self.identify_impacts(synthesized_text, industry)

        return RegulatoryGeneratorResult(
            scenario_config=scenario_config,
            impact_assessment=impacts,
            generation_metadata={
                "industry": industry,
                "jurisdiction": jurisdiction,
                "regulation_name": extraction.regulation_name,
                "requirements_count": len(extraction.key_requirements),
                "source": "autoresearch",
                "eurlex_results_count": len(
                    research_data.get("eurlex_results", [])
                ),
            },
        )

    async def generate_scenario(
        self,
        regulatory_text: str = "",
        industry: str = "general",
        regulation_name: str | None = None,
    ) -> RegulatoryGeneratorResult:
        """Generate a full simulation scenario from regulatory text.

        Args:
            regulatory_text: The regulatory document text
            industry: Industry context for role selection
            regulation_name: Optional regulation name; when provided and
                regulatory_text is empty, auto-fetches via research service

        Returns:
            RegulatoryGeneratorResult with scenario config and impacts
        """
        # Auto-fetch when regulation_name is provided and no text given
        if regulation_name and not regulatory_text.strip():
            return await self.auto_fetch_regulation(
                regulation_name=regulation_name,
                industry=industry,
            )

        if not self.llm:
            raise ValueError("LLM provider required for scenario generation")

        logger.info(f"Generating regulatory scenario for industry: {industry}")

        # Step 1: Extract regulatory information
        extraction = await self._extract_regulatory_info(regulatory_text)

        # Step 2: Generate agent roster
        roster = self._generate_agent_roster(industry, extraction)

        # Step 3: Generate simulation config
        scenario_config = self._build_scenario_config(
            extraction, roster, industry
        )

        # Step 4: Identify impacts
        impacts = await self.identify_impacts(regulatory_text, industry)

        return RegulatoryGeneratorResult(
            scenario_config=scenario_config,
            impact_assessment=impacts,
            generation_metadata={
                "industry": industry,
                "regulation_name": extraction.regulation_name,
                "requirements_count": len(extraction.key_requirements),
            },
        )

    async def _extract_regulatory_info(
        self, regulatory_text: str
    ) -> RegulatoryExtraction:
        """Use LLM to parse and extract regulatory information."""
        prompt = f"""Analyze the following regulatory text and extract key information.

REGULATORY TEXT:
{regulatory_text[:4000]}

Extract and return a JSON object with this exact structure:
{{
    "regulation_name": "Short name of the regulation",
    "key_requirements": ["requirement 1", "requirement 2", ...],
    "affected_parties": ["party 1", "party 2", ...],
    "compliance_deadlines": [
        {{"deadline": "date or timeframe", "description": "what must be done"}}
    ],
    "penalties": [
        {{"type": "fine/restriction/etc",
          "description": "penalty details",
          "severity": "low/medium/high"}}
    ]
}}

Respond with valid JSON only, no markdown formatting."""

        response = await self.llm.generate(
            messages=[
                LLMMessage(
                    role="system",
                    content=(
                        "You are a regulatory analyst. Extract structured "
                        "information from regulatory text. Respond with "
                        "valid JSON only."
                    ),
                ),
                LLMMessage(role="user", content=prompt),
            ],
            temperature=0.3,
            max_tokens=1000,
        )

        try:
            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            data = json.loads(content)
            return RegulatoryExtraction(**data)
        except Exception as e:
            logger.error(f"Failed to parse regulatory extraction: {e}")
            # Return default extraction
            return RegulatoryExtraction(
                regulation_name="Unknown Regulation",
                key_requirements=["Compliance required"],
                affected_parties=["Organization"],
                compliance_deadlines=[],
                penalties=[],
            )

    def _generate_agent_roster(
        self,
        industry: str,
        extraction: RegulatoryExtraction,
    ) -> list[AgentRosterEntry]:
        """Generate agent roster based on industry and regulation type."""
        roster: list[AgentRosterEntry] = []

        # Add core roles
        for role_info in self.CORE_ROLES:
            roster.append(AgentRosterEntry(
                role=role_info["role"],
                archetype_id=role_info["archetype_id"],
            ))

        # Add industry-specific roles
        industry_key = industry.lower().replace("-", "_").replace(" ", "_")
        industry_roles = self.INDUSTRY_ROLES.get(
            industry_key, self.INDUSTRY_ROLES["general"]
        )
        for role_info in industry_roles:
            roster.append(AgentRosterEntry(
                role=role_info["role"],
                archetype_id=role_info["archetype_id"],
            ))

        # Add regulation-specific roles based on affected parties
        for party in extraction.affected_parties[:3]:
            party_lower = party.lower()
            if "board" in party_lower:
                roster.append(AgentRosterEntry(
                    role="Board Member",
                    archetype_id="board_member",
                ))
            elif "investor" in party_lower or "shareholder" in party_lower:
                roster.append(AgentRosterEntry(
                    role="Investor Representative",
                    archetype_id="activist_investor",
                ))
            elif "union" in party_lower or "employee" in party_lower:
                roster.append(AgentRosterEntry(
                    role="Employee Representative",
                    archetype_id="union_rep",
                ))
            elif "customer" in party_lower:
                roster.append(AgentRosterEntry(
                    role="Customer Advocate",
                    archetype_id="media_stakeholder",
                    customization={"focus": "customer-perspective"},
                ))

        return roster

    def _build_scenario_config(
        self,
        extraction: RegulatoryExtraction,
        roster: list[AgentRosterEntry],
        industry: str,
    ) -> SimulationScenarioConfig:
        """Build the full scenario configuration."""
        # Determine round structure based on complexity
        requirements_count = len(extraction.key_requirements)
        if requirements_count > 10:
            total_rounds = 12
        elif requirements_count > 5:
            total_rounds = 8
        else:
            total_rounds = 6

        round_structure = {
            "total_rounds": total_rounds,
            "phases": [
                {"name": "assessment",
                 "description": "Assess regulatory impact"},
                {"name": "planning",
                 "description": "Develop compliance strategy"},
                {"name": "deliberation",
                 "description": "Debate implementation approach"},
                {"name": "decision",
                 "description": "Finalize compliance plan"},
            ],
            "decision_points": [
                {"round": total_rounds // 2, "type": "mid-course review"},
                {"round": total_rounds, "type": "final decision"},
            ],
        }

        expected_deliverables = [
            "Regulatory impact assessment",
            "Compliance roadmap",
            "Resource allocation plan",
            "Risk mitigation strategy",
            "Timeline with milestones",
        ]

        # Add regulation-specific deliverables
        if extraction.compliance_deadlines:
            expected_deliverables.append("Deadline adherence plan")
        if extraction.penalties:
            expected_deliverables.append("Penalty avoidance strategy")

        return SimulationScenarioConfig(
            name=f"{extraction.regulation_name} Compliance War Game",
            description=(
                f"Strategic war game for {industry} industry "
                f"responding to {extraction.regulation_name}"
            ),
            environment_type="war_room",
            regulation_summary=extraction,
            agent_roster=roster,
            round_structure=round_structure,
            expected_deliverables=expected_deliverables,
            parameters={
                "industry": industry,
                "regulation_name": extraction.regulation_name,
                "complexity": "high" if requirements_count > 10 else "medium",
            },
        )

    async def identify_impacts(
        self,
        regulatory_text: str,
        organization_context: str = "",
    ) -> list[RegulatoryImpact]:
        """Identify expected impacts with confidence scores.

        Args:
            regulatory_text: The regulatory document text
            organization_context: Optional context about the organization

        Returns:
            List of identified impacts with confidence scores
        """
        if not self.llm:
            raise ValueError("LLM provider required for impact identification")

        context_section = ""
        if organization_context:
            context_section = (
                f"\n\nORGANIZATION CONTEXT:\n{organization_context}"
            )

        prompt = f"""Analyze the following regulatory text and identify
expected organizational impacts.

REGULATORY TEXT:
{regulatory_text[:4000]}{context_section}

Identify impacts and return a JSON array with this structure:
[
    {{
        "impact": "Description of the specific impact",
        "category": "operational|financial|reputational|strategic",
        "severity": "low|medium|high|critical",
        "confidence": 0.0-1.0,
        "affected_departments": ["dept1", "dept2"]
    }}
]

Identify 5-10 significant impacts. Respond with valid JSON only."""

        response = await self.llm.generate(
            messages=[
                LLMMessage(
                    role="system",
                    content=(
                        "You are a regulatory impact analyst. Identify "
                        "organizational impacts from regulations. Respond "
                        "with valid JSON only."
                    ),
                ),
                LLMMessage(role="user", content=prompt),
            ],
            temperature=0.4,
            max_tokens=1500,
        )

        try:
            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            data = json.loads(content)
            impacts = []
            for item in data:
                impacts.append(RegulatoryImpact(**item))
            return impacts
        except Exception as e:
            logger.error(f"Failed to parse impact assessment: {e}")
            return [
                RegulatoryImpact(
                    impact="Regulatory compliance required",
                    category="operational",
                    severity="medium",
                    confidence=0.7,
                    affected_departments=["Compliance", "Operations"],
                ),
            ]
