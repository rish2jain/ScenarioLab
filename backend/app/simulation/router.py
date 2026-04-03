"""FastAPI router for simulation endpoints and WebSocket."""

import asyncio
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.database import ChatHistoryRepository
from app.llm.factory import get_llm_provider
from app.simulation.engine import simulation_engine
from app.simulation.models import (
    SimulationConfig,
    SimulationCreateRequest,
    SimulationMessage,
    SimulationState,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/simulations", tags=["simulations"])


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


@router.post("", response_model=SimulationState)
async def create_simulation(
    request: SimulationCreateRequest,
) -> SimulationState:
    """Create a new simulation."""
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
        return sim_state

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create simulation: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred while creating the simulation.",
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
        raise HTTPException(
            status_code=400, detail="Simulation already running"
        )

    # Define message callback for WebSocket updates
    async def on_message(message: SimulationMessage):
        await manager.broadcast(message.model_dump(), simulation_id)

    # Start simulation in background with proper tracking
    task = asyncio.create_task(
        simulation_engine.run_simulation(simulation_id, on_message=on_message),
        name=f"simulation-{simulation_id}",
    )
    task.add_done_callback(
        lambda t: _on_simulation_done(simulation_id, t)
    )
    _background_tasks[simulation_id] = task

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

    # Define message callback for WebSocket updates
    async def on_message(message: SimulationMessage):
        await manager.broadcast(message.model_dump(), simulation_id)

    # Resume simulation in background with proper tracking
    task = asyncio.create_task(
        simulation_engine.run_simulation(simulation_id, on_message=on_message),
        name=f"simulation-{simulation_id}",
    )
    task.add_done_callback(
        lambda t: _on_simulation_done(simulation_id, t)
    )
    _background_tasks[simulation_id] = task

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
        if (round_number is not None
                and round_state.round_number != round_number):
            continue

        for msg in round_state.messages:
            if phase is not None and msg.phase != phase:
                continue
            messages.append(msg.model_dump())

    return messages


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

    agents = [
        {
            "id": agent.id,
            "name": agent.name,
            "role": sim_state.config.environment_type.value,
            "archetype": agent.archetype_id,
        }
        for agent in sim_state.agents
    ]
    return agents


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
        if a.id == request.agent_id:
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
                # Convert DB history to in-memory format
                _chat_histories[simulation_id] = [
                    {"is_user": True, "content": h["user_message"],
                     "timestamp": h["timestamp"]}
                    for h in db_history
                ]
                # Add agent responses
                for h in db_history:
                    _chat_histories[simulation_id].append({
                        "is_user": False,
                        "content": h["agent_response"],
                        "agent_id": h["agent_id"],
                        "agent_name": h.get("agent_name"),
                        "timestamp": h["timestamp"],
                    })
            else:
                _chat_histories[simulation_id] = []
        except Exception as e:
            logger.warning(f"Failed to load chat history from DB: {e}")
            _chat_histories[simulation_id] = []

    chat_history = _chat_histories[simulation_id]

    # Build context for the agent
    system_prompt = f"""You are {agent.name}, a {agent.archetype_id} archetype.

Your persona:
{agent.persona_prompt}

You are participating in a post-simulation discussion.
Answer the user's questions about the simulation and
your perspective on what happened.

Your current stance: {agent.current_stance or 'Not determined'}"""

    # Build messages for LLM
    messages = [{"role": "system", "content": system_prompt}]

    # Add recent chat history (last 10 messages)
    recent_history = chat_history[-10:] if chat_history else []
    for msg in recent_history:
        if msg.get("is_user"):
            messages.append({"role": "user", "content": msg["content"]})
        else:
            messages.append({"role": "assistant", "content": msg["content"]})

    # Add current message
    messages.append({"role": "user", "content": request.message})

    # Get LLM response
    try:
        llm = get_llm_provider()
        response = await llm.generate(messages)
        response_text = response.get(
            "content", "I apologize, I couldn't generate a response."
        )
    except Exception as e:
        logger.error(f"Failed to generate chat response: {e}")
        response_text = f"I apologize, but I encountered an error: {str(e)}"

    # Store in chat history (in-memory)
    timestamp = datetime.now(timezone.utc).isoformat()
    chat_history.append({
        "is_user": True,
        "content": request.message,
        "timestamp": timestamp,
    })
    chat_history.append({
        "is_user": False,
        "content": response_text,
        "agent_id": agent.id,
        "agent_name": agent.name,
        "timestamp": timestamp,
    })

    # Persist to DB
    try:
        await _chat_repo.save_message(
            simulation_id=simulation_id,
            agent_id=agent.id,
            agent_name=agent.name,
            user_message=request.message,
            agent_response=response_text,
            timestamp=timestamp,
        )
    except Exception as e:
        logger.warning(f"Failed to save chat history to DB: {e}")

    return ChatResponse(
        agent_id=agent.id,
        agent_name=agent.name,
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
