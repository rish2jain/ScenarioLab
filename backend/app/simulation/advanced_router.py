"""FastAPI router for advanced simulation features."""

import json
import logging
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from app.analytics.emergent_patterns import (
    EmergentBehaviorsRegister,
    EmergentPatternDetector,
)
from app.analytics.sensitivity import SensitivityAnalyzer, TornadoChartData
from app.llm.factory import get_llm_provider
from app.personas.archetypes import CONSULTING_ARCHETYPES
from app.personas.interview_extractor import (
    ExtractedPersona,
    InterviewExtractor,
    InterviewProtocol,
)
from app.playbooks.auto_template import AutoTemplater, PlaybookSuggestion
from app.playbooks.copilot import CopilotSuggestions, PlaybookCopilot
from app.reports.narrative import NarrativeGenerator, SimulationNarrative
from app.seed.multilanguage import MultiLanguageProcessor
from app.simulation.assumptions import AssumptionRegister, AssumptionTracker
from app.simulation.branching import (
    ScenarioBranch,
    ScenarioBranchManager,
    ScenarioTree,
)
from app.simulation.engine import simulation_engine
from app.simulation.gamification import (
    GamificationConfig,
    GamificationEngine,
    Leaderboard,
)
from app.simulation.audit_trail import (
    AuditEventType,
    AuditTrail,
    audit_manager,
)
from app.simulation.confidence_decay import (
    ConfidenceDecayModel,
    DecayCurveResult,
    confidence_decay_model,
)
from app.simulation.hallucination import (
    HallucinationDetector,
    HallucinationReport,
)
from app.simulation.regulatory_generator import (
    RegulatoryGeneratorResult,
    RegulatoryScenarioGenerator,
)
from app.simulation.zopa import ZOPAAnalyzer, ZOPAResult
from app.simulation.backtesting import backtesting_engine
from app.simulation.market_intelligence import market_intelligence_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["advanced"])

# Initialize managers
branch_manager = ScenarioBranchManager()
gamification_engine = GamificationEngine()


# Request/Response Models
class WhatIfRequest(BaseModel):
    assumption_id: str
    new_value: str


class SeedAnalysisRequest(BaseModel):
    seed_content: str


class PlaybookSuggestRequest(BaseModel):
    scenario_description: str


class BranchCreateRequest(BaseModel):
    parent_branch_id: str
    name: str
    config_changes: dict
    description: str = ""
    creator: str = ""


class GamificationConfigRequest(BaseModel):
    config: GamificationConfig


class RefineSuggestionsRequest(BaseModel):
    suggestions: dict
    feedback: str


# Emergent Patterns Endpoints
@router.post(
    "/simulations/{simulation_id}/emergent-patterns",
    response_model=EmergentBehaviorsRegister,
)
async def detect_emergent_patterns(simulation_id: str):
    """Detect emergent behavior patterns in a simulation."""
    sim_state = await simulation_engine.get_simulation(simulation_id)
    if not sim_state:
        raise HTTPException(status_code=404, detail="Simulation not found")

    llm = get_llm_provider()
    detector = EmergentPatternDetector(llm_provider=llm)

    archetypes = CONSULTING_ARCHETYPES
    result = await detector.detect_patterns(sim_state, archetypes)
    return result


# Hallucination Detection Endpoints
@router.post(
    "/simulations/{simulation_id}/hallucination-check",
    response_model=HallucinationReport,
)
async def check_hallucinations(simulation_id: str):
    """Run hallucination detection on simulation messages."""
    sim_state = await simulation_engine.get_simulation(simulation_id)
    if not sim_state:
        raise HTTPException(status_code=404, detail="Simulation not found")

    llm = get_llm_provider()
    detector = HallucinationDetector(llm_provider=llm)

    result = await detector.check_simulation(sim_state)
    return result


