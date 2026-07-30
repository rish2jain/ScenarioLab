"""Simulation state repository.

CRUD operations for the ``simulations`` table.
Connection comes from ``app.db.connection.get_db``.

Note on imports
---------------
``SimulationState`` is imported lazily inside methods to avoid a circular
import chain:
    simulations.py → app.simulation.models
    app.simulation.__init__ → engine.py
    engine.py → app.database → app.db.simulations  (cycle!)
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from app.db.connection import get_db
from app.db.connection import utc_now_iso as _utc_now_iso

if TYPE_CHECKING:
    from app.simulation.models import SimulationState

logger = logging.getLogger(__name__)


class SimulationRepository:
    """CRUD operations for simulation state persistence."""

    async def save(self, sim_state: SimulationState) -> None:
        """Upsert a simulation state into the database."""
        db = await get_db()
        now = _utc_now_iso()
        state_json = sim_state.model_dump_json()
        config_json = sim_state.config.model_dump_json()

        await db.execute(
            """
            INSERT INTO simulations
                (id, name, config, state, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                config = excluded.config,
                state = excluded.state,
                status = excluded.status,
                updated_at = excluded.updated_at
            """,
            (
                sim_state.config.id,
                sim_state.config.name,
                config_json,
                state_json,
                sim_state.status.value,
                sim_state.created_at or now,
                now,
            ),
        )
        await db.commit()

    async def get(self, simulation_id: str) -> SimulationState | None:
        """Retrieve a simulation state by ID."""
        from app.simulation.models import SimulationState as _SimulationState

        db = await get_db()
        cursor = await db.execute(
            "SELECT state FROM simulations WHERE id = ?",
            (simulation_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return _SimulationState.model_validate_json(row[0])

    async def list_all(self, *, limit: int | None = None, offset: int = 0) -> list[dict]:
        """List summary info for simulations (newest first).

        When ``limit`` is set, returns a page; otherwise returns all rows
        (legacy callers). Prefer ``list_page`` for new code.
        """
        page, _total = await self.list_page(limit=limit, offset=offset)
        return page

    async def list_page(
        self, *, limit: int | None = 50, offset: int = 0
    ) -> tuple[list[dict], int]:
        """Return ``(summaries, total_count)`` with optional LIMIT/OFFSET."""
        db = await get_db()
        count_cursor = await db.execute("SELECT COUNT(*) FROM simulations")
        count_row = await count_cursor.fetchone()
        total = int(count_row[0]) if count_row else 0

        offset = max(0, int(offset))
        sql = (
            "SELECT id, name, status, config, state, created_at, updated_at "
            "FROM simulations ORDER BY updated_at DESC"
        )
        params: list[object] = []
        if limit is not None:
            limit = max(1, min(int(limit), 200))
            sql += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])

        cursor = await db.execute(sql, params)
        rows = await cursor.fetchall()
        summaries: list[dict] = []
        for row in rows:
            config = json.loads(row[3])
            state_raw = row[4]
            try:
                state = json.loads(state_raw) if state_raw else {}
            except json.JSONDecodeError:
                logger.warning("Invalid state JSON for simulation %s", row[0])
                state = {}
            current_round = int(state.get("current_round", 0) or 0)
            total_rounds = int(config.get("total_rounds", 0) or 0)
            summaries.append(
                {
                    "id": row[0],
                    "name": row[1],
                    "status": row[2],
                    "environment_type": config.get("environment_type", ""),
                    "current_round": current_round,
                    "total_rounds": total_rounds,
                    "agent_count": len(config.get("agents", [])),
                    "created_at": row[5],
                    "updated_at": row[6],
                }
            )
        return summaries, total

    async def delete(self, simulation_id: str) -> bool:
        """Delete a simulation by ID. Returns True if a row was deleted."""
        db = await get_db()
        cursor = await db.execute(
            "DELETE FROM simulations WHERE id = ?",
            (simulation_id,),
        )
        await db.commit()
        return cursor.rowcount > 0

    async def update_status(self, simulation_id: str, status: str) -> None:
        """Quick status update: status column and state JSON."""
        db = await get_db()
        now = _utc_now_iso()
        await db.execute(
            """
            UPDATE simulations
            SET status = ?,
                state = json_set(state, '$.status', ?),
                updated_at = ?
            WHERE id = ?
            """,
            (status, status, now, simulation_id),
        )
        await db.commit()
