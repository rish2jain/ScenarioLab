"""FastAPI router for report generation endpoints."""

import logging
from datetime import datetime
from typing import Literal

import httpx
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.config import settings
from app.llm.factory import get_llm_provider
from app.reports.exporters import (
    export_to_json,
    export_to_markdown,
    export_to_miro,
    export_to_pdf,
)
from app.reports.models import ReviewCheckpoint, SimulationReport
from app.reports.report_agent import ReportAgent
from app.reports.annotations import (
    Annotation,
    AnnotationCreate,
    annotation_manager,
)
from app.simulation.engine import simulation_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["reports"])


class MiroStatusResponse(BaseModel):
    """Response model for Miro status endpoint."""

    configured: bool
    connected: bool
    board_id: str | None
    mode: str


# In-memory storage for reports
_report_store: dict[str, SimulationReport] = {}


class CheckpointRequest(BaseModel):
    """Request to create a review checkpoint."""

    stage: Literal["draft", "risk_review", "scenario_review", "final"]
    reviewer_notes: str = ""


class CheckpointUpdateRequest(BaseModel):
    """Request to update a checkpoint."""

    status: Literal["approved", "revision_requested"]
    reviewer_notes: str = ""


@router.post(
    "/simulations/{simulation_id}/report",
    response_model=SimulationReport,
    status_code=status.HTTP_201_CREATED,
)
async def generate_report(simulation_id: str):
    """Generate a report for a completed simulation.

    Args:
        simulation_id: The ID of the simulation to generate report for

    Returns:
        The generated simulation report

    Raises:
        HTTPException: If simulation not found or not completed
    """
    logger.info(f"Generating report for simulation {simulation_id}")

    # Get simulation from engine
    sim_state = await simulation_engine.get_simulation(simulation_id)
    if not sim_state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation not found: {simulation_id}",
        )

    # Check if simulation is completed
    if sim_state.status.value not in ["completed", "failed"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Simulation must be completed before generating report. "
            f"Current status: {sim_state.status.value}",
        )

    # Check if report already exists
    existing_report = None
    for report in _report_store.values():
        if report.simulation_id == simulation_id:
            existing_report = report
            break

    if existing_report:
        logger.info(f"Returning existing report {existing_report.id}")
        return existing_report

    # Generate new report
    try:
        llm_provider = get_llm_provider()
        report_agent = ReportAgent(llm_provider, sim_state)
        report = await report_agent.generate_full_report()

        # Store report
        _report_store[report.id] = report

        logger.info(f"Report {report.id} done for sim {simulation_id}")
        return report

    except Exception as e:
        logger.error(f"Error generating report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate report: {str(e)}",
        )


@router.get("/reports/miro/status", response_model=MiroStatusResponse)
async def get_miro_status():
    """Get Miro API connection status.

    Returns:
        MiroStatusResponse with configuration status, connection status,
        board_id, and mode (real/mock)
    """
    token = settings.miro_api_token
    board_id = settings.miro_board_id or None

    # Check if token is configured
    configured = bool(token)

    if not configured:
        return MiroStatusResponse(
            configured=False,
            connected=False,
            board_id=board_id,
            mode="mock",
        )

    # Test token validity with a simple API call
    connected = False
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.miro.com/v2/boards",
                headers={"Authorization": f"Bearer {token}"},
                params={"limit": 1},
                timeout=10.0,
            )
            connected = response.status_code == 200
    except Exception as e:
        logger.warning(f"Miro API test failed: {e}")
        connected = False

    return MiroStatusResponse(
        configured=True,
        connected=connected,
        board_id=board_id,
        mode="real" if connected else "mock",
    )


@router.get("/reports", response_model=list[SimulationReport])
async def list_reports():
    """List all generated reports.

    Returns:
        List of all simulation reports
    """
    return list(_report_store.values())


