"""Chat history repository.

CRUD operations for the ``chat_history`` table.
"""

import logging
import uuid

from app.db.connection import get_db

logger = logging.getLogger(__name__)


class ChatHistoryRepository:
    """CRUD operations for chat history persistence."""

    async def save_message(
        self,
        simulation_id: str,
        agent_id: str,
        agent_name: str | None,
        user_message: str,
        agent_response: str,
        timestamp: str,
    ) -> str:
        """Save a chat message exchange. Returns the message ID."""
        db = await get_db()
        msg_id = str(uuid.uuid4())
        await db.execute(
            """
            INSERT INTO chat_history
                (id, simulation_id, agent_id, agent_name, user_message,
                 agent_response, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                msg_id,
                simulation_id,
                agent_id,
                agent_name,
                user_message,
                agent_response,
                timestamp,
            ),
        )
        await db.commit()
        return msg_id

    async def get_history(self, simulation_id: str) -> list[dict]:
        """Retrieve chat history for a simulation."""
        db = await get_db()
        cursor = await db.execute(
            "SELECT id, simulation_id, agent_id, agent_name, user_message,"
            " agent_response, timestamp"
            " FROM chat_history WHERE simulation_id = ?"
            " ORDER BY timestamp ASC",
            (simulation_id,),
        )
        rows = await cursor.fetchall()
        return [
            {
                "id": row[0],
                "simulation_id": row[1],
                "agent_id": row[2],
                "agent_name": row[3],
                "user_message": row[4],
                "agent_response": row[5],
                "timestamp": row[6],
            }
            for row in rows
        ]

    async def clear_history(self, simulation_id: str) -> int:
        """Clear chat history for a simulation. Returns count deleted."""
        db = await get_db()
        cursor = await db.execute(
            "SELECT COUNT(*) FROM chat_history WHERE simulation_id = ?",
            (simulation_id,),
        )
        row = await cursor.fetchone()
        count = row[0] if row else 0

        await db.execute(
            "DELETE FROM chat_history WHERE simulation_id = ?",
            (simulation_id,),
        )
        await db.commit()
        return count
