"""Structured interview protocol for persona extraction."""

import logging
import uuid

from pydantic import BaseModel, Field

from app.llm.provider import LLMMessage, LLMProvider
from app.research.service import research_service

logger = logging.getLogger(__name__)


class InterviewQuestion(BaseModel):
    """A single interview question for persona extraction."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    question: str
    attribute_target: str  # Which persona attribute this maps to
    follow_up: str | None = None


class InterviewProtocol(BaseModel):
    """Complete interview protocol with all questions."""

    questions: list[InterviewQuestion]


class ExtractedPersona(BaseModel):
    """Persona extracted from interview responses."""

    name: str
    role: str
    risk_tolerance: str
    information_bias: str
    decision_speed: str
    authority_level: int = Field(..., ge=1, le=10)
    coalition_tendencies: float = Field(..., ge=0.0, le=1.0)
    incentive_structure: list[str]
    behavioral_axioms: list[str]
    extraction_confidence: float = Field(..., ge=0.0, le=1.0)


class InterviewExtractor:
    """Extracts persona attributes from interview text or descriptions."""

    STANDARD_PROTOCOL: list[dict] = [
        {
            "question": "Describe your typical approach when facing a major strategic decision with significant uncertainty.",
            "attribute_target": "risk_tolerance",
            "follow_up": "Can you give a specific example where you took a bold stance despite opposition?",
        },
        {
            "question": "When evaluating proposals, what type of information do you rely on most heavily?",
            "attribute_target": "information_bias",
            "follow_up": "How do you balance quantitative data with qualitative insights?",
        },
        {
            "question": "Describe your decision-making speed. Do you prefer to decide quickly or take time for thorough analysis?",
            "attribute_target": "decision_speed",
            "follow_up": "What factors might cause you to delay a decision?",
        },
        {
            "question": "In organizational settings, how would you describe your level of influence and authority?",
            "attribute_target": "authority_level",
            "follow_up": "Can you describe a time when you overruled or significantly influenced a decision?",
        },
        {
            "question": "How do you typically approach building alliances or working with others to achieve your objectives?",
            "attribute_target": "coalition_tendencies",
            "follow_up": "Describe a coalition or alliance you formed and its outcome.",
        },
        {
            "question": "What primarily motivates your decisions and actions in a professional context?",
            "attribute_target": "incentive_structure",
            "follow_up": "How do you balance competing incentives like financial returns vs. reputation?",
        },
        {
            "question": "Describe a situation where you had to challenge the consensus or take an unpopular position.",
            "attribute_target": "behavioral_axioms",
            "follow_up": "What principles guided your stance in that situation?",
        },
        {
            "question": "How do you typically respond when you disagree with a proposal that has strong support?",
            "attribute_target": "behavioral_axioms",
            "follow_up": "Do you prefer direct confrontation or building support behind the scenes?",
        },
        {
            "question": "What role do you usually play in group decision-making settings?",
            "attribute_target": "authority_level",
            "follow_up": "Are you typically the decision-maker, advisor, or challenger?",
        },
        {
            "question": "Describe how you handle situations where there's pressure to make a quick decision.",
            "attribute_target": "decision_speed",
            "follow_up": "What information do you absolutely need before committing?",
        },
        {
            "question": "How do you evaluate risk versus opportunity in strategic contexts?",
            "attribute_target": "risk_tolerance",
            "follow_up": "What's your threshold for acceptable risk?",
        },
        {
            "question": "What core principles or rules of thumb guide your professional behavior?",
            "attribute_target": "behavioral_axioms",
            "follow_up": "Have these principles ever conflicted with organizational goals?",
        },
    ]

    def __init__(self, llm_provider: LLMProvider | None = None):
        self.llm = llm_provider

    async def extract_from_text(
        self, interview_responses: str
    ) -> ExtractedPersona:
        """Extract persona attributes from interview text responses.

        Args:
            interview_responses: Raw text of interview responses

        Returns:
            ExtractedPersona with mapped attributes
        """
        if not self.llm:
            raise ValueError("LLM provider required for extraction")

        prompt = f"""Analyze the following interview responses and extract a structured persona profile.

INTERVIEW RESPONSES:
{interview_responses}

