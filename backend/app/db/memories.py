"""Agent memory repository.

CRUD operations for the ``agent_memories`` table.
"""

import logging
import uuid

from app.db.connection import get_db

logger = logging.getLogger(__name__)


class AgentMemoryRepository:
    """CRUD operations for agent memory persistence."""

    async def save_memory(
        self,
        simulation_id: str,
        agent_id: str,
        round_number: int,
        content: str,
        memory_type: str,
        timestamp: str,
    ) -> str:
        """Save an agent memory. Returns the memory ID."""
        db = await get_db()
        memory_id = str(uuid.uuid4())
        await db.execute(
            """
            INSERT INTO agent_memories
                (id, simulation_id, agent_id, round_number, content,
                 memory_type, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                memory_id,
                simulation_id,
                agent_id,
                round_number,
                content,
                memory_type,
                timestamp,
            ),
        )
        await db.commit()
        return memory_id

    async def get_memories(
        self,
        simulation_id: str,
        agent_id: str,
        limit: int = 10,
    ) -> list[dict]:
        """Retrieve memories for an agent in a simulation."""
        db = await get_db()
        cursor = await db.execute(
            "SELECT id, simulation_id, agent_id, round_number, content,"
            " memory_type, timestamp"
            " FROM agent_memories"
            " WHERE simulation_id = ? AND agent_id = ?"
            " ORDER BY timestamp DESC LIMIT ?",
            (simulation_id, agent_id, limit),
        )
        rows = await cursor.fetchall()
        return [
            {
                "id": row[0],
                "simulation_id": row[1],
                "agent_id": row[2],
                "round_number": row[3],
                "content": row[4],
                "memory_type": row[5],
                "timestamp": row[6],
            }
            for row in rows
        ]

    async def search_memories(
        self,
        simulation_id: str,
        agent_id: str,
        query: str,
        limit: int = 5,
    ) -> list[dict]:
        """Search memories by content (simple LIKE search)."""
        db = await get_db()
        cursor = await db.execute(
            "SELECT id, simulation_id, agent_id, round_number, content,"
            " memory_type, timestamp"
            " FROM agent_memories"
            " WHERE simulation_id = ? AND agent_id = ?"
            " AND content LIKE ?"
            " ORDER BY timestamp DESC LIMIT ?",
            (simulation_id, agent_id, f"%{query}%", limit),
        )
        rows = await cursor.fetchall()
        return [
            {
                "id": row[0],
                "simulation_id": row[1],
                "agent_id": row[2],
                "round_number": row[3],
                "content": row[4],
                "memory_type": row[5],
                "timestamp": row[6],
            }
            for row in rows
        ]
