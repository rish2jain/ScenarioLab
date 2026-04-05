"""ReportAgent for generating consulting-grade reports from simulations."""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Literal, cast

from app.llm.provider import LLMMessage, LLMProvider
from app.reports.deliverables import (
    calculate_influence_scores,
    calculate_probability_ranges,
    compute_support_levels,
    construct_scenario_narratives,
    extract_key_findings,
    extract_risk_signals,
    format_for_presentation,
    get_outcome_dimensions,
    identify_decision_branches,
    identify_key_concerns,
    identify_risk_owner,
    score_risk_impact,
    score_risk_probability,
)
from app.reports.llm_json_fences import strip_llm_json_fences
from app.reports.models import (
    ExecutiveSummary,
    KeyRecommendation,
    ObjectiveAssessment,
    ReportMemoryByAgent,
    ReportMemoryToolContext,
    ReportRoundAuditEntry,
    ReportToolContext,
    ReportToolContextAgent,
    ReportToolContextLastMessage,
    ReportToolContextSummary,
    RiskItem,
    RiskRegister,
    ScenarioMatrix,
    ScenarioOutcome,
    SimulationReport,
    StakeholderHeatmap,
    StakeholderPosition,
)
from app.simulation.models import SimulationState
from app.simulation.objectives import format_simulation_objective_for_prompt

logger = logging.getLogger(__name__)

_VALID_IMPACT_LABELS = frozenset({"low", "medium", "high", "critical"})


def _coerce_int_score_1_5(value: object) -> int | None:
    """Parse a 1–5 integer from LLM JSON; return None if missing or invalid."""
    if value is None:
        return None
    try:
        v = int(round(float(value)))
    except (TypeError, ValueError):
        return None
    if 1 <= v <= 5:
        return v
    return None


def _impact_label_to_default_score(impact: str) -> int:
    """Map categorical impact to a default 1–5 impact score when LLM omits impact_score."""
    return {
        "low": 2,
        "medium": 3,
        "high": 4,
        "critical": 5,
    }.get(impact.strip().lower(), 3)


def _probability_to_likelihood_score(probability: float) -> int:
    """Map 0.0–1.0 probability to 1–5 when likelihood_score is absent."""
    p = max(0.0, min(1.0, float(probability)))
    return max(1, min(5, round(p * 4) + 1))


def _normalize_impact_label(
    raw: object,
) -> Literal["low", "medium", "high", "critical"]:
    s = str(raw or "medium").strip().lower()
    if s in _VALID_IMPACT_LABELS:
        return cast(Literal["low", "medium", "high", "critical"], s)
    return "medium"


