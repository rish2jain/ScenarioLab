"""Ground truth checking for agent statements."""

import logging
import re
import uuid

from pydantic import BaseModel, Field

from app.llm.provider import LLMMessage, LLMProvider

logger = logging.getLogger(__name__)


class HallucinationFlag(BaseModel):
    """A detected hallucination or contradiction."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str
    agent_name: str
    round_number: int
    statement: str
    ground_truth: str
    contradiction_type: str  # "factual", "temporal", "relational", "numerical"
    severity: str  # "major", "minor"
    confidence: float = Field(..., ge=0.0, le=1.0)
    suggested_correction: str


class HallucinationReport(BaseModel):
    """Report of all hallucination flags in a simulation."""

    simulation_id: str
    flags: list[HallucinationFlag]
    detection_rate: float = Field(..., ge=0.0, le=1.0)
    total_statements_checked: int


class HallucinationDetector:
    """Checks agent statements against ground truth."""

    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
        neo4j_client=None,
    ):
        self.llm = llm_provider
        self.db = neo4j_client

    async def check_simulation(
        self,
        simulation_state,
        ground_truth_facts: list[dict] | None = None,
    ) -> HallucinationReport:
        """Check all agent statements against ground truth.

        Args:
            simulation_state: The simulation state with messages
            ground_truth_facts: Optional list of known facts

        Returns:
            HallucinationReport with all detected flags
        """
        flags: list[HallucinationFlag] = []
        total_statements = 0

        if not simulation_state:
            return HallucinationReport(
                simulation_id="",
                flags=[],
                detection_rate=0.0,
                total_statements_checked=0,
            )

        simulation_id = simulation_state.config.id

        # Get facts from seed material / Neo4j if available
        facts = ground_truth_facts or []
        if self.db and simulation_state.config.seed_id:
            try:
                db_facts = await self._extract_facts_from_graph(
                    simulation_state.config.seed_id
                )
                facts.extend(db_facts)
            except Exception as e:
                logger.error(f"Failed to extract facts from graph: {e}")

        # Check each message in each round
        for round_state in simulation_state.rounds:
            for msg in round_state.messages:
                total_statements += 1

                # Skip short messages
                if len(msg.content) < 20:
                    continue

                # Check statement against facts
                flag = await self.check_statement(
                    msg.content, facts, msg.agent_id, msg.agent_name, round_state.round_number
                )
                if flag:
                    flags.append(flag)

        # Calculate detection rate
        detection_rate = (
            len(flags) / total_statements if total_statements > 0 else 0.0
        )

        return HallucinationReport(
            simulation_id=simulation_id,
            flags=flags,
            detection_rate=detection_rate,
            total_statements_checked=total_statements,
        )

    async def _extract_facts_from_graph(self, seed_id: str) -> list[dict]:
        """Extract facts from Neo4j graph for a seed."""
        if not self.db:
            return []

        try:
            # Query for entities and relationships
            query = """
            MATCH (n {seed_id: $seed_id})
            RETURN n.name as name, n.description as description,
                   n.entity_type as type
            """
            results = await self.db.execute_query(query, {"seed_id": seed_id})

            facts = []
            for record in results:
                facts.append({
                    "type": "entity",
                    "name": record.get("name"),
                    "description": record.get("description"),
                    "entity_type": record.get("type"),
                })

            # Query for relationships
            rel_query = """
            MATCH (a {seed_id: $seed_id})-[r]->(b {seed_id: $seed_id})
            RETURN a.name as source, b.name as target,
                   r.relationship_type as rel_type, r.description as description
            """
            rel_results = await self.db.execute_query(
                rel_query, {"seed_id": seed_id}
            )

            for record in rel_results:
                facts.append({
                    "type": "relationship",
                    "source": record.get("source"),
                    "target": record.get("target"),
                    "relationship": record.get("rel_type"),
                    "description": record.get("description"),
                })

            return facts

        except Exception as e:
            logger.error(f"Error extracting facts from graph: {e}")
            return []

    async def check_statement(
        self,
        statement: str,
        facts: list[dict],
        agent_id: str = "",
        agent_name: str = "",
        round_number: int = 0,
    ) -> HallucinationFlag | None:
        """Check a single statement against known facts.

        Args:
            statement: The statement to check
            facts: List of known facts
            agent_id: Optional agent ID
            agent_name: Optional agent name
            round_number: Optional round number

        Returns:
            HallucinationFlag if contradiction found, None otherwise
        """
        if not facts:
            return None

        # Quick numerical check first
        numerical_flag = self._check_numerical_contradiction(statement, facts)
        if numerical_flag:
            return HallucinationFlag(
                agent_id=agent_id,
                agent_name=agent_name,
                round_number=round_number,
                statement=statement,
                ground_truth=numerical_flag["ground_truth"],
                contradiction_type="numerical",
                severity=numerical_flag["severity"],
                confidence=numerical_flag["confidence"],
                suggested_correction=numerical_flag["correction"],
            )

        # Use LLM for semantic fact-checking if available
        if self.llm and len(statement) > 30:
            try:
                semantic_flag = await self._check_semantic_contradiction(
                    statement, facts
                )
                if semantic_flag:
                    return HallucinationFlag(
                        agent_id=agent_id,
                        agent_name=agent_name,
                        round_number=round_number,
                        statement=statement,
                        ground_truth=semantic_flag["ground_truth"],
                        contradiction_type=semantic_flag["type"],
                        severity=semantic_flag["severity"],
                        confidence=semantic_flag["confidence"],
                        suggested_correction=semantic_flag["correction"],
                    )
            except Exception as e:
                logger.error(f"Error in semantic checking: {e}")

        return None

    def _check_numerical_contradiction(
        self, statement: str, facts: list[dict]
    ) -> dict | None:
        """Check for numerical contradictions with 10% tolerance."""
        # Extract numbers from statement
        numbers_in_statement = re.findall(r"\d+(?:\.\d+)?", statement)

        if not numbers_in_statement:
            return None

        # Check against numerical facts
        for fact in facts:
            fact_desc = fact.get("description", "")
            fact_name = fact.get("name", "")

            # Look for numbers in fact
            numbers_in_fact = re.findall(r"\d+(?:\.\d+)?", fact_desc)
            numbers_in_fact.extend(re.findall(r"\d+(?:\.\d+)?", fact_name))

            for stmt_num_str in numbers_in_statement:
                try:
                    stmt_num = float(stmt_num_str)

                    for fact_num_str in numbers_in_fact:
                        try:
                            fact_num = float(fact_num_str)

                            # Check if numbers refer to same thing (context match)
                            if self._numbers_refer_to_same_entity(
                                stmt_num, fact_num, statement, fact_desc
                            ):
                                # Check 10% tolerance
                                diff_ratio = abs(stmt_num - fact_num) / fact_num
                                if diff_ratio > 0.10:
                                    severity = (
                                        "major" if diff_ratio > 0.25 else "minor"
                                    )
                                    return {
                                        "ground_truth": f"{fact_num}",
                                        "severity": severity,
                                        "confidence": min(0.9, 0.7 + diff_ratio),
                                        "correction": f"Should be {fact_num} (not {stmt_num})",
                                    }
                        except ValueError:
                            continue
                except ValueError:
                    continue

        return None

    def _numbers_refer_to_same_entity(
        self,
        stmt_num: float,
        fact_num: float,
        statement: str,
        fact_desc: str,
    ) -> bool:
        """Check if numbers in statement and fact refer to same entity."""
        # Simple heuristic: check if the numbers are in similar contexts
        # Extract surrounding words
        stmt_lower = statement.lower()
        fact_lower = fact_desc.lower()

        # Common quantity keywords
        quantity_keywords = [
            "revenue", "profit", "cost", "price", "market", "share",
            "employees", "customers", "users", "growth", "percent",
            "million", "billion", "thousand",
        ]

        # Check if any keyword appears near both numbers
        for keyword in quantity_keywords:
            if keyword in stmt_lower and keyword in fact_lower:
                return True

        # Check if numbers are in same order of magnitude
        if stmt_num > 0 and fact_num > 0:
            magnitude_diff = abs(stmt_num - fact_num) / max(stmt_num, fact_num)
            if magnitude_diff < 0.5:  # Within 50% suggests same entity
                return True

        return False

    async def _check_semantic_contradiction(
        self, statement: str, facts: list[dict]
    ) -> dict | None:
        """Use LLM to check for semantic contradictions."""
        # Prepare facts context
        facts_text = "\n".join([
            f"- {fact.get('name', '')}: {fact.get('description', '')}"
            for fact in facts[:10]  # Limit to first 10 facts
        ])

        prompt = f"""Check if the following statement contradicts any of the known facts.

KNOWN FACTS:
{facts_text}

STATEMENT TO CHECK:
"{statement}"

Analyze and respond in this JSON format:
{{
    "contradiction_found": true/false,
    "type": "factual|temporal|relational|numerical",
    "ground_truth": "What the facts actually say",
    "severity": "major|minor",
    "confidence": 0.0-1.0,
    "correction": "Suggested correction"
}}

Respond with valid JSON only."""

        response = await self.llm.generate(
            messages=[
                LLMMessage(
                    role="system",
                    content=(
                        "You check statements for contradictions against known facts. "
                        "Respond with valid JSON only."
                    ),
                ),
                LLMMessage(role="user", content=prompt),
            ],
            temperature=0.3,
            max_tokens=400,
        )

        try:
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

            result = json.loads(content)

            if result.get("contradiction_found", False):
                return {
                    "type": result.get("type", "factual"),
                    "ground_truth": result.get("ground_truth", ""),
                    "severity": result.get("severity", "minor"),
                    "confidence": result.get("confidence", 0.5),
                    "correction": result.get("correction", ""),
                }

        except Exception as e:
            logger.error(f"Failed to parse semantic check result: {e}")

        return None
