"""Third-party API integration router.

Provides public API endpoints for external integrations with API key auth.
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api_integrations.auth import (
    APIKey,
    api_key_manager,
    require_permission,
    verify_api_key,
)
from app.api_integrations.webhooks import (
    Webhook,
    webhook_manager,
)
from app.simulation.engine import simulation_engine
from app.simulation.models import (
    SimulationConfig,
    SimulationCreateRequest,
    SimulationState,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["api-v1"])


# Request/Response models


class CreateAPIKeyRequest(BaseModel):
    """Request to create a new API key."""

    name: str
    permissions: list[str] = []


class RegisterWebhookRequest(BaseModel):
    """Request to register a webhook."""

    url: str
    events: list[str]
    metadata: dict[str, Any] | None = None


# API Key Management Endpoints (no auth required for initial setup)


@router.post("/api-keys", response_model=dict)
async def create_api_key(request: CreateAPIKeyRequest):
    """Generate a new API key.

    Note: In production, this endpoint should be protected.
    """
    api_key = api_key_manager.generate_key(
        name=request.name,
        permissions=request.permissions,
    )
    logger.info(f"Created API key: {api_key.name}")
    return {
        "key_id": api_key.key_id,
        "name": api_key.name,
        "key": api_key.key,  # Only returned on creation
        "permissions": api_key.permissions,
        "created_at": api_key.created_at,
    }


@router.get("/api-keys")
async def list_api_keys():
    """List all API keys (masked)."""
    return api_key_manager.list_keys()


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(key_id: str):
    """Revoke an API key."""
    success = api_key_manager.revoke_key(key_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key not found: {key_id}",
        )
    return {"status": "revoked", "key_id": key_id}


# Webhook Management Endpoints


@router.post("/webhooks", response_model=Webhook)
async def register_webhook(
    request: RegisterWebhookRequest,
    api_key: APIKey = Depends(verify_api_key),
):
    """Register a new webhook."""
    try:
        webhook = webhook_manager.register_webhook(
            url=request.url,
            events=request.events,
            api_key_id=api_key.key_id,
            metadata=request.metadata,
        )
        return webhook
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/webhooks", response_model=list[Webhook])
async def list_webhooks(api_key: APIKey = Depends(verify_api_key)):
    """List webhooks for the authenticated API key."""
    return webhook_manager.list_webhooks(api_key_id=api_key.key_id)


@router.delete("/webhooks/{webhook_id}")
async def delete_webhook(
    webhook_id: str,
    api_key: APIKey = Depends(verify_api_key),
):
    """Delete a webhook."""
    webhook = webhook_manager.get_webhook(webhook_id)
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook not found: {webhook_id}",
        )

    # Verify ownership
    if webhook.api_key_id != api_key.key_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this webhook",
        )

    webhook_manager.delete_webhook(webhook_id)
    return {"status": "deleted", "webhook_id": webhook_id}


# Public Simulation API Endpoints (require API key)


@router.post("/simulations", response_model=SimulationState)
async def create_simulation(
    request: SimulationCreateRequest,
    api_key: APIKey = Depends(require_permission("write:simulations")),
):
    """Create a new simulation via public API."""
    try:
        config = SimulationConfig(
            name=request.name,
            description=request.description,
            playbook_id=request.playbook_id,
            environment_type=request.environment_type,
            agents=request.agents,
            total_rounds=request.total_rounds,
            seed_id=request.seed_id,
            parameters=request.parameters,
        )

        sim_state = await simulation_engine.create_simulation(config)

        # Fire webhook
        await webhook_manager.fire_webhook(
            "simulation_started",
            {
                "simulation_id": sim_state.config.id,
                "name": sim_state.config.name,
                "api_key_id": api_key.key_id,
            },
        )

        return sim_state

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create simulation: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred.",
        )


@router.get("/simulations/{simulation_id}", response_model=SimulationState)
async def get_simulation(
    simulation_id: str,
    api_key: APIKey = Depends(require_permission("read:simulations")),
):
    """Get simulation status and results."""
    sim_state = await simulation_engine.get_simulation(simulation_id)
    if not sim_state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation not found: {simulation_id}",
        )
    return sim_state


@router.get("/simulations/{simulation_id}/results")
async def get_simulation_results(
    simulation_id: str,
    api_key: APIKey = Depends(require_permission("read:simulations")),
):
    """Get simulation results summary."""
    sim_state = await simulation_engine.get_simulation(simulation_id)
    if not sim_state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation not found: {simulation_id}",
        )

    return {
        "simulation_id": simulation_id,
        "status": sim_state.status.value,
        "current_round": sim_state.current_round,
        "total_rounds": sim_state.config.total_rounds,
        "results_summary": sim_state.results_summary,
        "agent_count": len(sim_state.agents),
    }


@router.post("/simulations/{simulation_id}/start")
async def start_simulation(
    simulation_id: str,
    api_key: APIKey = Depends(require_permission("write:simulations")),
):
    """Start a simulation."""
    import asyncio

    from app.simulation.router import manager

    sim_state = await simulation_engine.get_simulation(simulation_id)
    if not sim_state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation not found: {simulation_id}",
        )

    if sim_state.status.value == "running":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Simulation already running",
        )

    # Import message type
    from app.simulation.models import SimulationMessage

    # Define message callback
    async def on_message(message: SimulationMessage):
        await manager.broadcast(message.model_dump(), simulation_id)

    # Start simulation
    asyncio.create_task(
        simulation_engine.run_simulation(
            simulation_id,
            on_message=on_message,
        ),
        name=f"api-simulation-{simulation_id}",
    )

    # Fire webhook
    await webhook_manager.fire_webhook(
        "simulation_started",
        {
            "simulation_id": simulation_id,
            "api_key_id": api_key.key_id,
        },
    )

    return {"status": "started", "simulation_id": simulation_id}


# Public Reports API Endpoints


@router.get("/reports/{report_id}")
async def get_report(
    report_id: str,
    api_key: APIKey = Depends(require_permission("read:reports")),
):
    """Get a report by ID."""
    # Import report store
    from app.reports.router import _report_store

    report = _report_store.get(report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report not found: {report_id}",
        )

    return report
