"""Data models for report generation deliverables."""

import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class RiskItem(BaseModel):
    """A single risk item in the risk register."""

    risk_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str
    probability: float = Field(ge=0.0, le=1.0)
    impact: Literal["low", "medium", "high", "critical"]
    # 1–5 ordinal scores (align with LLM severity framework); optional for older payloads.
    impact_score: int = Field(default=3, ge=1, le=5)
    likelihood_score: int = Field(default=3, ge=1, le=5)
    owner: str  # Agent/role responsible
    mitigation: str
    trigger: str  # What would trigger this risk


class RiskRegister(BaseModel):
    """Complete risk register for a simulation."""

    simulation_id: str
    items: list[RiskItem]
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ScenarioOutcome(BaseModel):
    """A single scenario outcome in the scenario matrix."""

    scenario_name: str
    description: str
    probability_range: tuple[float, float]  # e.g., (0.3, 0.5)
    confidence_interval: float
    key_drivers: list[str]
    outcomes: dict[str, str]  # outcome_dimension -> outcome_description


class ScenarioMatrix(BaseModel):
    """Scenario matrix with multiple possible futures."""

    simulation_id: str
    scenarios: list[ScenarioOutcome]  # 3-5 scenarios
    outcome_dimensions: list[str]  # 4-6 dimensions
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class StakeholderPosition(BaseModel):
    """Position of a stakeholder in the heatmap."""

    stakeholder: str
    role: str
    position: Literal["strongly_support", "support", "neutral", "oppose", "strongly_oppose"]
    influence: float = Field(ge=0.0, le=1.0)
    support_level: float = Field(ge=-1.0, le=1.0)
    key_concerns: list[str]


class StakeholderHeatmap(BaseModel):
    """Heatmap of stakeholder positions and influence."""

    simulation_id: str
    stakeholders: list[StakeholderPosition]
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class KeyRecommendation(BaseModel):
    """A key recommendation in the executive summary."""

    title: str
    description: str
    priority: Literal["high", "medium", "low"]
    rationale: str


class ExecutiveSummary(BaseModel):
    """Executive summary of the simulation."""

    simulation_id: str
    summary_text: str  # Max 2 pages worth of text
    key_findings: list[str]
    recommendations: list[KeyRecommendation]  # Max 3
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ObjectiveAssessment(BaseModel):
    """Evaluation of simulation outcomes against the stated objective."""

    simulation_id: str
    stated_objective: str = ""
    success_metrics_addressed: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    conclusion: str = ""
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ReviewCheckpoint(BaseModel):
    """A review checkpoint for the report."""

    checkpoint_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    stage: Literal["draft", "risk_review", "scenario_review", "final"]
    status: Literal["pending", "approved", "revision_requested"]
    reviewer_notes: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ReportToolContextAgent(BaseModel):
    """Agent row embedded in ReportToolContextSummary.agents."""

    id: str
    name: str
    archetype: str


class ReportToolContextLastMessage(BaseModel):
    """Short preview line for a single message (tail of transcript)."""

    model_config = ConfigDict(populate_by_name=True)

    from_: str = Field(alias="from")
    phase: str
    excerpt: str


class ReportToolContextSummary(BaseModel):
    """Simulation slice for interactive report tools (counts, roster, preview)."""

    simulation_id: str
    simulation_name: str
    total_messages: int
    rounds_recorded: int
    agents: list[ReportToolContextAgent]
    last_messages_preview: list[ReportToolContextLastMessage]


class ReportRoundAuditEntry(BaseModel):
    """One row in the per-round message audit (phase + message count)."""

    model_config = ConfigDict(populate_by_name=True)

    round_number: int = Field(alias="round")
    phase: str
    messages: int


class ReportMemoryByAgent(BaseModel):
    """Recent memory snippets for one agent (report drill-down)."""

    agent_id: str
    agent_name: str
    snippets: list[str]


class ReportMemoryToolContext(BaseModel):
    """Recent persisted agent memories for report drill-down (best-effort)."""

    by_agent: list[ReportMemoryByAgent] = Field(default_factory=list)
    skipped: str | None = None


class ReportToolContext(BaseModel):
    """Structured context for interactive report tools and UI drill-down.

    Populated by ReportAgent after deliverables: ``summary`` holds simulation
    metadata and transcript tail, ``round_audit`` lists per-round message counts,
    and ``memory`` holds optional persisted agent-memory snippets (or a
    ``skipped`` reason if loading failed).
    """

    summary: ReportToolContextSummary | None = None
    round_audit: list[ReportRoundAuditEntry] | None = None
    memory: ReportMemoryToolContext | None = None


class SimulationReport(BaseModel):
    """Complete simulation report with all deliverables."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    simulation_id: str
    simulation_name: str
    objective_assessment: ObjectiveAssessment | None = None
    executive_summary: ExecutiveSummary | None = None
    risk_register: RiskRegister | None = None
    scenario_matrix: ScenarioMatrix | None = None
    stakeholder_heatmap: StakeholderHeatmap | None = None
    checkpoints: list[ReviewCheckpoint] = []
    tool_context: ReportToolContext = Field(
        default_factory=ReportToolContext,
        description=(
            "Interactive drill-down context: summary (metadata + transcript tail), "
            "round_audit (per-round counts), memory (persisted snippets or skipped)."
        ),
    )
    status: Literal["generating", "draft", "in_review", "final"] = "generating"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @field_serializer("tool_context")
    def _serialize_tool_context(self, ctx: ReportToolContext) -> dict[str, Any]:
        """Omit null sub-keys so an uninitialized context stays ``{}`` like before."""
        return ctx.model_dump(
            exclude_none=True,
            mode="json",
            by_alias=True,
        )

    def model_post_init(self, __context: Any) -> None:
        """Ensure updated_at is set."""
        if not self.updated_at:
            self.updated_at = datetime.now(timezone.utc).isoformat()
