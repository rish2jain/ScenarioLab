"""Structured interview protocol for persona extraction."""

import logging
import uuid

from pydantic import BaseModel, Field

from app.llm.provider import LLMMessage, LLMProvider

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