Extract the following attributes and respond in this exact JSON format:
{{
    "name": "Person's name or identifier",
    "role": "Their professional role/title",
    "risk_tolerance": "conservative|moderate|aggressive",
    "information_bias": "qualitative|quantitative|balanced",
    "decision_speed": "fast|moderate|slow",
    "authority_level": 1-10,
    "coalition_tendencies": 0.0-1.0,
    "incentive_structure": ["financial", "reputational", "operational", "regulatory"],
    "behavioral_axioms": ["axiom 1", "axiom 2", "axiom 3"],
    "extraction_confidence": 0.0-1.0
}}

Guidelines:
- risk_tolerance: conservative (avoids risk), moderate (balanced), aggressive (embraces risk)
- information_bias: qualitative (stories/experience), quantitative (data/metrics), balanced
- decision_speed: fast (decides quickly), moderate, slow (thorough analysis)
- authority_level: 1 (low influence) to 10 (high influence/decision maker)
- coalition_tendencies: 0.0 (works alone) to 1.0 (always builds alliances)
- incentive_structure: select from "financial", "reputational", "operational", "regulatory"
- behavioral_axioms: 2-4 core principles that guide their behavior
- extraction_confidence: your confidence in the extraction (0.0-1.0)

Respond with valid JSON only."""

        try:
            response = await self.llm.generate(
                messages=[
                    LLMMessage(
                        role="system",
                        content=(
                            "You are a persona extraction specialist. "
                            "Analyze interview responses and extract structured "
                            "persona attributes. Respond with valid JSON only."
                        ),
                    ),
                    LLMMessage(role="user", content=prompt),
                ],
                temperature=0.3,
                max_tokens=800,
            )

            import json

            content = response.content.strip()
            # Remove markdown code blocks if present
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            data = json.loads(content)

            return ExtractedPersona(
                name=data.get("name", "Unknown"),
                role=data.get("role", "Unknown"),
                risk_tolerance=data.get("risk_tolerance", "moderate"),
                information_bias=data.get("information_bias", "balanced"),
                decision_speed=data.get("decision_speed", "moderate"),
                authority_level=data.get("authority_level", 5),
                coalition_tendencies=data.get("coalition_tendencies", 0.5),
                incentive_structure=data.get("incentive_structure", []),
                behavioral_axioms=data.get("behavioral_axioms", []),
                extraction_confidence=data.get("extraction_confidence", 0.5),
            )

        except Exception as e:
            logger.error(f"Failed to extract persona from interview: {e}")
            # Return a default persona on error
            return ExtractedPersona(
                name="Unknown",
                role="Unknown",
                risk_tolerance="moderate",
                information_bias="balanced",
                decision_speed="moderate",
                authority_level=5,
                coalition_tendencies=0.5,
                incentive_structure=["operational"],
                behavioral_axioms=["Pragmatic decision-maker"],
                extraction_confidence=0.0,
            )

    async def extract_from_description(
        self, stakeholder_description: str
    ) -> ExtractedPersona:
        """Extract persona from a narrative description of a stakeholder.

        Args:
            stakeholder_description: Narrative description of the stakeholder

        Returns:
            ExtractedPersona with mapped attributes
        """
        if not self.llm:
            raise ValueError("LLM provider required for extraction")

        prompt = f"""Analyze the following stakeholder description and extract a structured persona profile.

STAKEHOLDER DESCRIPTION:
{stakeholder_description}

Extract the following attributes and respond in this exact JSON format:
{{
    "name": "Person's name or identifier",
    "role": "Their professional role/title",
    "risk_tolerance": "conservative|moderate|aggressive",
    "information_bias": "qualitative|quantitative|balanced",
    "decision_speed": "fast|moderate|slow",
    "authority_level": 1-10,
    "coalition_tendencies": 0.0-1.0,
    "incentive_structure": ["financial", "reputational", "operational", "regulatory"],
    "behavioral_axioms": ["axiom 1", "axiom 2", "axiom 3"],
    "extraction_confidence": 0.0-1.0
}}

