"""FastAPI router for persona management endpoints."""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.config import settings
from app.llm.factory import get_llm_provider
from app.personas.archetypes import ArchetypeDefinition
from app.personas.behavioral_axioms import (
    AxiomExtractionResult,
    AxiomExtractor,
    AxiomValidationResult,
    BehavioralAxiom,
)
from app.personas.counterpart import counterpart_manager
from app.personas.designer import (
    Citation,
    CustomPersonaConfig,
    CustomPersonaDeleteOutcome,
    ResearchRefreshError,
    persona_designer,
)
from app.personas.interview_extractor import ExtractedPersona, InterviewExtractor
from app.personas.library import (
    create_custom_persona,
    get_all_archetypes,
    get_archetype,
    get_roster_for_playbook,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/personas", tags=["personas"])


def _retry_after_header_from_exception_chain(exc: BaseException | None) -> str | None:
    """Best-effort ``Retry-After`` header value (delay-seconds or HTTP-date).

    Walks ``__cause__`` so hints on ``ResearchRefreshError`` and upstream errors
    (e.g. httpx ``HTTPStatusError`` response headers) are both considered.
    """
    seen: set[int] = set()
    while exc is not None and id(exc) not in seen:
        seen.add(id(exc))
        ra = getattr(exc, "retry_after", None)
        if isinstance(ra, str) and ra.strip():
            return ra.strip()
        secs = getattr(exc, "retry_after_seconds", None)
        if isinstance(secs, (int, float)) and not isinstance(secs, bool) and secs >= 0:
            return str(int(secs))
        upstream = getattr(exc, "upstream_headers", None)
        if isinstance(upstream, dict):
            for key in ("Retry-After", "retry-after"):
                if key in upstream and str(upstream[key]).strip():
                    return str(upstream[key]).strip()
        resp = getattr(exc, "response", None)
        if resp is not None:
            headers = getattr(resp, "headers", None)
            if headers is not None:
                h = headers.get("Retry-After") or headers.get("retry-after")
                if h:
                    return str(h).strip()
        exc = exc.__cause__
    return None


class CustomPersonaRequest(BaseModel):
    """Request to create a custom persona."""

    base_archetype_id: str
    overrides: dict[str, Any]


class CustomPersonaResponse(BaseModel):
    """Response containing the created custom persona."""

    persona: ArchetypeDefinition
    message: str


class ArchetypeListResponse(BaseModel):
    """Response containing list of archetypes."""

    archetypes: list[ArchetypeDefinition]
    count: int


class RosterResponse(BaseModel):
    """Response containing playbook roster."""

    playbook_id: str
    roster: list[dict[str, Any]]


@router.get("", response_model=ArchetypeListResponse)
async def list_archetypes() -> ArchetypeListResponse:
    """Get all available persona archetypes.

    Returns:
        List of all consulting archetype definitions
    """
    archetypes = get_all_archetypes()
    return ArchetypeListResponse(archetypes=archetypes, count=len(archetypes))


@router.post(
    "/custom",
    response_model=CustomPersonaResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_persona(request: CustomPersonaRequest) -> CustomPersonaResponse:
    """Create a custom persona from a base archetype.

    Args:
        request: Custom persona creation request

    Returns:
        The created custom persona

    Raises:
        HTTPException: If base archetype not found
    """
    try:
        custom_persona = create_custom_persona(request.base_archetype_id, request.overrides)
        return CustomPersonaResponse(
            persona=custom_persona,
            message=f"Created custom persona from {request.base_archetype_id}",
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/roster/{playbook_id}", response_model=RosterResponse)
async def get_playbook_roster(playbook_id: str) -> RosterResponse:
    """Get recommended persona roster for a playbook.

    Args:
        playbook_id: The playbook identifier

    Returns:
        Recommended roster for the playbook
    """
    roster = get_roster_for_playbook(playbook_id)
    return RosterResponse(playbook_id=playbook_id, roster=roster)


# ========== Counterpart Agent Endpoints ==========


class CreateCounterpartRequest(BaseModel):
    """Request to create a counterpart agent."""

    brief: str
    stakeholder_type: str
    rehearsal_mode: str = "challenging"


class RehearseRequest(BaseModel):
    """Request for a rehearsal turn."""

    message: str


class GenerateObjectionsRequest(BaseModel):
    """Request to generate objections."""

    presentation_text: str


@router.post(
    "/counterpart/create",
    status_code=status.HTTP_201_CREATED,
)
async def create_counterpart(
    request: CreateCounterpartRequest,
) -> dict[str, Any]:
    """Create a counterpart agent for rehearsal.

    Args:
        request: Counterpart creation request

    Returns:
        Created counterpart configuration
    """
    try:
        return await counterpart_manager.create_counterpart(
            brief=request.brief,
            stakeholder_type=request.stakeholder_type,
            rehearsal_mode=request.rehearsal_mode,
        )
    except Exception as e:
        logger.error(f"Failed to create counterpart: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/counterpart")
async def list_counterparts() -> list[dict[str, Any]]:
    """List all counterpart agents."""
    return counterpart_manager.list_counterparts()


@router.get("/counterpart/{counterpart_id}")
async def get_counterpart(counterpart_id: str) -> dict[str, Any]:
    """Get a counterpart by ID."""
    counterpart = counterpart_manager.get_counterpart(counterpart_id)
    if not counterpart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Counterpart not found: {counterpart_id}",
        )
    return counterpart.model_dump()


@router.post("/counterpart/{counterpart_id}/rehearse")
async def rehearse_counterpart(
    counterpart_id: str,
    request: RehearseRequest,
) -> dict[str, Any]:
    """Run a rehearsal turn with a counterpart.

    Args:
        counterpart_id: The counterpart ID
        request: Rehearsal message

    Returns:
        Counterpart response with coaching tips
    """
    try:
        return await counterpart_manager.rehearse(
            counterpart_id=counterpart_id,
            user_message=request.message,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Rehearsal failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/counterpart/{counterpart_id}/objections")
async def generate_objections(
    counterpart_id: str,
    request: GenerateObjectionsRequest,
) -> list[dict[str, Any]]:
    """Generate objections from a counterpart.

    Args:
        counterpart_id: The counterpart ID
        request: Presentation text to analyze

    Returns:
        List of objections
    """
    try:
        return await counterpart_manager.generate_objections(
            counterpart_id=counterpart_id,
            presentation_text=request.presentation_text,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to generate objections: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/counterpart/{counterpart_id}/feedback")
async def get_rehearsal_feedback(
    counterpart_id: str,
) -> dict[str, Any]:
    """Get feedback summary for a rehearsal session.

    Args:
        counterpart_id: The counterpart ID

    Returns:
        Feedback summary
    """
    try:
        return await counterpart_manager.get_feedback_summary(
            counterpart_id=counterpart_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to get feedback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.delete("/counterpart/{counterpart_id}")
async def delete_counterpart(counterpart_id: str) -> dict[str, str]:
    """Delete a counterpart."""
    if counterpart_manager.delete_counterpart(counterpart_id):
        return {"status": "deleted"}
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Counterpart not found: {counterpart_id}",
    )


# ========== Custom Persona Designer Endpoints ==========


class CreatePersonaConfigRequest(BaseModel):
    """Request to create a custom persona configuration."""

    name: str
    role: str
    description: str = ""
    authority_level: int = 5
    risk_tolerance: str = "moderate"
    information_bias: str = "balanced"
    decision_speed: str = "moderate"
    coalition_tendencies: float = 0.5
    incentive_structure: list[str] = []
    behavioral_axioms: list[str] = []
    evidence_summary: str = ""
    citations: list[Citation] = Field(default_factory=list)
    last_researched_at: datetime | None = None
    evidence_pack_id: str = ""


class UpdatePersonaConfigRequest(BaseModel):
    """Request to update a custom persona configuration."""

    name: str | None = None
    role: str | None = None
    description: str | None = None
    authority_level: int | None = None
    risk_tolerance: str | None = None
    information_bias: str | None = None
    decision_speed: str | None = None
    coalition_tendencies: float | None = None
    incentive_structure: list[str] | None = None
    behavioral_axioms: list[str] | None = None
    evidence_summary: str | None = None
    citations: list[Citation] | None = None
    last_researched_at: datetime | None = None
    evidence_pack_id: str | None = None


class ResearchPersonaRequest(BaseModel):
    """Ground a persona from public executive research."""

    name: str
    company: str = ""
    role: str = ""


class ValidateCoherenceRequest(BaseModel):
    """Request to validate persona coherence."""

    config: dict[str, Any]


@router.post(
    "/research-persona",
    response_model=ExtractedPersona,
    status_code=status.HTTP_200_OK,
)
async def research_persona_http(
    request: ResearchPersonaRequest,
) -> ExtractedPersona:
    """Research-backed persona (InterviewExtractor.research_persona)."""
    llm = get_llm_provider()
    extractor = InterviewExtractor(llm_provider=llm)
    try:
        return await extractor.research_persona(request.name, company=request.company, role=request.role)
    except Exception as e:
        logger.exception(
            "research_persona failed (name=%r company=%r role=%r)",
            request.name,
            request.company,
            request.role,
        )
        detail = "Internal server error while researching persona"
        if settings.debug:
            detail = f"{detail}: {e!s}"
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
        ) from e


@router.post(
    "/designer",
    status_code=status.HTTP_201_CREATED,
)
async def create_designer_persona(
    request: CreatePersonaConfigRequest,
) -> dict[str, Any]:
    """Create a custom persona using the designer.

    Args:
        request: Persona configuration

    Returns:
        Created persona with generated system prompt
    """
    try:
        return await persona_designer.create_custom_persona(request.model_dump())
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/designer")
async def list_designer_personas() -> list[dict[str, Any]]:
    """List all custom personas created with the designer."""
    return await persona_designer.list_custom_personas()


@router.get("/designer/{persona_id}")
async def get_designer_persona(persona_id: str) -> dict[str, Any]:
    """Get a custom persona by ID."""
    persona = await persona_designer.get_custom_persona(persona_id)
    if not persona:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Persona not found: {persona_id}",
        )
    return persona


@router.post(
    "/designer/{persona_id}/refresh-research",
    response_model=CustomPersonaConfig,
)
async def refresh_designer_persona_research(persona_id: str) -> CustomPersonaConfig:
    """Re-fetch web evidence and merge into designer persona."""
    try:
        updated = await persona_designer.refresh_research_for_persona(persona_id)
    except ResearchRefreshError as e:
        retry_after = _retry_after_header_from_exception_chain(e)
        kwargs: dict[str, Any] = {
            "status_code": status.HTTP_503_SERVICE_UNAVAILABLE,
            "detail": str(e),
        }
        if retry_after is not None:
            kwargs["headers"] = {"Retry-After": retry_after}
        raise HTTPException(**kwargs) from e
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Persona not found: {persona_id}",
        )
    return CustomPersonaConfig.model_validate(updated)


@router.put("/designer/{persona_id}")
async def update_designer_persona(
    persona_id: str,
    request: UpdatePersonaConfigRequest,
) -> dict[str, Any]:
    """Update a custom persona.

    Args:
        persona_id: The persona ID
        request: Fields to update

    Returns:
        Updated persona
    """
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    persona = await persona_designer.update_custom_persona(persona_id, updates)
    if not persona:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Persona not found: {persona_id}",
        )
    return persona


