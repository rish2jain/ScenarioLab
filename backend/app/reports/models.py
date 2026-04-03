"""Data models for report generation deliverables."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class RiskItem(BaseModel):
    """A single risk item in the risk register."""

    risk_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str
    probability: float = Field(ge=0.0, le=1.0)
    impact: Literal["low", "medium", "high", "critical"]
    owner: str  # Agent/role responsible
    mitigation: str
    trigger: str  # What would trigger this risk


class RiskRegister(BaseModel):
    """Complete risk register for a simulation."""

    simulation_id: str
    items: list[RiskItem]
    generated_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )


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
    generated_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )


class StakeholderPosition(BaseModel):
    """Position of a stakeholder in the heatmap."""

    stakeholder: str
    role: str
    position: Literal[
        "strongly_support", "support", "neutral", "oppose", "strongly_oppose"
    ]
    influence: float = Field(ge=0.0, le=1.0)
    support_level: float = Field(ge=-1.0, le=1.0)
    key_concerns: list[str]


class StakeholderHeatmap(BaseModel):
    """Heatmap of stakeholder positions and influence."""

    simulation_id: str
    stakeholders: list[StakeholderPosition]
    generated_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )


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
    generated_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )


class ReviewCheckpoint(BaseModel):
    """A review checkpoint for the report."""

    checkpoint_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    stage: Literal["draft", "risk_review", "scenario_review", "final"]
    status: Literal["pending", "approved", "revision_requested"]
    reviewer_notes: str = ""
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )


class SimulationReport(BaseModel):
    """Complete simulation report with all deliverables."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    simulation_id: str
    simulation_name: str
    executive_summary: ExecutiveSummary | None = None
    risk_register: RiskRegister | None = None
    scenario_matrix: ScenarioMatrix | None = None
    stakeholder_heatmap: StakeholderHeatmap | None = None
    checkpoints: list[ReviewCheckpoint] = []
    status: Literal["generating", "draft", "in_review", "final"] = "generating"
    created_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )

    def model_post_init(self, __context):
        """Ensure updated_at is set."""
        if not self.updated_at:
            self.updated_at = datetime.utcnow().isoformat()
