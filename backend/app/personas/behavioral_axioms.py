"""Behavioral axiom extraction from historical data."""

import json
import logging
import re
import uuid
from collections import Counter

from pydantic import BaseModel, Field

from app.llm.provider import LLMMessage, LLMProvider

logger = logging.getLogger(__name__)


class BehavioralAxiom(BaseModel):
    """A single behavioral axiom extracted from historical data."""

    axiom_id: str = Field(
        default_factory=lambda: str(uuid.uuid4())
    )
    role: str
    axiom_text: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence_count: int
    source_references: list[str] = []


class AxiomExtractionResult(BaseModel):
    """Result of axiom extraction from historical data."""

    data_type: str
    axioms: list[BehavioralAxiom]
    overall_confidence: float = Field(..., ge=0.0, le=1.0)
    data_points_analyzed: int


class AxiomValidationResult(BaseModel):
    """Result of validating axioms against holdout data."""

    total_axioms: int
    validated_axioms: int
    failed_axioms: int
    accuracy_score: float
    validation_details: list[dict] = []


class AxiomExtractor:
    """Extract behavioral axioms from historical text data.

    Analyzes board minutes, earnings calls, war game outputs,
    and other historical text to identify recurring behavioral
    patterns for specific roles.
    """

    DATA_TYPES = {
        "board_minutes": "Board meeting minutes and transcripts",
        "earnings_calls": "Earnings call transcripts",
        "war_game_outputs": "Previous war game simulation outputs",
        "interview_transcripts": "Executive interview transcripts",
        "news_articles": "Business news and press coverage",
        "regulatory_filings": "SEC filings and regulatory documents",
    }

    # Common role patterns to look for
    ROLE_PATTERNS = {
        "CEO": ["ceo", "chief executive", "president"],
        "CFO": ["cfo", "chief financial", "finance chief"],
        "CRO": ["cro", "chief risk", "risk officer"],
        "General Counsel": ["general counsel", "chief legal", "legal officer"],
        "Board Member": ["director", "board member", "board"],
        "Activist Investor": ["activist", "hedge fund", "investor"],
        "Regulator": ["regulator", "regulatory", "commissioner"],
        "Operations Head": ["coo", "chief operating", "operations"],
    }

    def __init__(self, llm_provider: LLMProvider | None = None):
        self.llm = llm_provider

    async def extract_axioms(
        self,
        historical_data: str,
        data_type: str = "board_minutes",
    ) -> AxiomExtractionResult:
        """Extract behavioral axioms from historical text.

        Args:
            historical_data: The historical text to analyze
            data_type: Type of data (board_minutes, earnings_calls, etc.)

        Returns:
            AxiomExtractionResult with extracted axioms
        """
        if not self.llm:
            raise ValueError("LLM provider required for axiom extraction")

        data_type_desc = self.DATA_TYPES.get(
            data_type, "historical documents"
        )

        logger.info(
            f"Extracting axioms from {data_type} "
            f"({len(historical_data)} chars)"
        )

        # Truncate if too long
        max_chars = 8000
        data_sample = historical_data[:max_chars]

        # Use LLM to extract axioms
        axioms = await self._llm_extract_axioms(
            data_sample, data_type, data_type_desc
        )

        # Compute overall confidence
        if axioms:
            overall_confidence = sum(
                a.confidence for a in axioms
            ) / len(axioms)
        else:
            overall_confidence = 0.0

        return AxiomExtractionResult(
            data_type=data_type,
            axioms=axioms,
            overall_confidence=round(overall_confidence, 3),
            data_points_analyzed=len(data_sample),
        )

    async def _llm_extract_axioms(
        self,
        data: str,
        data_type: str,
        data_type_desc: str,
    ) -> list[BehavioralAxiom]:
        """Use LLM to extract axioms from data."""
        prompt = f"""Analyze the following {data_type_desc} and extract
behavioral axioms for each role/person mentioned.

DATA ({data_type}):
{data}

For each role/person identified, extract behavioral axioms in this format:
{{
    "extractions": [
        {{
            "role": "role name",
            "axioms": [
                {{
                    "axiom": "behavioral pattern description",
                    "frequency": "always/often/sometimes",
                    "evidence": ["quote 1", "quote 2"]
                }}
            ]
        }}
    ]
}}

Focus on:
- Decision-making patterns (how they make choices)
- Risk preferences (conservative/aggressive/moderate)
- Communication style (formal/informal, data-driven/intuition)
- Coalition behavior (who they align with)
- Voting patterns (if applicable)

Respond with valid JSON only."""

        try:
            response = await self.llm.generate(
                messages=[
                    LLMMessage(
                        role="system",
                        content=(
                            "You are a behavioral analyst who extracts "
                            "patterns from corporate documents. Respond "
                            "with valid JSON only."
                        ),
                    ),
                    LLMMessage(role="user", content=prompt),
                ],
                temperature=0.3,
                max_tokens=2000,
            )

            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            result = json.loads(content)
            return self._parse_extractions(result)

        except Exception as e:
            logger.error(f"Failed to extract axioms: {e}")
            return self._heuristic_extraction(data)

    def _parse_extractions(
        self,
        result: dict,
    ) -> list[BehavioralAxiom]:
        """Parse LLM extraction result into BehavioralAxiom objects."""
        axioms = []

        extractions = result.get("extractions", [])
        for extraction in extractions:
            role = extraction.get("role", "Unknown")
            role_axioms = extraction.get("axioms", [])

            for axiom_data in role_axioms:
                axiom_text = axiom_data.get("axiom", "")
                frequency = axiom_data.get("frequency", "sometimes")
                evidence = axiom_data.get("evidence", [])

                # Map frequency to confidence
                freq_confidence = {
                    "always": 0.9,
                    "often": 0.7,
                    "sometimes": 0.5,
                    "rarely": 0.3,
                }
                confidence = freq_confidence.get(frequency, 0.5)

                # Adjust confidence by evidence count
                evidence_count = len(evidence)
                if evidence_count >= 3:
                    confidence = min(confidence + 0.1, 1.0)
                elif evidence_count == 0:
                    confidence = max(confidence - 0.2, 0.1)

                axioms.append(BehavioralAxiom(
                    role=role,
                    axiom_text=axiom_text,
                    confidence=round(confidence, 2),
                    evidence_count=evidence_count,
                    source_references=evidence[:3],
                ))

        return axioms

    def _heuristic_extraction(
        self,
        data: str,
    ) -> list[BehavioralAxiom]:
        """Fallback heuristic extraction when LLM fails."""
        axioms = []
        data_lower = data.lower()

        # Find role mentions
        for role, patterns in self.ROLE_PATTERNS.items():
            role_count = sum(
                data_lower.count(p) for p in patterns
            )

            if role_count >= 2:
                # Extract basic patterns
                sentences = re.split(r'[.!?]+', data)

                role_sentences = [
                    s for s in sentences
                    if any(p in s.lower() for p in patterns)
                ]

                if role_sentences:
                    # Look for decision patterns
                    decision_words = [
                        "decided", "approved", "rejected",
                        "voted", "supported", "opposed",
                    ]
                    decision_count = sum(
                        1 for s in role_sentences
                        if any(w in s.lower() for w in decision_words)
                    )

                    if decision_count > 0:
                        axioms.append(BehavioralAxiom(
                            role=role,
                            axiom_text=(
                                f"Tends to participate in decisions "
                                f"({decision_count} decisions observed)"
                            ),
                            confidence=0.5,
                            evidence_count=decision_count,
                            source_references=role_sentences[:2],
                        ))

        return axioms

    async def validate_axioms(
        self,
        axioms: list[BehavioralAxiom],
        holdout_data: str,
    ) -> AxiomValidationResult:
        """Validate extracted axioms against holdout data.

        Tests whether the extracted axioms hold true in
        previously unseen data.

        Args:
            axioms: List of axioms to validate
            holdout_data: Holdout data for validation

        Returns:
            AxiomValidationResult with accuracy scores
        """
        if not self.llm:
            raise ValueError("LLM provider required for axiom validation")

        if not axioms:
            return AxiomValidationResult(
                total_axioms=0,
                validated_axioms=0,
                failed_axioms=0,
                accuracy_score=1.0,
                validation_details=[],
            )

        logger.info(
            f"Validating {len(axioms)} axioms against "
            f"{len(holdout_data)} chars of holdout data"
        )

        # Truncate holdout data
        max_chars = 6000
        data_sample = holdout_data[:max_chars]

        # Validate each axiom
        validation_details = []
        validated = 0
        failed = 0

        # Batch axioms by role for efficiency
        role_axioms: dict[str, list[BehavioralAxiom]] = {}
        for axiom in axioms:
            if axiom.role not in role_axioms:
                role_axioms[axiom.role] = []
            role_axioms[axiom.role].append(axiom)

        for role, role_axiom_list in role_axioms.items():
            result = await self._validate_role_axioms(
                role, role_axiom_list, data_sample
            )
            validation_details.extend(result)

            for detail in result:
                if detail.get("validated", False):
                    validated += 1
                else:
                    failed += 1

        accuracy = validated / len(axioms) if axioms else 1.0

        return AxiomValidationResult(
            total_axioms=len(axioms),
            validated_axioms=validated,
            failed_axioms=failed,
            accuracy_score=round(accuracy, 3),
            validation_details=validation_details,
        )

    async def _validate_role_axioms(
        self,
        role: str,
        axioms: list[BehavioralAxiom],
        data: str,
    ) -> list[dict]:
        """Validate axioms for a single role."""
        axiom_texts = [a.axiom_text for a in axioms]

        prompt = f"""Validate these behavioral axioms for {role}
against the provided data.

AXIOMS TO VALIDATE:
{json.dumps(axiom_texts, indent=2)}

DATA:
{data[:4000]}

For each axiom, determine if it holds true in this data.
Respond with JSON:
{{
    "validations": [
        {{
            "axiom": "axiom text",
            "validated": true/false,
            "evidence_found": ["quote 1", ...],
            "contradicting_evidence": ["quote 1", ...],
            "confidence": 0.0-1.0
        }}
    ]
}}

Respond with valid JSON only."""

        try:
            response = await self.llm.generate(
                messages=[
                    LLMMessage(
                        role="system",
                        content=(
                            "You validate behavioral patterns against "
                            "text data. Respond with valid JSON only."
                        ),
                    ),
                    LLMMessage(role="user", content=prompt),
                ],
                temperature=0.2,
                max_tokens=1500,
            )

            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            result = json.loads(content)
            return result.get("validations", [])

        except Exception as e:
            logger.error(f"Failed to validate axioms for {role}: {e}")
            return [
                {
                    "axiom": a.axiom_text,
                    "validated": False,
                    "error": str(e),
                }
                for a in axioms
            ]

    def get_axiom_summary(
        self,
        result: AxiomExtractionResult,
    ) -> dict:
        """Get a summary of extracted axioms."""
        role_counts = Counter(a.role for a in result.axioms)

        return {
            "total_axioms": len(result.axioms),
            "roles_identified": len(role_counts),
            "roles": dict(role_counts),
            "average_confidence": result.overall_confidence,
            "high_confidence_axioms": [
                a.axiom_text for a in result.axioms
                if a.confidence >= 0.8
            ],
            "data_type": result.data_type,
            "data_points": result.data_points_analyzed,
        }
