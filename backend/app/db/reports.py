"""Repository for persisting simulation reports to SQLite."""

import json
import logging
from datetime import datetime, timezone

from app.db.connection import get_db

logger = logging.getLogger(__name__)


class ReportRepository:
    """CRUD operations for persisted reports."""

    async def save(self, report_id: str, report) -> None:
        """Persist a SimulationReport (or update if exists)."""
        db = await get_db()
        now = datetime.now(timezone.utc).isoformat()
        report_json = report.model_dump_json()
        await db.execute(
            """
            INSERT INTO reports (
                id, simulation_id, simulation_name,
                status, report_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                status = excluded.status,
                report_json = excluded.report_json,
                updated_at = excluded.updated_at
            """,
            (
                report_id,
                report.simulation_id,
                report.simulation_name,
                report.status,
                report_json,
                now,
                now,
            ),
        )
        await db.commit()

    async def get(self, report_id: str) -> dict | None:
        """Load a report by ID. Returns raw dict."""
        db = await get_db()
        cursor = await db.execute(
            "SELECT report_json FROM reports WHERE id = ?",
            (report_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return json.loads(row[0])

    async def get_by_simulation(
        self,
        simulation_id: str,
    ) -> dict | None:
        """Load the most recent report for a simulation."""
        db = await get_db()
        cursor = await db.execute(
            "SELECT report_json FROM reports " "WHERE simulation_id = ? " "ORDER BY updated_at DESC LIMIT 1",
            (simulation_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return json.loads(row[0])

    async def list_all(self) -> list[dict]:
        """List all reports (metadata only, no full JSON)."""
        db = await get_db()
        cursor = await db.execute(
            "SELECT id, simulation_id, simulation_name, "
            "status, created_at, updated_at FROM reports "
            "ORDER BY updated_at DESC"
        )
        rows = await cursor.fetchall()
        return [
            {
                "id": r[0],
                "simulation_id": r[1],
                "simulation_name": r[2],
                "status": r[3],
                "created_at": r[4],
                "updated_at": r[5],
            }
            for r in rows
        ]

    async def delete(self, report_id: str) -> bool:
        """Delete a report by ID."""
        db = await get_db()
        cursor = await db.execute(
            "DELETE FROM reports WHERE id = ?",
            (report_id,),
        )
        await db.commit()
        return cursor.rowcount > 0