# Narrative Generation Endpoints
@router.post(
    "/simulations/{simulation_id}/narrative",
    response_model=SimulationNarrative,
)
async def generate_narrative(simulation_id: str):
    """Generate narrative summary of simulation."""
    sim_state = await simulation_engine.get_simulation(simulation_id)
    if not sim_state:
        raise HTTPException(status_code=404, detail="Simulation not found")

    llm = get_llm_provider()
    generator = NarrativeGenerator(llm_provider=llm)

    result = await generator.generate_narrative(sim_state)
    return result


# Assumptions Endpoints
@router.post(
    "/simulations/{simulation_id}/assumptions",
    response_model=AssumptionRegister,
)
async def extract_assumptions(simulation_id: str):
    """Extract assumptions from simulation."""
    sim_state = await simulation_engine.get_simulation(simulation_id)
    if not sim_state:
        raise HTTPException(status_code=404, detail="Simulation not found")

    llm = get_llm_provider()
    tracker = AssumptionTracker(llm_provider=llm)

    result = await tracker.extract_assumptions(
        sim_state.config, sim_state
    )
    return result


@router.post("/assumptions/{assumption_id}/what-if")
async def what_if_analysis(
    assumption_id: str,
    request: WhatIfRequest,
):
    """Perform what-if analysis on an assumption."""
    # Note: This requires the assumption register to be passed in
    # In a real implementation, you'd store and retrieve the register
    llm = get_llm_provider()
    tracker = AssumptionTracker(llm_provider=llm)

    # Create a minimal register for the analysis
    register = AssumptionRegister(
        simulation_id="",
        assumptions=[],
    )

    result = await tracker.what_if_analysis(
        assumption_id, request.new_value, register
    )
    return result


# Persona Interview Extraction Endpoints
@router.post("/personas/extract-interview", response_model=ExtractedPersona)
async def extract_persona_from_interview(interview_responses: str):
    """Extract persona from interview text responses."""
    llm = get_llm_provider()
    extractor = InterviewExtractor(llm_provider=llm)

    result = await extractor.extract_from_text(interview_responses)
    return result


@router.get("/personas/interview-protocol", response_model=InterviewProtocol)
async def get_interview_protocol():
    """Get the standard interview question set."""
    extractor = InterviewExtractor()
    return extractor.get_interview_protocol()


# Seed Analysis Endpoints
@router.post("/seeds/analyze", response_model=CopilotSuggestions)
async def analyze_seed(request: SeedAnalysisRequest):
    """Analyze seed material with Copilot."""
    llm = get_llm_provider()
    copilot = PlaybookCopilot(llm_provider=llm)

    result = await copilot.analyze_seed(request.seed_content)
    return result


@router.post("/seeds/analyze/refine", response_model=CopilotSuggestions)
async def refine_seed_analysis(request: RefineSuggestionsRequest):
    """Refine seed analysis based on feedback."""
    llm = get_llm_provider()
    copilot = PlaybookCopilot(llm_provider=llm)

    # Convert dict back to CopilotSuggestions
    suggestions = CopilotSuggestions(**request.suggestions)
    result = await copilot.refine_with_feedback(suggestions, request.feedback)
    return result


# Playbook Suggestion Endpoints
@router.post("/playbooks/suggest", response_model=list[PlaybookSuggestion])
async def suggest_playbook(request: PlaybookSuggestRequest):
    """Auto-suggest playbook based on scenario description."""
    llm = get_llm_provider()
    templater = AutoTemplater(llm_provider=llm)

    result = await templater.suggest_playbook(request.scenario_description)
    return result


# Vertical Libraries Endpoints
@router.get("/playbooks/verticals")
async def list_verticals():
    """List available vertical libraries."""
    verticals_dir = Path(__file__).parent.parent / "playbooks" / "vertical_libraries"

    verticals = []
    if verticals_dir.exists():
        for json_file in verticals_dir.glob("*.json"):
            try:
                with open(json_file, "r") as f:
                    data = json.load(f)
                verticals.append({
                    "id": data.get("vertical", json_file.stem),
                    "name": data.get("vertical", json_file.stem).replace("_", " ").title(),
                    "scenario_count": len(data.get("scenarios", [])),
                })
            except Exception as e:
                logger.error(f"Failed to load vertical {json_file}: {e}")

    return verticals


