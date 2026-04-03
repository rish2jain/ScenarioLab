"""Annotations repository.

CRUD operations for the ``annotations`` table.
"""

import logging

from app.db.connection import get_db

logger = logging.getLogger(__name__)


class AnnotationRepository:
    """CRUD operations for annotation persistence."""

    async def save_annotation(self, annotation: dict) -> None:
        """Upsert an annotation to the database."""
        db = await get_db()
        await db.execute(
            """
            INSERT INTO annotations
                (id, simulation_id, agent_id, message_id, round_number,
                 content, tag, annotator, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                agent_id = excluded.agent_id,
                message_id = excluded.message_id,
                round_number = excluded.round_number,
                content = excluded.content,
                tag = excluded.tag,
                annotator = excluded.annotator
            """,
            (
                annotation["id"],
                annotation["simulation_id"],
                annotation.get("agent_id"),
                annotation.get("message_id"),
                annotation.get("round_number"),
                annotation["content"],
                annotation["tag"],
                annotation["annotator"],
                annotation["timestamp"],
            ),
        )
        await db.commit()

    async def get_annotations(
        self,
        simulation_id: str,
        tag: str | None = None,
        annotator: str | None = None,
        round_num: int | None = None,
    ) -> list[dict]:
        """Retrieve annotations for a simulation with optional filters."""
        db = await get_db()
        query = (
            "SELECT id, simulation_id, agent_id, message_id, round_number,"
            " content, tag, annotator, timestamp"
            " FROM annotations WHERE simulation_id = ?"
        )
        params: list = [simulation_id]

        if tag:
            query += " AND tag = ?"
            params.append(tag)
        if annotator:
            query += " AND annotator = ?"
            params.append(annotator)
        if round_num is not None:
            query += " AND round_number = ?"
            params.append(round_num)

        query += " ORDER BY timestamp DESC"

        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        return [
            {
                "id": row[0],
                "simulation_id": row[1],
                "agent_id": row[2],
                "message_id": row[3],
                "round_number": row[4],
                "content": row[5],
                "tag": row[6],
                "annotator": row[7],
                "timestamp": row[8],
            }
            for row in rows
        ]

    async def delete_annotation(self, annotation_id: str) -> bool:
        """Delete an annotation by ID."""
        db = await get_db()
        cursor = await db.execute(
            "DELETE FROM annotations WHERE id = ?",
            (annotation_id,),
        )
        await db.commit()
        return cursor.rowcount > 0

    async def export_annotations(self, simulation_id: str) -> list[dict]:
        """Export all annotations for a simulation."""
        return await self.get_annotations(simulation_id)