@router.delete("/designer/{persona_id}")
async def delete_designer_persona(persona_id: str) -> dict[str, str]:
    """Delete a custom persona."""
    outcome = await persona_designer.delete_custom_persona(persona_id)
    if outcome is CustomPersonaDeleteOutcome.DELETED:
        return {"status": "deleted"}
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Persona not found: {persona_id}",
    )


@router.post("/designer/validate")
async def validate_persona_coherence(
    request: ValidateCoherenceRequest,
) -> dict[str, Any]:
    """Validate coherence of a persona configuration.

    Args:
        request: Configuration to validate

    Returns:
        List of coherence warnings
    """
    warnings = persona_designer.validate_coherence(request.config)
    return {"warnings": warnings}


# ========== Behavioral Axiom Endpoints ==========


class ExtractAxiomsRequest(BaseModel):
    """Request to extract behavioral axioms."""

    historical_data: str
    data_type: str = "board_minutes"


class ValidateAxiomsRequest(BaseModel):
    """Request to validate axioms against holdout data."""

    axioms: list[BehavioralAxiom]
    holdout_data: str


@router.post(
    "/axioms/extract",
    response_model=AxiomExtractionResult,
    status_code=status.HTTP_201_CREATED,
)
async def extract_behavioral_axioms(
    request: ExtractAxiomsRequest,
) -> AxiomExtractionResult:
    """Extract behavioral axioms from historical data.

    Args:
        request: Historical data and data type

    Returns:
        Extracted behavioral axioms
    """
    logger.info(f"Extracting axioms from {request.data_type} " f"({len(request.historical_data)} chars)")

    try:
        llm = get_llm_provider()
        extractor = AxiomExtractor(llm_provider=llm)

        result = await extractor.extract_axioms(
            historical_data=request.historical_data,
            data_type=request.data_type,
        )
        return result
    except Exception as e:
        logger.error(f"Axiom extraction failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Axiom extraction failed: {str(e)}",
        )


