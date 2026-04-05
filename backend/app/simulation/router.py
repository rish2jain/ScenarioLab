"""FastAPI router for simulation endpoints and WebSocket."""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.db.chat import (
    ChatHistoryRepository,
    flatten_chat_exchanges_to_session_messages,
)
from app.graph.ontology_generator import generate_ontology
from app.llm.factory import get_llm_provider
from app.llm.provider import LLMMessage
from app.llm.wizard_models import validate_wizard_model_override
from app.personas.library import get_archetype
from app.research.stakeholder_research import (
    stakeholder_research_orchestrator,
)
from app.simulation.batch import BatchConfig, BatchRunner
from app.simulation.engine import simulation_engine
from app.simulation.models import (
    DualCreateRequest,
    DualCreateResponse,
    DualRunPresetCreateResponse,
    DualRunPresetWarning,
    EnvironmentType,
    SimulationConfig,
    SimulationCreateRequest,
    SimulationMessage,
    SimulationState,
    SimulationStatus,
)
from app.simulation.monte_carlo import MonteCarloConfig, MonteCarloRunner
from app.simulation.objectives import (
    objective_text_for_stale_check,
    parse_simulation_objective,
    parsed_objective_matches_description,
)
from app.simulation.roster_suggest import suggest_roster_from_text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/simulations", tags=["simulations"])


class DualCreatePairPartError(Exception):
    """Dual-create failed on scenario A or B (non-validation); ``failed_part`` is A or B."""

    def __init__(self, failed_part: str, cause: BaseException) -> None:
        self.failed_part = failed_part
        super().__init__(str(cause))


def _dual_create_http_500_detail(exc: BaseException) -> str:
    """Build 500 detail for dual-create; prefers ``failed_part`` when present."""
    base = "An internal error occurred while creating the comparison pair"
    failed = getattr(exc, "failed_part", None)
    if isinstance(failed, str) and failed:
        return f"{base}; failed_part={failed}"
    return f"{base}; {str(exc)}"


# WebSocket connection manager
class ConnectionManager:
    """Manage WebSocket connections for simulations."""

    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, simulation_id: str):
        """Accept and store a WebSocket connection."""
        await websocket.accept()
        if simulation_id not in self.active_connections:
            self.active_connections[simulation_id] = []
        self.active_connections[simulation_id].append(websocket)
        logger.info(f"WebSocket connected for simulation {simulation_id}")

    def disconnect(self, websocket: WebSocket, simulation_id: str):
        """Remove a WebSocket connection."""
        if simulation_id in self.active_connections:
            if websocket in self.active_connections[simulation_id]:
                self.active_connections[simulation_id].remove(websocket)
        logger.info(f"WebSocket disconnected for simulation {simulation_id}")

    async def broadcast(self, message: dict, simulation_id: str):
        """Broadcast a message to all connections for a simulation."""
        if simulation_id not in self.active_connections:
            return

        disconnected = []
        for connection in self.active_connections[simulation_id]:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)

        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn, simulation_id)


manager = ConnectionManager()

# Track background simulation tasks to prevent silent exception loss
_background_tasks: dict[str, asyncio.Task] = {}

# Chat history storage per simulation (in-memory cache)
_chat_histories: dict[str, list[dict]] = {}

# Chat history repository for persistence
_chat_repo = ChatHistoryRepository()


class ChatRequest(BaseModel):
    """Request to send a chat message to an agent."""

    agent_id: str
    message: str


class ChatResponse(BaseModel):
    """Response from an agent chat."""

    agent_id: str
    agent_name: str
    response: str
    timestamp: str


class ChatHistoryMessage(BaseModel):
    """Serialized chat history entry for the frontend."""

    id: str
    simulation_id: str
    content: str
    timestamp: str
    is_user: bool
    agent_id: str | None = None
    agent_name: str | None = None


def _agent_value(agent: Any, key: str, default: str = "") -> str:
    """Read agent data safely from Pydantic models or dict-like payloads."""
    if isinstance(agent, dict):
        value = agent.get(key, default)
    else:
        value = getattr(agent, key, default)
    return value if isinstance(value, str) else default


class DualRunPresetRequest(BaseModel):
    """Two configs with shared seeds for comparison."""

    name_a: str = "Scenario A"
    name_b: str = "Scenario B"
    base: SimulationCreateRequest
    environment_type_b: str | None = None