Guidelines:
- risk_tolerance: conservative (avoids risk), moderate (balanced), aggressive (embraces risk)
- information_bias: qualitative (stories/experience), quantitative (data/metrics), balanced
- decision_speed: fast (decides quickly), moderate, slow (thorough analysis)
- authority_level: 1 (low influence) to 10 (high influence/decision maker)
- coalition_tendencies: 0.0 (works alone) to 1.0 (always builds alliances)
- incentive_structure: select from "financial", "reputational", "operational", "regulatory"
- behavioral_axioms: 2-4 core principles that guide their behavior
- extraction_confidence: your confidence in the extraction (0.0-1.0)

Respond with valid JSON only."""

        try:
            response = await self.llm.generate(
                messages=[
                    LLMMessage(
                        role="system",
                        content=(
                            "You are a persona extraction specialist. "
                            "Analyze stakeholder descriptions and extract "
                            "structured persona attributes. "
                            "Respond with valid JSON only."
                        ),
                    ),
                    LLMMessage(role="user", content=prompt),
                ],
                temperature=0.3,
                max_tokens=800,
            )

            import json

            content = response.content.strip()
            # Remove markdown code blocks if present
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            data = json.loads(content)

            return ExtractedPersona(
                name=data.get("name", "Unknown"),
                role=data.get("role", "Unknown"),
                risk_tolerance=data.get("risk_tolerance", "moderate"),
                information_bias=data.get("information_bias", "balanced"),
                decision_speed=data.get("decision_speed", "moderate"),
                authority_level=data.get("authority_level", 5),
                coalition_tendencies=data.get("coalition_tendencies", 0.5),
                incentive_structure=data.get("incentive_structure", []),
                behavioral_axioms=data.get("behavioral_axioms", []),
                extraction_confidence=data.get("extraction_confidence", 0.5),
            )

        except Exception as e:
            logger.error(f"Failed to extract persona from description: {e}")
            # Return a default persona on error
            return ExtractedPersona(
                name="Unknown",
                role="Unknown",
                risk_tolerance="moderate",
                information_bias="balanced",
                decision_speed="moderate",
                authority_level=5,
                coalition_tendencies=0.5,
                incentive_structure=["operational"],
                behavioral_axioms=["Pragmatic decision-maker"],
                extraction_confidence=0.0,
            )

    # ---- Role-to-authority heuristic ----

    _ROLE_AUTHORITY_MAP: dict[str, int] = {
        "ceo": 10,
        "chief executive": 10,
        "president": 10,
        "cfo": 9,
        "coo": 9,
        "cto": 9,
        "cro": 9,
        "cmo": 9,
        "chief": 9,
        "evp": 8,
        "executive vice president": 8,
        "svp": 8,
        "senior vice president": 8,
        "general manager": 8,
        "managing director": 8,
        "vp": 7,
        "vice president": 7,
        "head of": 7,
        "director": 6,
        "senior director": 7,
        "manager": 5,
        "senior manager": 6,
        "lead": 5,
        "analyst": 4,
        "associate": 3,
    }

    @staticmethod
    def _infer_authority_from_role(role: str) -> int:
        """Infer authority level (1-10) from a job title/role string."""
        role_lower = role.lower()
        for keyword, level in InterviewExtractor._ROLE_AUTHORITY_MAP.items():
            if keyword in role_lower:
                return level
        return 5  # default mid-level

    @staticmethod
    def _parse_coalition_tendencies(description: str) -> float:
        """Parse a coalition tendencies description to a 0.0-1.0 float."""
        desc_lower = description.lower() if description else ""
        keyword_scores: dict[str, float] = {
            "rarely": 0.2,
            "seldom": 0.2,
            "avoids": 0.2,
            "independent": 0.2,
            "lone": 0.2,
            "sometimes": 0.5,
            "occasional": 0.5,
            "moderate": 0.5,
            "when needed": 0.5,
            "frequently": 0.8,
            "often": 0.8,
            "regularly": 0.8,
            "always": 0.9,
            "strong": 0.8,
            "extensive": 0.8,
            "active": 0.7,
            "collaborative": 0.7,
            "coalition": 0.7,
            "alliance": 0.7,
        }
        for keyword, score in keyword_scores.items():
            if keyword in desc_lower:
                return score
        return 0.5  # default moderate

    @staticmethod
    def _derive_incentive_structure(
        role: str, known_priorities: list[str]
    ) -> list[str]:
        """Derive incentive structure from role and known priorities."""
        incentives: list[str] = []
        role_lower = role.lower()
        priorities_text = " ".join(known_priorities).lower()

        if any(k in role_lower for k in ("cfo", "finance", "investor", "treasurer")):
            incentives.append("financial")
        if any(k in role_lower for k in ("ceo", "president", "founder", "board")):
            incentives.extend(["reputational", "financial"])
        if any(k in role_lower for k in ("coo", "operations", "supply", "logistics")):
            incentives.append("operational")
        if any(k in role_lower for k in ("compliance", "legal", "regulatory", "counsel")):
            incentives.append("regulatory")

        if "growth" in priorities_text or "revenue" in priorities_text:
            incentives.append("financial")
        if "brand" in priorities_text or "reputation" in priorities_text:
            incentives.append("reputational")
        if "efficiency" in priorities_text or "cost" in priorities_text:
            incentives.append("operational")
        if "compliance" in priorities_text or "regulation" in priorities_text:
            incentives.append("regulatory")

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique: list[str] = []
        for item in incentives:
            if item not in seen:
                seen.add(item)
                unique.append(item)

        return unique if unique else ["operational"]

    @staticmethod
    def _derive_behavioral_axioms(
        notable_decisions: list[str], public_statements: list[str]
    ) -> list[str]:
        """Derive behavioral axioms from notable decisions and public statements."""
        axioms: list[str] = []

        for decision in notable_decisions[:2]:
            if decision:
                axioms.append(f"Decision pattern: {decision}")

        for statement in public_statements[:2]:
            if statement:
                axioms.append(f"Stated principle: {statement}")

        return axioms if axioms else ["Pragmatic decision-maker"]

    async def research_persona(
        self, name: str, company: str = "", role: str = ""
    ) -> ExtractedPersona:
        """Extract persona attributes by researching an executive's public profile.

        Uses the autoresearch service to gather public data about the executive
        and maps the synthesis to ExtractedPersona fields. Falls back to
        extract_from_description() if research fails.

        Args:
            name: Executive's full name
            company: Company name (optional, improves research accuracy)
            role: Job title / role (optional, used for authority inference)

        Returns:
            ExtractedPersona with research-derived attributes
        """
        try:
            result = await research_service.research_executive(
                name, company=company, role=role
            )
            synthesis = result.get("synthesis", {})

            if not synthesis or not isinstance(synthesis, dict):
                raise ValueError("Empty or invalid synthesis returned from research")

            resolved_role = synthesis.get("role", role) or role or "Unknown"

            return ExtractedPersona(
                name=synthesis.get("name", name) or name,
                role=resolved_role,
                risk_tolerance=synthesis.get("risk_tolerance", "moderate"),
                information_bias=synthesis.get("information_bias", "balanced"),
                decision_speed=synthesis.get("decision_speed", "moderate"),
                authority_level=self._infer_authority_from_role(resolved_role),
                coalition_tendencies=self._parse_coalition_tendencies(
                    synthesis.get("coalition_tendencies", "")
                ),
                incentive_structure=self._derive_incentive_structure(
                    resolved_role,
                    synthesis.get("known_priorities", []),
                ),
                behavioral_axioms=self._derive_behavioral_axioms(
                    synthesis.get("notable_decisions", []),
                    synthesis.get("public_statements", []),
                ),
                extraction_confidence=0.6,
            )

        except Exception as e:
            logger.error(f"Research-based persona extraction failed for {name}: {e}")
            # Fall back to description-based extraction
            fallback_description = (
                f"{name} is a {role or 'professional'}"
                f"{' at ' + company if company else ''}. "
                "No further details are available."
            )
            return await self.extract_from_description(fallback_description)

    def get_interview_protocol(self) -> InterviewProtocol:
        """Return the standard interview question set.

        Returns:
            InterviewProtocol with all standard questions
        """
        questions = [
            InterviewQuestion(
                question=q["question"],
                attribute_target=q["attribute_target"],
                follow_up=q.get("follow_up"),
            )
            for q in self.STANDARD_PROTOCOL
        ]
        return InterviewProtocol(questions=questions)