@router.get("/playbooks/verticals/{vertical}")
async def get_vertical_scenarios(vertical: str):
    """Get scenarios for a specific vertical."""
    verticals_dir = (
        Path(__file__).parent.parent / "playbooks" / "vertical_libraries"
    ).resolve()
    json_file = (verticals_dir / f"{vertical}.json").resolve()

    # Prevent path traversal — ensure resolved path stays within verticals_dir
    if not str(json_file).startswith(str(verticals_dir)):
        raise HTTPException(
            status_code=400, detail="Invalid vertical identifier"
        )

    if not json_file.exists():
        raise HTTPException(status_code=404, detail="Vertical not found")

    try:
        with open(json_file, "r") as f:
            data = json.load(f)
        return data
    except Exception as e:
        logger.error(f"Failed to load vertical {vertical}: {e}")
        raise HTTPException(status_code=500, detail="Failed to load vertical")


# Branching Endpoints
@router.post("/branches", response_model=ScenarioBranch)
async def create_branch(request: BranchCreateRequest):
    """Create a new scenario branch."""
    try:
        result = await branch_manager.create_branch(
            parent_branch_id=request.parent_branch_id,
            name=request.name,
            config_changes=request.config_changes,
            description=request.description,
            creator=request.creator,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/branches/root", response_model=ScenarioBranch)
async def create_root_branch(
    name: str,
    base_config: dict,
    description: str = "",
    creator: str = "",
):
    """Create a new root branch (new scenario tree)."""
    result = await branch_manager.create_root_branch(
        name=name,
        base_config=base_config,
        description=description,
        creator=creator,
    )
    return result


@router.get("/branches/tree/{root_id}", response_model=ScenarioTree)
async def get_branch_tree(root_id: str):
    """Get the full scenario tree."""
    try:
        result = await branch_manager.get_tree(root_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/branches/{branch_id}/lineage")
async def get_branch_lineage(branch_id: str):
    """Get the lineage (path from root) for a branch."""
    try:
        result = await branch_manager.get_branch_lineage(branch_id)
        return {"lineage": [b.model_dump() for b in result]}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/branches/compare")
async def compare_branches(branch_ids: list[str]):
    """Compare multiple branches side-by-side."""
    try:
        result = await branch_manager.compare_branches(branch_ids)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/branches/{branch_a_id}/diff/{branch_b_id}")
async def diff_branches(branch_a_id: str, branch_b_id: str):
    """Show config differences between two branches."""
    try:
        result = await branch_manager.diff_configs(branch_a_id, branch_b_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# Gamification Endpoints
@router.post("/simulations/{simulation_id}/gamification/configure")
async def configure_gamification(
    simulation_id: str,
    request: GamificationConfigRequest,
):
    """Configure gamification for a simulation."""
    sim_state = await simulation_engine.get_simulation(simulation_id)
    if not sim_state:
        raise HTTPException(status_code=404, detail="Simulation not found")

    # Store config in simulation parameters
    if not sim_state.config.parameters:
        sim_state.config.parameters = {}
    sim_state.config.parameters["gamification"] = request.config.model_dump()

    return {"status": "configured", "simulation_id": simulation_id}


@router.get("/simulations/{simulation_id}/leaderboard", response_model=Leaderboard)
async def get_leaderboard(simulation_id: str):
    """Get current leaderboard for a simulation."""
    sim_state = await simulation_engine.get_simulation(simulation_id)
    if not sim_state:
        raise HTTPException(status_code=404, detail="Simulation not found")

    # Get gamification config from parameters
    gamification_data = sim_state.config.parameters.get("gamification", {})
    config = GamificationConfig(**gamification_data)

    result = await gamification_engine.compute_scores(sim_state, config)
    return result


@router.post("/simulations/{simulation_id}/leaderboard/update")
async def update_leaderboard(simulation_id: str):
    """Update leaderboard after a round."""
    sim_state = await simulation_engine.get_simulation(simulation_id)
    if not sim_state:
        raise HTTPException(status_code=404, detail="Simulation not found")

    # Get current round state
    current_round = None
    if sim_state.rounds:
        current_round = sim_state.rounds[-1]

    # Get gamification config
    gamification_data = sim_state.config.parameters.get("gamification", {})
    config = GamificationConfig(**gamification_data)

    result = await gamification_engine.update_leaderboard(
        simulation_id, current_round, config
    )
    return result


# Multi-language Endpoints
@router.post("/seeds/detect-language")
async def detect_language(text: str):
    """Detect language of text."""
    llm = get_llm_provider()
    processor = MultiLanguageProcessor(llm_provider=llm)

    result = await processor.detect_language(text)
    return result


@router.post("/seeds/translate")
async def translate_to_english(text: str, source_language: str):
    """Translate text to English."""
    llm = get_llm_provider()
    processor = MultiLanguageProcessor(llm_provider=llm)

    result = await processor.translate_to_english(text, source_language)
    return {"translated_text": result}


@router.post("/seeds/process-multilanguage")
async def process_multilanguage_seed(content: str):
    """Process seed material in any supported language."""
    llm = get_llm_provider()
    processor = MultiLanguageProcessor(llm_provider=llm)

    result = await processor.process_multilanguage_seed(content)
    return result


# Regulatory Scenario Generator Endpoints
class RegulatoryGenerateRequest(BaseModel):
    """Request for regulatory scenario generation."""
    regulatory_text: str
    industry: str = "general"
    organization_context: str = ""


@router.post(
    "/regulatory/generate",
    response_model=RegulatoryGeneratorResult,
)
async def generate_regulatory_scenario(
    request: RegulatoryGenerateRequest,
):
    """Generate a simulation scenario from regulatory text."""
    llm = get_llm_provider()
    generator = RegulatoryScenarioGenerator(llm_provider=llm)

    result = await generator.generate_scenario(
        regulatory_text=request.regulatory_text,
        industry=request.industry,
    )

    # Also get impact assessment
    impacts = await generator.identify_impacts(
        regulatory_text=request.regulatory_text,
        organization_context=request.organization_context,
    )

    result.impact_assessment = impacts
    return result


# Confidence Decay Endpoints
@router.get(
    "/simulations/{simulation_id}/confidence-decay",
    response_model=DecayCurveResult,
)
async def get_confidence_decay(simulation_id: str):
    """Get confidence decay curve for a simulation."""
    sim_state = await simulation_engine.get_simulation(simulation_id)
    if not sim_state:
        raise HTTPException(status_code=404, detail="Simulation not found")

    result = confidence_decay_model.compute_decay_curve(
        simulation_id=simulation_id,
        num_rounds=sim_state.config.total_rounds,
        environment_type=sim_state.config.environment_type,
    )
    return result


# Audit Trail Endpoints
@router.get(
    "/simulations/{simulation_id}/audit-trail",
    response_model=AuditTrail,
)
async def get_audit_trail(simulation_id: str):
    """Get the audit trail for a simulation."""
    sim_state = await simulation_engine.get_simulation(simulation_id)
    if not sim_state:
        raise HTTPException(status_code=404, detail="Simulation not found")

    return audit_manager.get_trail(simulation_id)


@router.get("/simulations/{simulation_id}/audit-trail/verify")
async def verify_audit_trail(simulation_id: str):
    """Verify the hash chain integrity of an audit trail."""
    sim_state = await simulation_engine.get_simulation(simulation_id)
    if not sim_state:
        raise HTTPException(status_code=404, detail="Simulation not found")

    is_valid, message = audit_manager.verify_integrity(simulation_id)
    return {"valid": is_valid, "message": message}


@router.get("/simulations/{simulation_id}/audit-trail/export/{format}")
async def export_audit_trail(
    simulation_id: str,
    format: Literal["json", "csv"],
):
    """Export audit trail in JSON or CSV format."""
    sim_state = await simulation_engine.get_simulation(simulation_id)
    if not sim_state:
        raise HTTPException(status_code=404, detail="Simulation not found")

    try:
        data = audit_manager.export_trail(simulation_id, format)
        if format == "csv":
            return PlainTextResponse(
                content=data,
                media_type="text/csv",
                headers={
                    "Content-Disposition": (
                        f"attachment; filename=audit_trail_{simulation_id}.csv"
                    )
                },
            )
        return PlainTextResponse(
            content=data,
            media_type="application/json",
            headers={
                "Content-Disposition": (
                    f"attachment; filename=audit_trail_{simulation_id}.json"
                )
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ZOPA Analysis Endpoints
@router.post(
    "/simulations/{simulation_id}/zopa",
    response_model=ZOPAResult,
)
async def analyze_zopa(simulation_id: str):
    """Run ZOPA analysis for a negotiation simulation."""
    sim_state = await simulation_engine.get_simulation(simulation_id)
    if not sim_state:
        raise HTTPException(status_code=404, detail="Simulation not found")

    llm = get_llm_provider()
    analyzer = ZOPAAnalyzer(llm_provider=llm)

    result = await analyzer.analyze(sim_state)
    return result


# Market Intelligence Endpoints
class MarketIntelligenceConfigRequest(BaseModel):
    """Request for market intelligence configuration."""
    simulation_id: str
    stock_symbols: list[str] | None = None
    news_queries: list[str] | None = None
    refresh_interval: int | None = None


@router.post("/market-intelligence/configure")
async def configure_market_intelligence(
    request: MarketIntelligenceConfigRequest,
):
    """Configure market intelligence sources for a simulation."""
    config = {
        "stock_symbols": request.stock_symbols or [],
        "news_queries": request.news_queries or [],
        "refresh_interval": request.refresh_interval,
    }
    result = await market_intelligence_service.configure_sources(
        request.simulation_id, config
    )
    return result


@router.get("/market-intelligence/feed/{simulation_id}")
async def get_market_intelligence_feed(simulation_id: str):
    """Get latest market intelligence feed for a simulation."""
    result = await market_intelligence_service.get_market_feed(simulation_id)
    return result


@router.post("/market-intelligence/inject/{simulation_id}")
async def inject_market_intelligence(simulation_id: str):
    """Inject market intelligence into agent worldviews."""
    feed = await market_intelligence_service.get_market_feed(simulation_id)
    result = await market_intelligence_service.update_agent_worldview(
        simulation_id, feed
    )
    return result


# Backtesting Endpoints
class BacktestRequest(BaseModel):
    """Request for running a backtest."""
    case_id: str | None = None
    seed_material: str | None = None
    actual_outcomes: dict | None = None


@router.post("/simulations/backtest")
async def run_backtest(request: BacktestRequest):
    """Run a backtest against historical outcomes."""
    result = await backtesting_engine.run_backtest(
        case_id=request.case_id,
        seed_material=request.seed_material,
        actual_outcomes=request.actual_outcomes,
    )
    return result


@router.get("/simulations/backtest/cases")
async def get_backtest_cases():
    """Get list of bundled backtest cases."""
    cases = backtesting_engine.get_bundled_cases()
    return {"cases": cases}


# Sensitivity Analysis Endpoints
@router.post(
    "/simulations/{simulation_id}/sensitivity",
    response_model=TornadoChartData,
)
async def run_sensitivity_analysis(simulation_id: str):
    """Run sensitivity analysis on a completed simulation.

    Analyzes how key parameters affect simulation outcomes
    and returns tornado chart data.
    """
    sim_state = await simulation_engine.get_simulation(simulation_id)
    if not sim_state:
        raise HTTPException(status_code=404, detail="Simulation not found")

    llm = get_llm_provider()
    analyzer = SensitivityAnalyzer(llm_provider=llm)

    result = await analyzer.analyze(sim_state)
    return result