def _on_simulation_done(simulation_id: str, task: asyncio.Task):
    """Callback when a background simulation task finishes."""
    _background_tasks.pop(simulation_id, None)
    if task.cancelled():
        logger.warning(f"Simulation task {simulation_id} was cancelled")
    elif task.exception():
        logger.error(
            f"Simulation task {simulation_id} failed: {task.exception()}",
            exc_info=task.exception(),
        )


async def _create_simulation_core(request: SimulationCreateRequest) -> SimulationState:
    """Shared create path for POST / and POST /dual-create."""
    params: dict = dict(request.parameters or {})
    if isinstance(params, dict):
        m = params.get("model")
        if isinstance(m, str) and m.strip():
            validate_wizard_model_override(m)

    desc = objective_text_for_stale_check(request.description, params)
    po = params.get("parsedObjective") or params.get("parsed_objective")
    if isinstance(po, dict) and po and not parsed_objective_matches_description(
        po, request.description, params
    ):
        params.pop("parsedObjective", None)
        params.pop("parsed_objective", None)

    if desc and not params.get("parsedObjective") and not params.get("parsed_objective"):
        mode_raw = params.get("objective_mode") or params.get("objectiveMode")
        mode = str(mode_raw).strip().lower() if isinstance(mode_raw, str) and mode_raw.strip() else "consulting"
        if mode not in ("consulting", "general_prediction"):
            mode = "consulting"
        parsed = await parse_simulation_objective(desc, mode=mode)
        params["parsedObjective"] = parsed.model_dump(mode="json")

    config = SimulationConfig(
        name=request.name,
        description=desc,
        playbook_id=request.playbook_id,
        environment_type=request.environment_type,
        agents=request.agents,
        total_rounds=request.total_rounds,
        seed_id=request.seed_id,
        seed_ids=request.seed_ids,
        parameters=params,
    )

    return await simulation_engine.create_simulation(config)


async def _rollback_dual_create_first(simulation_id: str) -> None:
    """Best-effort delete of the first sim when the second create fails."""
    try:
        ok = await simulation_engine.delete_simulation(simulation_id)
        if not ok:
            logger.error(
                "Dual-create rollback: delete_simulation returned False for %s",
                simulation_id,
            )
    except Exception:
        logger.exception(
            "Dual-create rollback failed for simulation %s — orphan may remain",
            simulation_id,
        )


async def _dual_create_pair(request: DualCreateRequest) -> DualCreateResponse:
    """Shared rollback-safe pair creation for /dual-create and /dual-run-preset-create.

    If scenario B fails after A is fully created, A is removed so no half-pair remains.
    Rollback runs in ``finally`` when ``first_id`` is set but the pair was not completed
    (any failure after the first sim exists, including KeyboardInterrupt / SystemExit).
    """
    first_id: str | None = None
    pair_completed = False
    try:
        first = await _create_simulation_core(request.scenario_a)
        first_id = first.config.id
        second = await _create_simulation_core(request.scenario_b)
        pair_completed = True
        return DualCreateResponse(simulation_a=first, simulation_b=second)
    except Exception as e:
        failed_part = "B" if first_id else "A"
        if isinstance(e, ValueError):
            raise
        logger.error(
            "Dual-create failed (failed_part=%s): %s",
            failed_part,
            e,
            exc_info=True,
        )
        try:
            setattr(e, "failed_part", failed_part)
        except (AttributeError, TypeError):
            pass
        raise DualCreatePairPartError(failed_part, e) from e
    finally:
        if first_id and not pair_completed:
            await _rollback_dual_create_first(first_id)


def _build_dual_run_preset_scenarios(
    request: DualRunPresetRequest,
) -> tuple[SimulationCreateRequest, SimulationCreateRequest, str, list[DualRunPresetWarning]]:
    """Merge base config into two scenarios with a shared batch_parent_id."""
    req_a = request.base.model_copy(deep=True)
    req_b = request.base.model_copy(deep=True)
    req_a.name = request.name_a
    req_b.name = request.name_b
    warnings: list[DualRunPresetWarning] = []
    if request.environment_type_b:
        try:
            req_b.environment_type = EnvironmentType(request.environment_type_b)
        except ValueError as e:
            logger.warning(
                "Invalid environment_type_b %r for dual-run preset; using default: %s",
                request.environment_type_b,
                e,
            )
            warnings.append(
                DualRunPresetWarning(
                    code="invalid_environment_type_b",
                    message=str(e),
                    metadata={
                        "field": "environment_type_b",
                        "value": request.environment_type_b,
                    },
                )
            )
    batch_id = uuid.uuid4().hex[:12]
    for req in (req_a, req_b):
        merged = dict(req.parameters) if isinstance(req.parameters, dict) else {}
        merged["batch_parent_id"] = batch_id
        req.parameters = merged
    return req_a, req_b, batch_id, warnings


