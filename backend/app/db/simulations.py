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

from app.db.connection import get_db, utc_now_iso as _utc_now_iso

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

    async def list_all(self) -> list[dict]:
        """List summary info for all simulations."""
        db = await get_db()
        cursor = await db.execute(
            "SELECT id, name, status, config, created_at, updated_at FROM simulations"
            " ORDER BY updated_at DESC"
        )
        rows = await cursor.fetchall()
        summaries: list[dict] = []
        for row in rows:
            config = json.loads(row[3])
            summaries.append(
                {
                    "id": row[0],
                    "name": row[1],
                    "status": row[2],
                    "environment_type": config.get("environment_type", ""),
                    "current_round": config.get("total_rounds", 0),
                    "total_rounds": config.get("total_rounds", 0),
                    "agent_count": len(config.get("agents", [])),
                    "created_at": row[4],
                    "updated_at": row[5],
                }
            )
        return summaries

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
        """Quick status update — updates both the status column and the state JSON."""
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