class ReportAgent:
    """Generates consulting-grade reports from simulation results."""

    # Shared system message for all JSON-producing LLM calls — avoids
    # duplicating near-identical instructions across every section prompt.
    _SYSTEM_JSON = "You are an expert strategy consultant. " "Respond with valid JSON only."

    # Section-specific system messages that provide richer expertise context.
    # Falls back to _SYSTEM_JSON if a section key is missing.
    _SYSTEM_MESSAGES: dict[str, str] = {
        "executive_summary": (
            "You are a McKinsey-level strategy consultant writing for C-suite "
            "executives. Ground every claim in simulation evidence — cite agent "
            "names and round numbers. Respond with valid JSON only."
        ),
        "objective_assessment": (
            "You are a senior strategy evaluator assessing whether a war-game "
            "simulation answered its stated objective. Use specific evidence "
            "from the transcript to justify every judgement. Respond with valid "
            "JSON only."
        ),
        "risk_register": (
            "You are a risk management expert identifying actionable risks "
            "from simulation dynamics. Every risk must trace to specific "
            "simulation evidence. Respond with valid JSON only."
        ),
        "scenario_matrix": (
            "You are a scenario planning strategist developing forward-looking "
            "scenarios grounded in observed simulation dynamics. Each scenario "
            "must reference the decision branches and agent behaviors that "
            "make it plausible. Respond with valid JSON only."
        ),
        "stakeholder_heatmap": (
            "You are a stakeholder analysis expert mapping influence and "
            "alignment dynamics. Base every assessment on observed agent "
            "behavior, stated positions, and coalition patterns from the "
            "simulation transcript. Respond with valid JSON only."
        ),
    }

    @classmethod
    def _system_message_for(cls, section: str) -> str:
        """Return the section-specific system message, falling back to the generic one."""
        return cls._SYSTEM_MESSAGES.get(section, cls._SYSTEM_JSON)

    def __init__(
        self,
        llm_provider: LLMProvider,
        simulation_state: SimulationState,
    ):
        self.llm = llm_provider
        self.simulation = simulation_state
        # Lazily built once per report and shared across all sections.
        self._shared_context: str | None = None
        self._shared_all_messages: list | None = None

    def _get_context(self) -> str:
        """Return simulation context, building it once and caching."""
        if self._shared_context is None:
            self._shared_context = self._build_simulation_context()
        return self._shared_context

    def _get_all_messages(self) -> list:
        """Get all messages from all rounds (cached)."""
        if self._shared_all_messages is None:
            messages = []
            for round_state in self.simulation.rounds:
                messages.extend(round_state.messages)
            self._shared_all_messages = messages
        return self._shared_all_messages

    async def generate_full_report(self) -> SimulationReport:
        """Generate complete report with all deliverables."""
        logger.info(f"Starting report generation for sim {self.simulation.config.id}")

        # Create base report
        report = SimulationReport(
            simulation_id=self.simulation.config.id,
            simulation_name=self.simulation.config.name,
            status="generating",
        )

        # Pre-build shared context once so every section reuses it.
        self._get_context()
        self._get_all_messages()

        try:
            # Generate all sections in parallel for speed
            (
                report.objective_assessment,
                report.executive_summary,
                report.risk_register,
                report.scenario_matrix,
                report.stakeholder_heatmap,
                mem_ctx,
            ) = await asyncio.gather(
                self.generate_objective_assessment(),
                self.generate_executive_summary(),
                self.generate_risk_register(),
                self.generate_scenario_matrix(),
                self.generate_stakeholder_heatmap(),
                self._memory_tool_context(),
            )
            report.tool_context = ReportToolContext(
                summary=self.collect_tool_context(),
                round_audit=self.tool_audit_round_summary(),
                memory=mem_ctx,
            )
            report.status = "draft"

            report.updated_at = datetime.now(timezone.utc).isoformat()

            logger.info(f"Report done for {report.simulation_id}")

        except Exception as e:
            logger.error(f"Error generating report: {e}")
            report.status = "draft"  # Still return partial report

        return report

    def _objective_block_for_report(self) -> str:
        """Objective text for prompts (description + parsed objective)."""
        return format_simulation_objective_for_prompt(
            self.simulation.config.description,
            self.simulation.config.parameters,
        )

    async def generate_objective_assessment(self) -> ObjectiveAssessment:
        """Assess whether the simulation addressed the user's stated objective."""
        objective_block = self._objective_block_for_report()
        oid = self.simulation.config.id
        if not objective_block.strip():
            return ObjectiveAssessment(
                simulation_id=oid,
                stated_objective="",
                conclusion=("No explicit simulation objective was configured; " "assessment is not applicable."),
            )

        # Tiered transcript: recent rounds get full text, older rounds
        # get shorter excerpts to prioritise signal-dense recent discussion
        # while staying within a reasonable context budget.
        all_msgs = self._get_all_messages()
        total_rounds = len(self.simulation.rounds)
        recent_cutoff = max(1, total_rounds - 3)  # last 3 rounds = "recent"
        transcript_lines: list[str] = []
        for m in all_msgs:
            limit = 600 if m.round_number >= recent_cutoff else 150
            excerpt = m.content[:limit]
            if len(m.content) > limit:
                excerpt += "..."
            transcript_lines.append(f"[R{m.round_number}] {m.agent_name} ({m.agent_role}): " f"{excerpt}")
        transcript = "\n".join(transcript_lines)

        prompt = f"""You are evaluating whether this war-game simulation answered
the user's stated objective.

USER OBJECTIVE AND STRUCTURED PARSE:
{objective_block}

TRANSCRIPT (older rounds summarised, recent rounds full):
{transcript}

EVIDENCE REQUIREMENTS:
- For each entry in "success_metrics_addressed", cite the round number (e.g. R2)
  and the agent name who provided the most relevant evidence.
- For each gap, classify its severity:
  CRITICAL = the objective cannot be answered from this simulation
  SIGNIFICANT = partial answer exists but key questions remain open
  MINOR = mostly answered but nuances or edge cases are missing
- Format each gap as: "[SEVERITY] description — what would be needed to close it"

Respond with valid JSON only:
{{
  "stated_objective": "one-paragraph restatement of what success looks like",
  "success_metrics_addressed": ["metric — evidence from [Agent] in R[N]: brief quote or paraphrase"],
  "gaps": ["[CRITICAL|SIGNIFICANT|MINOR] gap description — what is needed to close it"],
  "conclusion": "2-4 sentences: did we answer the user's question, and what is still missing?"
}}"""

        try:
            response = await self.llm.generate(
                messages=[
                    LLMMessage(role="system", content=self._system_message_for("objective_assessment")),
                    LLMMessage(role="user", content=prompt),
                ],
                temperature=0.15,
                max_tokens=1200,
            )
            content = self._clean_json_response(response.content)
            data = json.loads(content)
            return ObjectiveAssessment(
                simulation_id=oid,
                stated_objective=str(data.get("stated_objective", "")),
                success_metrics_addressed=list(data.get("success_metrics_addressed") or []),
                gaps=list(data.get("gaps") or []),
                conclusion=str(data.get("conclusion", "")),
            )
        except Exception as e:
            logger.error(f"Error generating objective assessment: {e}")
            return ObjectiveAssessment(
                simulation_id=oid,
                stated_objective=objective_block[:500],
                conclusion=(
                    "Objective assessment could not be generated automatically; " f"see stated objective above. ({e})"
                ),
            )

    async def generate_executive_summary(self) -> ExecutiveSummary:
        """Generate executive summary with max 3 key recommendations."""
        logger.info("Generating executive summary")

        # Extract key findings using helper
        findings = extract_key_findings(
            self._get_all_messages(),
            self.simulation.rounds,
            self.simulation.agents,
        )

        # Use pre-built shared context
        context = self._get_context()

        objective_block = self._objective_block_for_report()
        obj_section = ""
        if objective_block.strip():
            obj_section = "\n\nSTATED OBJECTIVE (primary user question):\n"
            obj_section += objective_block

        prompt = f"""You are a senior strategy consultant writing an executive summary.

SIMULATION CONTEXT:
{context}
{obj_section}

KEY FINDINGS (extracted by analysis):
{json.dumps(findings, indent=2)}

TASK:
Write an executive summary (max 1000 words) that:
1. Provides a concise overview of the simulation and its purpose
2. Explicitly relates findings to the stated objective (if one was provided)
3. Highlights the most critical dynamics and outcomes
4. Synthesizes stakeholder positions and key tensions
5. Presents clear strategic implications

GROUNDING REQUIREMENTS:
- Every key finding MUST reference at least one specific agent name and
  quote or paraphrase from the simulation transcript (e.g., "As [Agent]
  noted in Round 3, '...'").
- Each recommendation must specify: WHO should act, WHAT action to take,
  and WHAT SUCCESS looks like (measurable or observable outcome).
- Do NOT use generic phrases like "stakeholders should consider" or
  "further analysis is needed" without specifying which stakeholders
  and what specific analysis.

Respond with valid JSON in this exact format:
{{
    "summary_text": "The executive summary text...",
    "key_findings": ["finding 1", "finding 2", "finding 3"],
    "recommendations": [
        {{
            "title": "Recommendation title",
            "description": "Detailed description with who/what/success criteria",
            "priority": "high|medium|low",
            "rationale": "Why this matters — cite simulation evidence"
        }}
    ]
}}

IMPORTANT: Include at most 3 recommendations, ranked by impact."""

        try:
            response = await self.llm.generate(
                messages=[
                    LLMMessage(role="system", content=self._system_message_for("executive_summary")),
                    LLMMessage(role="user", content=prompt),
                ],
                temperature=0.3,
                max_tokens=2500,
            )

            content = self._clean_json_response(response.content)
            data = json.loads(content)

            # Validate and create recommendations
            recommendations = []
            for rec_data in data.get("recommendations", [])[:3]:
                recommendations.append(KeyRecommendation(**rec_data))

            return ExecutiveSummary(
                simulation_id=self.simulation.config.id,
                summary_text=format_for_presentation(data.get("summary_text", "")),
                key_findings=data.get("key_findings", findings),
                recommendations=recommendations,
            )

        except Exception as e:
            logger.error(f"Error generating executive summary: {e}")
            # Fallback to basic extraction
            return self._generate_fallback_executive_summary(findings)

    async def generate_risk_register(self) -> RiskRegister:
        """Extract risks from simulation dynamics."""
        logger.info("Generating risk register")

        # Extract risk signals using helper
        signals = extract_risk_signals(
            self._get_all_messages(),
            self.simulation.agents,
        )

        if not signals:
            logger.warning("No risk signals detected")
            return RiskRegister(
                simulation_id=self.simulation.config.id,
                items=[],
            )

        # Use pre-built shared context
        context = self._get_context()
        signals_json = json.dumps(signals[:10], indent=2)  # Limit to top 10

        prompt = f"""You are a risk management consultant analyzing a business simulation.

SIMULATION CONTEXT:
{context}

RISK SIGNALS DETECTED:
{signals_json}

TASK:
Based on the detected risk signals, create a structured risk register.

SEVERITY FRAMEWORK:
- Score each risk on two dimensions:
  Impact (1-5): 1=negligible, 2=minor, 3=moderate, 4=major, 5=catastrophic
  Likelihood (1-5): 1=rare, 2=unlikely, 3=possible, 4=likely, 5=almost certain
- Map the combined score to impact level:
  critical (>=20), high (12-19), medium (6-11), low (<=5)

ATTRIBUTION REQUIREMENT:
- Each risk MUST trace to a specific simulation dynamic (e.g., "CFO raised
  cash flow concerns in Round 2" or "Coalition between X and Y formed
  against the proposal in Round 3").
- Trigger conditions must be specific and observable, not vague.

For each risk, provide:
- Clear description with source attribution (agent name + round)
- Probability (0.0-1.0) based on signal strength and repetition
- impact_score (integer 1-5) and likelihood_score (integer 1-5) per the severity framework above
- Impact level (low, medium, high, critical) derived from the two dimensions (must be consistent with scores)
- Risk owner (the specific stakeholder most responsible, by name)
- Mitigation strategy (actionable, with responsible party)
- Trigger condition (specific observable event from simulation dynamics)

Respond with valid JSON in this exact format:
{{
    "risks": [
        {{
            "description": "Risk description citing agent and round",
            "probability": 0.7,
            "impact_score": 4,
            "likelihood_score": 3,
            "impact": "high",
            "owner": "Stakeholder name/role",
            "mitigation": "Specific mitigation with responsible party",
            "trigger": "Specific trigger condition from simulation"
        }}
    ]
}}

Include 3-7 significant risks. Be specific and actionable."""

        try:
            response = await self.llm.generate(
                messages=[
                    LLMMessage(role="system", content=self._system_message_for("risk_register")),
                    LLMMessage(role="user", content=prompt),
                ],
                temperature=0.2,
                max_tokens=2000,
            )

            content = self._clean_json_response(response.content)
            data = json.loads(content)

            # Create risk items
            items = []
            for risk_data in data.get("risks", []):
                prob = float(risk_data.get("probability", 0.5) or 0.0)
                prob = max(0.0, min(1.0, prob))
                impact = _normalize_impact_label(risk_data.get("impact", "medium"))

                parsed_impact_s = _coerce_int_score_1_5(risk_data.get("impact_score"))
                impact_score = (
                    parsed_impact_s if parsed_impact_s is not None else _impact_label_to_default_score(impact)
                )

                parsed_like_s = _coerce_int_score_1_5(risk_data.get("likelihood_score"))
                likelihood_score = (
                    parsed_like_s if parsed_like_s is not None else _probability_to_likelihood_score(prob)
                )

                items.append(
                    RiskItem(
                        description=risk_data.get("description", "Unknown risk"),
                        probability=prob,
                        impact=impact,
                        impact_score=impact_score,
                        likelihood_score=likelihood_score,
                        owner=risk_data.get("owner", "Unassigned"),
                        mitigation=risk_data.get("mitigation", "TBD"),
                        trigger=risk_data.get("trigger", "Unknown"),
                    )
                )

            return RiskRegister(
                simulation_id=self.simulation.config.id,
                items=items,
            )

        except Exception as e:
            logger.error(f"Error generating risk register: {e}")
            return self._generate_fallback_risk_register(signals)

    async def generate_scenario_matrix(self) -> ScenarioMatrix:
        """Generate 3-5 scenarios with outcomes and probabilities."""
        logger.info("Generating scenario matrix")

        # Use helpers to identify branches and construct narratives
        branches = identify_decision_branches(self.simulation.rounds)
        narratives = construct_scenario_narratives(branches, len(self.simulation.rounds))

        # Use pre-built shared context
        context = self._get_context()
        narratives_json = json.dumps(narratives, indent=2)

        # Standard outcome dimensions
        outcome_dimensions = get_outcome_dimensions()

        prompt = f"""You are a scenario planning consultant developing strategic scenarios.

SIMULATION CONTEXT:
{context}

SCENARIO NARRATIVES:
{narratives_json}

OUTCOME DIMENSIONS TO EVALUATE:
{json.dumps(outcome_dimensions, indent=2)}

TASK:
Develop 3-5 detailed scenarios based on the narratives above.
For each scenario:
1. Provide a descriptive name and narrative
2. Estimate probability range (min, max) that must sum to reasonable coverage
3. Identify 2-4 key drivers that shape this scenario
4. Assess outcomes across each dimension (positive/negative description)

GROUNDING REQUIREMENTS:
- Each scenario description MUST reference the specific decision branches
  or agent behaviors from the simulation that make it plausible (e.g.,
  "This scenario follows from the coalition formed in Round 2 between
  [Agent A] and [Agent B] opposing the proposal").
- Key drivers must be traceable to observed simulation dynamics, not
  hypothetical external factors.
- Outcome descriptions must connect back to positions or concerns
  raised by specific agents during the simulation.

Respond with valid JSON in this exact format:
{{
    "scenarios": [
        {{
            "scenario_name": "Name",
            "description": "Detailed scenario narrative citing simulation evidence",
            "probability_range": [0.2, 0.4],
            "confidence_interval": 0.8,
            "key_drivers": ["driver traced to simulation dynamic"],
            "outcomes": {{
                "Financial Performance": "Outcome description citing agent evidence",
                "Market Position": "Outcome description",
                ...
            }}
        }}
    ]
}}

Ensure scenarios are distinct, plausible, and cover a range of outcomes."""

        try:
            response = await self.llm.generate(
                messages=[
                    LLMMessage(role="system", content=self._system_message_for("scenario_matrix")),
                    LLMMessage(role="user", content=prompt),
                ],
                temperature=0.5,
                max_tokens=2500,
            )

            content = self._clean_json_response(response.content)
            data = json.loads(content)

            # Create scenario outcomes
            scenarios = []
            for scen_data in data.get("scenarios", []):
                prob_range = scen_data.get("probability_range", [0.2, 0.4])
                if isinstance(prob_range, list) and len(prob_range) == 2:
                    prob_tuple = (float(prob_range[0]), float(prob_range[1]))
                else:
                    prob_tuple = (0.2, 0.4)

                scenarios.append(
                    ScenarioOutcome(
                        scenario_name=scen_data.get("scenario_name", "Unnamed"),
                        description=scen_data.get("description", ""),
                        probability_range=prob_tuple,
                        confidence_interval=scen_data.get("confidence_interval", 0.7),
                        key_drivers=scen_data.get("key_drivers", []),
                        outcomes=scen_data.get("outcomes", {}),
                    )
                )

            return ScenarioMatrix(
                simulation_id=self.simulation.config.id,
                scenarios=scenarios,
                outcome_dimensions=outcome_dimensions,
            )

        except Exception as e:
            logger.error(f"Error generating scenario matrix: {e}")
            return self._generate_fallback_scenario_matrix(narratives)

    async def generate_stakeholder_heatmap(self) -> StakeholderHeatmap:
        """Map stakeholder positions and influence."""
        logger.info("Generating stakeholder heatmap")

        # Calculate positions and influence for each agent
        stakeholders = []
        messages = self._get_all_messages()

        for agent in self.simulation.agents:
            position, support_level = compute_support_levels(agent, messages, self.simulation.rounds)
            influence = calculate_influence_scores(agent, self.simulation.agents, messages)
            concerns = identify_key_concerns(agent, messages)

            stakeholders.append(
                {
                    "agent": agent,
                    "position": position,
                    "support_level": support_level,
                    "influence": influence,
                    "concerns": concerns,
                }
            )

        # Use pre-built shared context
        context = self._get_context()
        stakeholders_json = json.dumps(
            [
                {
                    "name": s["agent"].name,
                    "role": s["agent"].archetype_id,
                    "position": s["position"],
                    "support_level": s["support_level"],
                    "influence": s["influence"],
                    "concerns": s["concerns"],
                }
                for s in stakeholders
            ],
            indent=2,
        )

        prompt = f"""You are a stakeholder analysis consultant mapping influence dynamics.

SIMULATION CONTEXT:
{context}

STAKEHOLDER DATA:
{stakeholders_json}

TASK:
Analyze the stakeholder positions and refine the assessment.
For each stakeholder, confirm or adjust:
- Position category (strongly_support, support, neutral, oppose,
  strongly_oppose)
- Influence score (0.0-1.0) based on authority and engagement
- Support level (-1.0 to 1.0)
- Key concerns (top 2-3)

EVIDENCE REQUIREMENTS:
- Each position assessment must cite the agent's own statements or voting
  behavior (e.g., "Voted against in Round 3; stated 'we cannot accept
  these terms'").
- Influence scores must reflect observed behavior: did other agents defer
  to them, form coalitions with them, or shift positions after their
  arguments?
- Key concerns must be drawn from the agent's actual statements, not
  inferred from their role title alone.
- If an agent's position shifted during the simulation, note the shift
  and the round where it occurred.

Respond with valid JSON in this exact format:
{{
    "stakeholders": [
        {{
            "stakeholder": "Name",
            "role": "Role/Title",
            "position": "support|neutral|oppose|...",
            "influence": 0.7,
            "support_level": 0.5,
            "key_concerns": ["concern citing agent's own words or actions"]
        }}
    ]
}}

Ensure the analysis reflects the actual dynamics observed in the simulation."""

        try:
            response = await self.llm.generate(
                messages=[
                    LLMMessage(role="system", content=self._system_message_for("stakeholder_heatmap")),
                    LLMMessage(role="user", content=prompt),
                ],
                temperature=0.25,
                max_tokens=2000,
            )

            content = self._clean_json_response(response.content)
            data = json.loads(content)

            # Create stakeholder positions
            positions = []
            for pos_data in data.get("stakeholders", []):
                positions.append(
                    StakeholderPosition(
                        stakeholder=pos_data.get("stakeholder", "Unknown"),
                        role=pos_data.get("role", "Unknown"),
                        position=pos_data.get("position", "neutral"),
                        influence=pos_data.get("influence", 0.5),
                        support_level=pos_data.get("support_level", 0.0),
                        key_concerns=pos_data.get("key_concerns", []),
                    )
                )

            return StakeholderHeatmap(
                simulation_id=self.simulation.config.id,
                stakeholders=positions,
            )

        except Exception as e:
            logger.error(f"Error generating stakeholder heatmap: {e}")
            return self._generate_fallback_stakeholder_heatmap(stakeholders)

    def _build_simulation_context(self) -> str:
        """Build a text summary of the simulation for LLM context."""
        obj = self._objective_block_for_report()
        lines = [
            f"Simulation: {self.simulation.config.name}",
            f"Description: {self.simulation.config.description}",
        ]
        if obj.strip():
            lines.append(f"Objective and parsed fields:\n{obj}")
        lines.extend(
            [
                f"Environment: {self.simulation.config.environment_type.value}",
                f"Total Rounds: {len(self.simulation.rounds)}",
                f"Status: {self.simulation.status.value}",
                "",
                "Agents:",
            ]
        )

        for agent in self.simulation.agents:
            lines.append(f"  - {agent.name} ({agent.archetype_id})")
            if agent.current_stance:
                lines.append(f"    Final Stance: {agent.current_stance}")
            if agent.coalition_members:
                coalitions = ", ".join(agent.coalition_members)
                lines.append(f"    Coalitions: {coalitions}")

        lines.extend(["", "Messages by Round:"])

        # Tiered truncation: recent rounds (last 3) get full excerpts,
        # older rounds get shorter excerpts to fit more signal per token.
        total_rounds = len(self.simulation.rounds)
        recent_cutoff = max(1, total_rounds - 3)

        for round_state in self.simulation.rounds:
            lines.append(f"\nRound {round_state.round_number} " f"({len(round_state.messages)} messages):")
            is_recent = round_state.round_number >= recent_cutoff
            char_limit = 600 if is_recent else 150
            for msg in round_state.messages:
                excerpt = msg.content[:char_limit]
                if len(msg.content) > char_limit:
                    excerpt += "..."
                lines.append(f"  [{msg.agent_name} ({msg.agent_role})] " f"{excerpt}")

            # Include round decisions/votes if present
            for dec in round_state.decisions:
                ev = dec.get("evaluation", {})
                outcome = ev.get("outcome", "")
                if outcome:
                    lines.append(f"  >> Outcome: {outcome}")
                vote = ev.get("vote_result", {})
                if vote:
                    lines.append(
                        f"  >> Vote: {vote.get('result', '?')} "
                        f"(for={vote.get('for', 0)} "
                        f"against={vote.get('against', 0)} "
                        f"abstain={vote.get('abstain', 0)})"
                    )

        return "\n".join(lines)

    def collect_tool_context(self) -> ReportToolContextSummary:
        """Structured slices for interactive report tools and UI drill-down."""
        msgs = self._get_all_messages()
        tail = msgs[-8:] if msgs else []
        return ReportToolContextSummary(
            simulation_id=self.simulation.config.id,
            simulation_name=self.simulation.config.name,
            total_messages=len(msgs),
            rounds_recorded=len(self.simulation.rounds),
            agents=[
                ReportToolContextAgent(
                    id=a.id,
                    name=a.name,
                    archetype=a.archetype_id,
                )
                for a in self.simulation.agents
            ],
            last_messages_preview=[
                ReportToolContextLastMessage.model_validate(
                    {
                        "from": m.agent_name,
                        "phase": getattr(m, "phase", ""),
                        "excerpt": (m.content or "")[:240],
                    }
                )
                for m in tail
            ],
        )

    def tool_audit_round_summary(self) -> list[ReportRoundAuditEntry]:
        """Per-round message counts for audit-style reporting."""
        return [
            ReportRoundAuditEntry.model_validate(
                {
                    "round": rs.round_number,
                    "phase": rs.phase,
                    "messages": len(rs.messages),
                }
            )
            for rs in self.simulation.rounds
        ]

    async def _memory_tool_context(self) -> ReportMemoryToolContext:
        """Recent persisted agent memories for report drill-down (best-effort)."""
        try:
            # Lazy import to avoid circular imports / import-order issues with the db layer.
            from app.db.memories import AgentMemoryRepository

            repo = AgentMemoryRepository()
            sid = self.simulation.config.id
            by_agent: list[ReportMemoryByAgent] = []
            for a in self.simulation.agents[:8]:
                mems = await repo.get_memories(sid, a.id, limit=3)
                if not mems:
                    continue
                by_agent.append(
                    ReportMemoryByAgent(
                        agent_id=a.id,
                        agent_name=a.name,
                        snippets=[(m.get("content") or "")[:300] for m in mems],
                    )
                )
            return ReportMemoryToolContext(by_agent=by_agent)
        except Exception as e:
            logger.debug("memory tool context skipped: %s", e)
            return ReportMemoryToolContext(by_agent=[], skipped=str(e))

    def _clean_json_response(self, content: str) -> str:
        """Clean up LLM response to extract valid JSON (strip markdown fences)."""
        return strip_llm_json_fences(content)

    def _generate_fallback_executive_summary(self, findings: list) -> ExecutiveSummary:
        """Generate a basic executive summary without LLM."""
        summary_text = (
            f"This report summarizes the '{self.simulation.config.name}' "
            f"simulation conducted across {len(self.simulation.rounds)} "
            f"rounds with {len(self.simulation.agents)} participating "
            f"stakeholders.\n\nKey dynamics observed include: "
        )
        summary_text += "; ".join(findings[:3])

        return ExecutiveSummary(
            simulation_id=self.simulation.config.id,
            summary_text=summary_text,
            key_findings=findings,
            recommendations=[
                KeyRecommendation(
                    title="Review Simulation Findings",
                    description="Conduct detailed review of identified dynamics",
                    priority="high",
                    rationale=("Understanding is critical"),
                )
            ],
        )

    def _generate_fallback_risk_register(self, signals: list) -> RiskRegister:
        """Generate a basic risk register without LLM."""
        items = []
        messages = self._get_all_messages()

        for signal in signals[:5]:
            prob = score_risk_probability(signal, messages)
            impact = score_risk_impact(signal.get("content", ""))
            owner = identify_risk_owner(signal, self.simulation.agents)

            impact_label = _normalize_impact_label(impact)
            items.append(
                RiskItem(
                    description=signal.get("content", "Unknown risk")[:100],
                    probability=prob,
                    impact=impact_label,
                    impact_score=_impact_label_to_default_score(impact_label),
                    likelihood_score=_probability_to_likelihood_score(prob),
                    owner=owner,
                    mitigation="Further analysis required",
                    trigger="TBD",
                )
            )

        return RiskRegister(
            simulation_id=self.simulation.config.id,
            items=items,
        )

    def _generate_fallback_scenario_matrix(self, narratives: list) -> ScenarioMatrix:
        """Generate a basic scenario matrix without LLM."""
        scenarios = []
        dimensions = get_outcome_dimensions()

        for narrative in narratives[:4]:
            prob_range = calculate_probability_ranges(narrative, narratives)

            scenarios.append(
                ScenarioOutcome(
                    scenario_name=narrative.get("name", "Unnamed"),
                    description=narrative.get("description", ""),
                    probability_range=prob_range,
                    confidence_interval=0.6,
                    key_drivers=narrative.get("key_decisions", []),
                    outcomes={dim: "TBD" for dim in dimensions},
                )
            )

        return ScenarioMatrix(
            simulation_id=self.simulation.config.id,
            scenarios=scenarios,
            outcome_dimensions=dimensions,
        )

    def _generate_fallback_stakeholder_heatmap(self, stakeholders_data: list) -> StakeholderHeatmap:
        """Generate a basic stakeholder heatmap without LLM."""
        positions = []

        for data in stakeholders_data:
            agent = data["agent"]
            positions.append(
                StakeholderPosition(
                    stakeholder=agent.name,
                    role=agent.archetype_id,
                    position=data["position"],
                    influence=data["influence"],
                    support_level=data["support_level"],
                    key_concerns=data["concerns"],
                )
            )

        return StakeholderHeatmap(
            simulation_id=self.simulation.config.id,
            stakeholders=positions,
        )