@router.get("/reports/{report_id}", response_model=SimulationReport)
async def get_report(report_id: str):
    """Get a specific report by ID.

    Args:
        report_id: The ID of the report to retrieve

    Returns:
        The simulation report

    Raises:
        HTTPException: If report not found
    """
    report = _report_store.get(report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report not found: {report_id}",
        )
    return report


@router.get("/reports/{report_id}/export/{format}")
async def export_report(report_id: str, format: str):
    """Export a report in the specified format.

    Args:
        report_id: The ID of the report to export
        format: Export format (markdown, json, pdf, miro)

    Returns:
        The exported report content with appropriate content type

    Raises:
        HTTPException: If report not found or format unsupported
    """
    report = _report_store.get(report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report not found: {report_id}",
        )

    format = format.lower()

    try:
        if format == "json":
            content = await export_to_json(report)
            return {
                "content": content.decode("utf-8"),
                "content_type": "application/json",
                "filename": f"report_{report_id}.json",
            }

        elif format == "markdown":
            content = await export_to_markdown(report)
            return {
                "content": content.decode("utf-8"),
                "content_type": "text/markdown",
                "filename": f"report_{report_id}.md",
            }

        elif format == "pdf":
            content = await export_to_pdf(report)
            return {
                "content": content.decode("utf-8"),
                "content_type": "text/html",  # Returns HTML for PDF rendering
                "filename": f"report_{report_id}.html",
                "note": "PDF export returns HTML. Use a PDF renderer like "
                "WeasyPrint or wkhtmltopdf to convert to PDF.",
            }

        elif format == "miro":
            result = await export_to_miro(report, settings.miro_api_token)
            if result.get("mock_mode"):
                return {
                    "mock_mode": True,
                    "note": result.get("note"),
                    "board_structure": result,
                    "message": (
                        "Miro export is in mock mode. "
                        "Configure MIRO_API_TOKEN to create real boards."
                    ),
                }
            return {
                "mock_mode": False,
                "board_id": result.get("board_id"),
                "board_url": result.get("board_url"),
                "stats": {
                    "frames": result.get("frames_created"),
                    "cards": result.get("cards_created"),
                    "sticky_notes": result.get("sticky_notes_created"),
                    "connectors": result.get("connectors_created"),
                },
            }

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported format: {format}. "
                f"Supported formats: json, markdown, pdf, miro",
            )

    except Exception as e:
        logger.error(f"Error exporting report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export report: {str(e)}",
        )


@router.get("/reports/{report_id}/export/interactive-deck")
async def export_interactive_deck(
    report_id: str,
    logo_url: str | None = None,
    primary_color: str = "#3B82F6",
    company_name: str = "MiroFish",
):
    """Export report as interactive HTML presentation deck.

    Returns a self-contained HTML file with embedded JavaScript.

    Query params:
        logo_url: Optional URL for company logo
        primary_color: Primary color for styling (hex)
        company_name: Company name for branding
    """
    from fastapi.responses import HTMLResponse

    from app.reports.exporters.interactive_deck import (
        export_interactive_deck as do_export,
    )
    from app.simulation.engine import simulation_engine

    report = _report_store.get(report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report not found: {report_id}",
        )

    try:
        # Get simulation state for additional context
        sim_state = await simulation_engine.get_simulation(
            report.simulation_id
        )

        html = await do_export(
            report=report,
            simulation_state=sim_state,
            logo_url=logo_url,
            primary_color=primary_color,
            company_name=company_name,
        )

        return HTMLResponse(content=html)

    except Exception as e:
        logger.error(f"Error exporting interactive deck: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export: {str(e)}",
        )


