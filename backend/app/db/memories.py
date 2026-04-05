"""Agent memory repository.

CRUD operations for the ``agent_memories`` table.
"""

import uuid
from typing import Any, Sequence

from app.db.connection import get_db


def _row_to_memory_dict(row: Sequence[Any]) -> dict[str, Any]:
    """Convert a DB row from ``agent_memories`` to a plain dict.

    Centralises the field mapping used by both :meth:`get_memories` and
    :meth:`search_memories` to avoid duplication.
    """
    return {
        "id": row[0],
        "simulation_id": row[1],
        "agent_id": row[2],
        "round_number": row[3],
        "content": row[4],
        "memory_type": row[5],
        "timestamp": row[6],
    }


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
        return [_row_to_memory_dict(row) for row in rows]

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
        return [_row_to_memory_dict(row) for row in rows]
