"""Simulation-level memory coordination."""

import logging
from datetime import datetime, timezone

from app.database import AgentMemoryRepository
from app.simulation.models import RoundState, SimulationMessage

logger = logging.getLogger(__name__)


class SimulationMemoryManager:
    """Coordinates memory for all agents in a simulation."""

    def __init__(self, graph_memory_manager=None):
        self.graph_memory = graph_memory_manager
        self._local_memories: dict[str, list] = {}  # Fallback if no Neo4j
        self._memory_repo = AgentMemoryRepository()

    async def record_round(
        self,
        simulation_id: str,
        round_state: RoundState,
        agents: list,
    ):
        """Record memories from a completed round for all agents."""
        for agent in agents:
            try:
                # Build memory content from what this agent observed
                observed_messages = self._get_observed_messages(
                    agent, round_state.messages
                )

                if not observed_messages:
                    continue

                memory_content = self._format_memory(
                    round_state.round_number,
                    round_state.phase,
                    observed_messages,
                )

                # Store via agent's memory system or fallback
                await self._store_agent_memory(
                    agent=agent,
                    simulation_id=simulation_id,
                    round_number=round_state.round_number,
                    content=memory_content,
                    memory_type="observation",
                )

            except Exception as e:
                logger.error(
                    f"Failed to record memory for agent {agent.name}: {e}"
                )

    def _get_observed_messages(
        self,
        agent,
        messages: list[SimulationMessage],
    ) -> list[SimulationMessage]:
        """Get messages observed by an agent."""
        observed = []
        for msg in messages:
            # Agent sees their own messages
            if msg.agent_id == agent.id:
                observed.append(msg)
                continue

            # Public messages
            if msg.visibility == "public":
                observed.append(msg)
                continue

            # Private messages to this agent
            if msg.visibility == "private" and agent.id in msg.target_agents:
                observed.append(msg)
                continue

            # Coalition messages
            if msg.visibility == "coalition":
                if msg.agent_id in agent.state.coalition_members:
                    observed.append(msg)
                    continue

        return observed

    def _format_memory(
        self,
        round_number: int,
        phase: str,
        messages: list[SimulationMessage],
    ) -> str:
        """Format observed messages into a memory string."""
        parts = [f"Round {round_number}, Phase: {phase}"]

        for msg in messages:
            parts.append(f"- {msg.agent_name}: {msg.content[:150]}")

        return "\n".join(parts)

    async def _store_agent_memory(
        self,
        agent,
        simulation_id: str,
        round_number: int,
        content: str,
        memory_type: str,
    ):
        """Store memory for an agent (via their memory or fallback)."""
        # Try agent's memory manager first
        if agent.memory:
            try:
                await agent.store_memory(
                    simulation_id=simulation_id,
                    round_number=round_number,
                    content=content,
                    memory_type=memory_type,
                )
                return
            except Exception as e:
                logger.warning(f"Agent memory failed, using fallback: {e}")

        # Fallback to local in-memory storage
        await self._store_local_memory(
            agent_id=agent.id,
            simulation_id=simulation_id,
            round_number=round_number,
            content=content,
            memory_type=memory_type,
        )

    async def _store_local_memory(
        self,
        agent_id: str,
        simulation_id: str,
        round_number: int,
        content: str,
        memory_type: str,
    ):
        """Store memory in local fallback storage with SQLite persistence."""
        key = f"{simulation_id}:{agent_id}"
        timestamp = datetime.now(timezone.utc).isoformat()

        memory_entry = {
            "simulation_id": simulation_id,
            "agent_id": agent_id,
            "round_number": round_number,
            "content": content,
            "memory_type": memory_type,
            "timestamp": timestamp,
        }

        if key not in self._local_memories:
            self._local_memories[key] = []

        self._local_memories[key].append(memory_entry)

        # Persist to SQLite
        try:
            await self._memory_repo.save_memory(
                simulation_id=simulation_id,
                agent_id=agent_id,
                round_number=round_number,
                content=content,
                memory_type=memory_type,
                timestamp=timestamp,
            )
        except Exception as e:
            logger.warning(f"Failed to save memory to DB: {e}")

        logger.debug(f"Stored local memory for agent {agent_id}")

    async def get_agent_context(
        self,
        agent_id: str,
        simulation_id: str,
        current_round: int,
    ) -> str:
        """Build context string from agent's memories for LLM prompt."""
        # Try to get from graph memory first
        if self.graph_memory:
            try:
                memories = await self.graph_memory.get_recent_memories(
                    agent_id=agent_id,
                    simulation_id=simulation_id,
                    rounds=3,
                )

                if memories:
                    context_parts = ["RECENT MEMORIES:"]
                    for mem in memories[:5]:  # Last 5 memories
                        context_parts.append(
                            f"- Round {mem.round_number}: {mem.content[:200]}"
                        )
                    return "\n".join(context_parts)

            except Exception as e:
                logger.warning(f"Graph memory failed, using fallback: {e}")

        # Fallback to local memories
        return await self._get_local_context(
            agent_id, simulation_id, current_round
        )

    async def _get_local_context(
        self,
        agent_id: str,
        simulation_id: str,
        current_round: int,
    ) -> str:
        """Get context from local fallback storage with DB fallback."""
        key = f"{simulation_id}:{agent_id}"
        memories = self._local_memories.get(key, [])

        # Try loading from DB if not in memory
        if not memories:
            try:
                db_memories = await self._memory_repo.get_memories(
                    simulation_id, agent_id, limit=10
                )
                if db_memories:
                    memories = db_memories
                    self._local_memories[key] = memories  # Cache
            except Exception as e:
                logger.warning(f"Failed to load memories from DB: {e}")

        if not memories:
            return ""

        # Get recent memories (last 3 rounds)
        recent = [
            m for m in memories
            if m.get("round_number", 0) >= current_round - 3
        ]

        if not recent:
            return ""

        context_parts = ["RECENT MEMORIES:"]
        for mem in recent[-5:]:  # Last 5 memories
            context_parts.append(
                f"- Round {mem['round_number']}: {mem['content'][:200]}"
            )

        return "\n".join(context_parts)

    async def clear_memories(self, simulation_id: str):
        """Clear all memories for a simulation."""
        # Clear local memories
        keys_to_remove = [
            key for key in self._local_memories.keys()
            if key.startswith(f"{simulation_id}:")
        ]
        for key in keys_to_remove:
            del self._local_memories[key]

        logger.info(f"Cleared memories for simulation {simulation_id}")