@router.post(
    "/reports/{report_id}/checkpoint",
    response_model=SimulationReport,
)
async def create_checkpoint(report_id: str, request: CheckpointRequest):
    """Submit a review checkpoint for a report.

    Args:
        report_id: The ID of the report
        request: Checkpoint creation request

    Returns:
        The updated report

    Raises:
        HTTPException: If report not found
    """
    report = _report_store.get(report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report not found: {report_id}",
        )

    checkpoint = ReviewCheckpoint(
        stage=request.stage,
        status="pending",
        reviewer_notes=request.reviewer_notes,
    )

    report.checkpoints.append(checkpoint)
    report.updated_at = datetime.utcnow().isoformat()

    # Update report status based on stage
    if request.stage == "final":
        report.status = "in_review"

    logger.info(f"Checkpoint {checkpoint.checkpoint_id} for {report_id}")
    return report


@router.patch(
    "/reports/{report_id}/checkpoint/{checkpoint_id}",
    response_model=SimulationReport,
)
async def update_checkpoint(
    report_id: str,
    checkpoint_id: str,
    request: CheckpointUpdateRequest,
):
    """Update a checkpoint status (approve or request revision).

    Args:
        report_id: The ID of the report
        checkpoint_id: The ID of the checkpoint to update
        request: Checkpoint update request

    Returns:
        The updated report

    Raises:
        HTTPException: If report or checkpoint not found
    """
    report = _report_store.get(report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report not found: {report_id}",
        )

    checkpoint = None
    for cp in report.checkpoints:
        if cp.checkpoint_id == checkpoint_id:
            checkpoint = cp
            break

    if not checkpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Checkpoint not found: {checkpoint_id}",
        )

    checkpoint.status = request.status
    if request.reviewer_notes:
        checkpoint.reviewer_notes = request.reviewer_notes
    checkpoint.timestamp = datetime.utcnow().isoformat()

    report.updated_at = datetime.utcnow().isoformat()

    # Update report status if all checkpoints approved
    if request.status == "approved":
        all_approved = all(
            cp.status == "approved" for cp in report.checkpoints
        )
        if all_approved and report.checkpoints:
            report.status = "final"
    elif request.status == "revision_requested":
        report.status = "draft"

    logger.info(f"Checkpoint {checkpoint_id} updated to {request.status}")
    return report


# Annotation Endpoints
@router.post(
    "/annotations",
    response_model=Annotation,
    status_code=status.HTTP_201_CREATED,
)
async def create_annotation(request: AnnotationCreate):
    """Create a new annotation.

    Args:
        request: Annotation creation request

    Returns:
        The created annotation
    """
    annotation = annotation_manager.create_annotation(
        simulation_id=request.simulation_id,
        agent_id=request.agent_id,
        message_id=request.message_id,
        round_number=request.round_number,
        content=request.content,
        tag=request.tag,
        annotator=request.annotator,
    )
    logger.info(f"Created annotation {annotation.id}")
    return annotation


@router.get(
    "/simulations/{simulation_id}/annotations",
    response_model=list[Annotation],
)
async def get_annotations(
    simulation_id: str,
    tag: str | None = None,
    annotator: str | None = None,
    round: int | None = None,
):
    """Get annotations for a simulation.

    Args:
        simulation_id: The simulation ID
        tag: Filter by tag (agree, disagree, caveat)
        annotator: Filter by annotator name
        round: Filter by round number

    Returns:
        List of matching annotations
    """
    annotations = annotation_manager.get_annotations(
        simulation_id=simulation_id,
        tag=tag,
        annotator=annotator,
        round=round,
    )
    return annotations


@router.delete("/annotations/{annotation_id}")
async def delete_annotation(annotation_id: str):
    """Delete an annotation.

    Args:
        annotation_id: The ID of the annotation to delete

    Returns:
        Success status

    Raises:
        HTTPException: If annotation not found
    """
    success = annotation_manager.delete_annotation(annotation_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Annotation not found: {annotation_id}",
        )
    return {"status": "deleted", "annotation_id": annotation_id}


@router.get("/simulations/{simulation_id}/annotations/export")
async def export_annotations(simulation_id: str):
    """Export all annotations for a simulation as JSON.

    Args:
        simulation_id: The simulation ID

    Returns:
        JSON export of all annotations
    """
    export_data = annotation_manager.export_annotations(simulation_id)
    return export_data
