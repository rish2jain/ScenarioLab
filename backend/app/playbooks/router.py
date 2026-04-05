"""FastAPI router for playbook management endpoints."""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.playbooks.manager import (
    AgentRosterEntry,
    PlaybookConfig,
    PlaybookSummary,
    get_all_playbooks,
    get_playbook,
    prefill_roster,
    validate_playbook_config,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/playbooks", tags=["playbooks"])


class PlaybookListResponse(BaseModel):
    """Response containing list of playbooks."""

    playbooks: list[PlaybookSummary]
    count: int


class PlaybookDetailResponse(BaseModel):
    """Response containing full playbook details."""

    playbook: PlaybookConfig


class RosterResponse(BaseModel):
    """Response containing pre-filled roster."""

    playbook_id: str
    roster: list[AgentRosterEntry]


class ValidationRequest(BaseModel):
    """Request to validate a playbook configuration."""

    config: dict[str, Any]


class ValidationResponse(BaseModel):
    """Response from playbook validation."""

    is_valid: bool
    errors: list[str]


@router.get("", response_model=PlaybookListResponse)
async def list_playbooks() -> PlaybookListResponse:
    """Get all available playbook summaries.

    Returns:
        List of all playbook summaries
    """
    playbooks = get_all_playbooks()
    return PlaybookListResponse(playbooks=playbooks, count=len(playbooks))


@router.get("/{playbook_id}", response_model=PlaybookDetailResponse)
async def get_single_playbook(playbook_id: str) -> PlaybookDetailResponse:
    """Get full configuration for a single playbook.

    Args:
        playbook_id: The playbook identifier

    Returns:
        The complete playbook configuration

    Raises:
        HTTPException: If playbook not found
    """
    playbook = get_playbook(playbook_id)
    if not playbook:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Playbook not found: {playbook_id}")
    return PlaybookDetailResponse(playbook=playbook)


@router.get("/{playbook_id}/roster", response_model=RosterResponse)
async def get_playbook_roster(playbook_id: str) -> RosterResponse:
    """Get pre-filled agent roster for a playbook.

    Args:
        playbook_id: The playbook identifier

    Returns:
        The default agent roster for the playbook

    Raises:
        HTTPException: If playbook not found
    """
    roster = prefill_roster(playbook_id)
    if roster is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Playbook not found: {playbook_id}")
    return RosterResponse(playbook_id=playbook_id, roster=roster)


@router.post("/validate", response_model=ValidationResponse)
async def validate_playbook(request: ValidationRequest) -> ValidationResponse:
    """Validate a playbook configuration.

    Args:
        request: Validation request containing playbook config

    Returns:
        Validation result with any errors
    """
    is_valid, errors = validate_playbook_config(request.config)
    return ValidationResponse(is_valid=is_valid, errors=errors)