@router.post("", response_model=SimulationState)
async def create_simulation(
    request: SimulationCreateRequest,
) -> SimulationState:
    """Create a new simulation."""
    try:
        return await _create_simulation_core(request)

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create simulation: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred while creating the simulation.",
        )


@router.post("/dual-create", response_model=DualCreateResponse)
async def dual_create_simulations(request: DualCreateRequest) -> DualCreateResponse:
    """Create two simulations; if the second fails, the first is deleted (no half-pair)."""
    try:
        return await _dual_create_pair(request)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except DualCreatePairPartError as e:
        raise HTTPException(
            status_code=500,
            detail=_dual_create_http_500_detail(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=_dual_create_http_500_detail(e),
        ) from e


_monte_carlo_runner = MonteCarloRunner(simulation_engine)
_batch_runner = BatchRunner(simulation_engine)


class PreflightResearchRequest(BaseModel):
    """Wizard preflight: research key entities before launch."""

    seed_texts: list[str] = []
    simulation_requirement: str = ""
    max_entities: int = 6


class ParseObjectiveRequest(BaseModel):
    text: str
    mode: str = "consulting"


class SuggestRosterRequest(BaseModel):
    text: str
    playbook_id: str | None = None
    ontology: dict[str, Any] | None = None


class GenerateOntologyRequest(BaseModel):
    document_excerpt: str
    simulation_requirement: str = ""
    mode: str = "consulting"


@router.post("/preflight-research")
async def preflight_research(request: PreflightResearchRequest) -> dict:
    """Stakeholder research prefetch for the new-simulation wizard."""
    packs, ok, msg = await stakeholder_research_orchestrator.run_preflight(
        seed_texts=request.seed_texts,
        simulation_requirement=request.simulation_requirement,
        max_entities=request.max_entities,
    )
    return {
        "research_enabled": ok,
        "message": msg,
        "evidence_packs": [p.model_dump() for p in packs],
    }


@router.post("/parse-objective")
async def parse_objective(request: ParseObjectiveRequest) -> dict:
    """Structured fields from natural-language simulation objective."""
    parsed = await parse_simulation_objective(request.text, mode=request.mode)
    return parsed.model_dump()


@router.post("/suggest-roster")
async def suggest_roster(request: SuggestRosterRequest) -> dict:
    """Suggest agent role counts from seed text + optional playbook."""
    return await suggest_roster_from_text(
        request.text,
        request.playbook_id,
        ontology=request.ontology,
    )


@router.post("/generate-ontology")
async def generate_ontology_endpoint(request: GenerateOntologyRequest) -> dict:
    """LLM ontology for broad-mode graph extraction."""
    onto = await generate_ontology(
        request.document_excerpt,
        request.simulation_requirement,
        mode=request.mode,
    )
    return onto.model_dump()


@router.post("/monte-carlo")
async def run_monte_carlo_sim(config: MonteCarloConfig) -> dict:
    """Monte Carlo runner (mirrors /api/analytics/simulations/monte-carlo)."""
    try:
        result = await _monte_carlo_runner.run(config)
        return result.model_dump()
    except Exception as e:
        logger.error("Monte Carlo run failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/batch")
async def run_batch_sim(config: BatchConfig) -> dict:
    """Batch scenario comparison (mirrors /api/analytics/simulations/batch)."""
    try:
        result = await _batch_runner.run_batch(config)
        return result.model_dump()
    except Exception as e:
        logger.error("Batch run failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/dual-run-preset")
async def dual_run_preset(request: DualRunPresetRequest) -> dict:
    """Build two simulation create payloads (JSON preview); does not persist."""
    req_a, req_b, batch_id, warnings = _build_dual_run_preset_scenarios(request)
    return {
        "batch_parent_id": batch_id,
        "scenario_a": req_a.model_dump(mode="json"),
        "scenario_b": req_b.model_dump(mode="json"),
        "warnings": warnings,
    }


@router.post("/dual-run-preset-create", response_model=DualRunPresetCreateResponse)
async def dual_run_preset_create(
    request: DualRunPresetRequest,
) -> DualRunPresetCreateResponse:
    """Merge preset (same as /dual-run-preset) then create both via rollback-safe dual-create."""
    req_a, req_b, batch_id, warnings = _build_dual_run_preset_scenarios(request)
    dual = DualCreateRequest(scenario_a=req_a, scenario_b=req_b)
    try:
        pair = await _dual_create_pair(dual)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except DualCreatePairPartError as e:
        raise HTTPException(
            status_code=500,
            detail=_dual_create_http_500_detail(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=_dual_create_http_500_detail(e),
        ) from e
    return DualRunPresetCreateResponse(
        batch_parent_id=batch_id,
        warnings=warnings,
        simulation_a=pair.simulation_a,
        simulation_b=pair.simulation_b,
    )


@router.get("")
async def list_simulations() -> list[dict]:
    """List all simulations."""
    return await simulation_engine.list_simulations()


@router.get("/{simulation_id}", response_model=SimulationState)
async def get_simulation(simulation_id: str) -> SimulationState:
    """Get a simulation by ID."""
    sim_state = await simulation_engine.get_simulation(simulation_id)
    if not sim_state:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return sim_state


@router.post("/{simulation_id}/start")
async def start_simulation(simulation_id: str) -> dict:
    """Start or resume a simulation."""
    sim_state = await simulation_engine.get_simulation(simulation_id)
    if not sim_state:
        raise HTTPException(status_code=404, detail="Simulation not found")

    if sim_state.status.value == "running":
        raise HTTPException(status_code=400, detail="Simulation already running")

    previous_status = sim_state.status

    # Define message callback for WebSocket updates
    async def on_message(message: SimulationMessage):
        await manager.broadcast(message.model_dump(), simulation_id)

    # Start simulation in background with proper tracking; only mark RUNNING
    # after asyncio.create_task succeeds so we do not leave a stuck RUNNING state.
    try:
        task = asyncio.create_task(
            simulation_engine.run_simulation(simulation_id, on_message=on_message),
            name=f"simulation-{simulation_id}",
        )
        task.add_done_callback(lambda t: _on_simulation_done(simulation_id, t))
        _background_tasks[simulation_id] = task
        sim_state.status = SimulationStatus.RUNNING
    except Exception as e:
        logger.error(
            "Failed to schedule simulation task for %s: %s",
            simulation_id,
            e,
            exc_info=True,
        )
        sim_state.status = previous_status
        raise HTTPException(
            status_code=500,
            detail="Failed to start simulation background task.",
        ) from e

    return {"status": "started", "simulation_id": simulation_id}


@router.post("/{simulation_id}/pause")
async def pause_simulation(simulation_id: str) -> dict:
    """Pause a running simulation."""
    sim_state = await simulation_engine.get_simulation(simulation_id)
    if not sim_state:
        raise HTTPException(status_code=404, detail="Simulation not found")

    await simulation_engine.pause_simulation(simulation_id)
    return {"status": "paused", "simulation_id": simulation_id}


@router.post("/{simulation_id}/resume")
async def resume_simulation(simulation_id: str) -> dict:
    """Resume a paused simulation."""
    sim_state = await simulation_engine.get_simulation(simulation_id)
    if not sim_state:
        raise HTTPException(status_code=404, detail="Simulation not found")

    if sim_state.status.value != "paused":
        raise HTTPException(status_code=400, detail="Simulation is not paused")

    previous_status = sim_state.status

    # Define message callback for WebSocket updates
    async def on_message(message: SimulationMessage):
        await manager.broadcast(message.model_dump(), simulation_id)

    try:
        task = asyncio.create_task(
            simulation_engine.run_simulation(simulation_id, on_message=on_message),
            name=f"simulation-{simulation_id}",
        )
        task.add_done_callback(lambda t: _on_simulation_done(simulation_id, t))
        _background_tasks[simulation_id] = task
        sim_state.status = SimulationStatus.RUNNING
    except Exception as e:
        logger.error(
            "Failed to schedule simulation resume task for %s: %s",
            simulation_id,
            e,
            exc_info=True,
        )
        sim_state.status = previous_status
        raise HTTPException(
            status_code=500,
            detail="Failed to resume simulation background task.",
        ) from e

    return {"status": "resumed", "simulation_id": simulation_id}


@router.get("/{simulation_id}/messages")
async def get_simulation_messages(
    simulation_id: str,
    round_number: int | None = None,
    phase: str | None = None,
) -> list[dict]:
    """Get simulation messages with optional filters."""
    sim_state = await simulation_engine.get_simulation(simulation_id)
    if not sim_state:
        raise HTTPException(status_code=404, detail="Simulation not found")

    messages = []
    for round_state in sim_state.rounds:
        if round_number is not None and round_state.round_number != round_number:
            continue

        for msg in round_state.messages:
            if phase is not None and msg.phase != phase:
                continue
            messages.append(msg.model_dump())

    return messages


@router.post("/{simulation_id}/stop")
async def stop_simulation(simulation_id: str) -> dict:
    """Stop: mark cancelled (user abort); preserves partial rounds (does not delete)."""
    sim_state = await simulation_engine.get_simulation(simulation_id)
    if not sim_state:
        raise HTTPException(status_code=404, detail="Simulation not found")

    success = True
    if simulation_id in _background_tasks:
        task = _background_tasks[simulation_id]
        task.cancel()
        deferred_exc: HTTPException | None = None
        try:
            await task
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error cancelling task for {simulation_id}: {e}")
            deferred_exc = HTTPException(
                status_code=500,
                detail="Failed to cancel simulation task",
            )
        else:
            # Race: task in _background_tasks may finish between task.cancel() and await task.
            logger.info(
                "stop_simulation: await on task %r for simulation_id=%s returned without "
                "CancelledError after task.cancel() — background task completed before "
                "cancellation was observed; continuing with "
                "simulation_engine.stop_simulation(%s) and _background_tasks.pop",
                task,
                simulation_id,
                simulation_id,
            )
        finally:
            stop_exc: Exception | None = None
            try:
                success = await simulation_engine.stop_simulation(simulation_id)
            except Exception as e:
                stop_exc = e
                success = False
            _background_tasks.pop(simulation_id, None)
        if deferred_exc is not None and stop_exc is not None:
            raise deferred_exc from stop_exc
        if stop_exc is not None:
            raise stop_exc
        if deferred_exc is not None:
            raise deferred_exc
    else:
        success = await simulation_engine.stop_simulation(simulation_id)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to stop simulation")

    final = await simulation_engine.get_simulation(simulation_id)
    out_status = final.status.value if final else "unknown"
    return {"status": out_status, "simulation_id": simulation_id}


@router.delete("/{simulation_id}")
async def delete_simulation(simulation_id: str) -> dict:
    """Delete a simulation."""
    success = await simulation_engine.delete_simulation(simulation_id)
    if not success:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return {"status": "deleted", "simulation_id": simulation_id}


@router.get("/{simulation_id}/agents")
async def get_simulation_agents(simulation_id: str):
    """Get list of agents in a simulation.

    Args:
        simulation_id: The ID of the simulation

    Returns:
        List of agents with their id, name, role, and archetype

    Raises:
        HTTPException: If simulation not found
    """
    sim_state = await simulation_engine.get_simulation(simulation_id)
    if not sim_state:
        raise HTTPException(status_code=404, detail="Simulation not found")

    agents = []
    for agent in sim_state.agents:
        # `name` is the display label; `role` must be the archetype role (picker subtitle),
        # not a duplicate of `name` (config.name was incorrectly used here).
        arch = get_archetype(agent.archetype_id)
        role_label = arch.role if arch is not None else agent.archetype_id.replace("_", " ").title()
        agents.append(
            {
                "id": agent.id,
                "name": agent.name,
                "role": role_label,
                "archetype": agent.archetype_id,
            }
        )
    return agents


@router.get(
    "/{simulation_id}/chat",
    response_model=list[ChatHistoryMessage],
)
async def get_chat_history(simulation_id: str) -> list[ChatHistoryMessage]:
    """Return persisted chat history for a simulation."""
    sim_state = await simulation_engine.get_simulation(simulation_id)
    if not sim_state:
        raise HTTPException(status_code=404, detail="Simulation not found")

    try:
        db_history = await _chat_repo.get_history(simulation_id)
    except Exception as e:
        logger.warning(f"Failed to load chat history from DB: {e}")
        db_history = []

    messages: list[ChatHistoryMessage] = []
    for exchange in db_history:
        user_id = f"{exchange['id']}:user"
        assistant_id = f"{exchange['id']}:assistant"
        messages.append(
            ChatHistoryMessage(
                id=user_id,
                simulation_id=simulation_id,
                content=exchange["user_message"],
                timestamp=exchange["timestamp"],
                is_user=True,
            )
        )
        messages.append(
            ChatHistoryMessage(
                id=assistant_id,
                simulation_id=simulation_id,
                agent_id=exchange["agent_id"],
                agent_name=exchange.get("agent_name"),
                content=exchange["agent_response"],
                timestamp=exchange["timestamp"],
                is_user=False,
            )
        )

    return messages


@router.post("/{simulation_id}/chat", response_model=ChatResponse)
async def send_chat_message(
    simulation_id: str,
    request: ChatRequest,
) -> ChatResponse:
    """Send a chat message to an agent.

    Args:
        simulation_id: The ID of the simulation
        request: Chat request with agent_id and message

    Returns:
        Chat response from the agent

    Raises:
        HTTPException: If simulation or agent not found
    """
    sim_state = await simulation_engine.get_simulation(simulation_id)
    if not sim_state:
        raise HTTPException(status_code=404, detail="Simulation not found")

    # Find the agent
    agent = None
    for a in sim_state.agents:
        agent_id = a.get("id") if isinstance(a, dict) else getattr(a, "id", None)
        if agent_id == request.agent_id:
            agent = a
            break

    if not agent:
        raise HTTPException(
            status_code=404,
            detail=f"Agent not found: {request.agent_id}",
        )

    # Get or initialize chat history (try DB first)
    if simulation_id not in _chat_histories:
        try:
            db_history = await _chat_repo.get_history(simulation_id)
            if db_history:
                # Interleave user/assistant per exchange (same order as append on POST)
                _chat_histories[simulation_id] = flatten_chat_exchanges_to_session_messages(db_history)
            else:
                _chat_histories[simulation_id] = []
        except Exception as e:
            logger.warning(f"Failed to load chat history from DB: {e}")
            _chat_histories[simulation_id] = []

    chat_history = _chat_histories[simulation_id]

    agent_name = _agent_value(agent, "name", "Agent")
    agent_archetype = _agent_value(agent, "archetype_id", "stakeholder")
    agent_persona = _agent_value(agent, "persona_prompt", "")
    agent_stance = _agent_value(agent, "current_stance", "Not determined")

    # Build context for the agent
    system_prompt = f"""You are {agent_name}, a {agent_archetype} archetype.

Your persona:
{agent_persona}

You are participating in a post-simulation discussion.
Answer the user's questions about the simulation and
your perspective on what happened.

Your current stance: {agent_stance}"""

    # Build messages for LLM
    messages: list[LLMMessage] = [LLMMessage(role="system", content=system_prompt)]

    # Add recent chat history (last 10 messages)
    recent_history = chat_history[-10:] if chat_history else []
    for msg in recent_history:
        role = "user" if msg.get("is_user") else "assistant"
        messages.append(LLMMessage(role=role, content=msg["content"]))

    # Add current message
    messages.append(LLMMessage(role="user", content=request.message))

    # Get LLM response
    try:
        llm = get_llm_provider()
        response = await llm.generate(messages)
        response_text = response.content or "I apologize, I couldn't generate a response."
    except Exception as e:
        logger.error(f"Failed to generate chat response: {e}")
        response_text = "I couldn't generate a response just now. " "Please try again in a moment."

    # Store in chat history (in-memory)
    timestamp = datetime.now(timezone.utc).isoformat()
    chat_history.append(
        {
            "is_user": True,
            "content": request.message,
            "timestamp": timestamp,
        }
    )
    chat_history.append(
        {
            "is_user": False,
            "content": response_text,
            "agent_id": request.agent_id,
            "agent_name": agent_name,
            "timestamp": timestamp,
        }
    )

    # Persist to DB
    try:
        await _chat_repo.save_message(
            simulation_id=simulation_id,
            agent_id=request.agent_id,
            agent_name=agent_name,
            user_message=request.message,
            agent_response=response_text,
            timestamp=timestamp,
        )
    except Exception as e:
        logger.warning(f"Failed to save chat history to DB: {e}")

    return ChatResponse(
        agent_id=request.agent_id,
        agent_name=agent_name,
        response=response_text,
        timestamp=timestamp,
    )


# WebSocket endpoint
@router.websocket("/ws/{simulation_id}")
async def simulation_websocket(websocket: WebSocket, simulation_id: str):
    """WebSocket for real-time simulation updates."""
    await manager.connect(websocket, simulation_id)

    try:
        while True:
            # Keep connection alive and handle client messages
            data = await websocket.receive_json()

            # Handle client commands
            if data.get("action") == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(websocket, simulation_id)
    except Exception as e:
        logger.error(f"WebSocket error for {simulation_id}: {e}")
        manager.disconnect(websocket, simulation_id)
