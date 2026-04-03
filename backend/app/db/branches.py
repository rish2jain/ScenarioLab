"""Scenario branch repository.

CRUD operations for the ``scenario_branches`` table.
"""

import json
import logging

from app.db.connection import get_db

logger = logging.getLogger(__name__)


class BranchRepository:
    """CRUD operations for scenario branch persistence."""

    async def save_branch(self, branch: dict) -> None:
        """Upsert a scenario branch to the database."""
        db = await get_db()
        await db.execute(
            """
            INSERT INTO scenario_branches
                (branch_id, root_id, parent_id, name, description,
                 config_diff, simulation_id, created_at, creator)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(branch_id) DO UPDATE SET
                root_id = excluded.root_id,
                parent_id = excluded.parent_id,
                name = excluded.name,
                description = excluded.description,
                config_diff = excluded.config_diff,
                simulation_id = excluded.simulation_id,
                creator = excluded.creator
            """,
            (
                branch["id"],
                branch["root_id"],
                branch.get("parent_id"),
                branch["name"],
                branch.get("description"),
                json.dumps(branch.get("config_diff", {})),
                branch.get("simulation_id"),
                branch["created_at"],
                branch.get("creator"),
            ),
        )
        await db.commit()

    async def get_branch(self, branch_id: str) -> dict | None:
        """Retrieve a branch by ID."""
        db = await get_db()
        cursor = await db.execute(
            "SELECT branch_id, root_id, parent_id, name, description,"
            " config_diff, simulation_id, created_at, creator"
            " FROM scenario_branches WHERE branch_id = ?",
            (branch_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return self._row_to_dict(row)

    async def get_branches_by_root(self, root_id: str) -> list[dict]:
        """Retrieve all branches for a root scenario."""
        db = await get_db()
        cursor = await db.execute(
            "SELECT branch_id, root_id, parent_id, name, description,"
            " config_diff, simulation_id, created_at, creator"
            " FROM scenario_branches WHERE root_id = ?",
            (root_id,),
        )
        rows = await cursor.fetchall()
        return [self._row_to_dict(row) for row in rows]

    async def delete_branch(self, branch_id: str) -> bool:
        """Delete a branch by ID."""
        db = await get_db()
        cursor = await db.execute(
            "DELETE FROM scenario_branches WHERE branch_id = ?",
            (branch_id,),
        )
        await db.commit()
        return cursor.rowcount > 0

    def _row_to_dict(self, row: object) -> dict:
        return {
            "id": row[0],
            "root_id": row[1],
            "parent_id": row[2],
            "name": row[3],
            "description": row[4],
            "config_diff": json.loads(row[5]) if row[5] else {},
            "simulation_id": row[6],
            "created_at": row[7],
            "creator": row[8],
        }