@router.post(
    "/axioms/validate",
    response_model=AxiomValidationResult,
    status_code=status.HTTP_200_OK,
)
async def validate_behavioral_axioms(
    request: ValidateAxiomsRequest,
) -> AxiomValidationResult:
    """Validate extracted axioms against holdout data.

    Args:
        request: Axioms to validate and holdout data

    Returns:
        Validation results with accuracy scores
    """
    logger.info(f"Validating {len(request.axioms)} axioms " f"against {len(request.holdout_data)} chars")

    try:
        llm = get_llm_provider()
        extractor = AxiomExtractor(llm_provider=llm)

        result = await extractor.validate_axioms(
            axioms=request.axioms,
            holdout_data=request.holdout_data,
        )
        return result
    except Exception as e:
        logger.error(f"Axiom validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Axiom validation failed: {str(e)}",
        )


# Registered last: a path like ``/designer`` must not be captured as ``{archetype_id}``.
@router.get("/{archetype_id}", response_model=ArchetypeDefinition)
async def get_single_archetype(archetype_id: str) -> ArchetypeDefinition:
    """Get a single archetype by ID.

    Args:
        archetype_id: The archetype identifier

    Returns:
        The archetype definition

    Raises:
        HTTPException: If archetype not found
    """
    archetype = get_archetype(archetype_id)
    if not archetype:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Archetype not found: {archetype_id}",
        )
    return archetype
