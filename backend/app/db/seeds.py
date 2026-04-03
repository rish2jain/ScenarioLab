"""Seed material repository.

CRUD operations for the ``seeds`` table.

Note on imports
---------------
``SeedMaterial`` is imported lazily (inside methods or via TYPE_CHECKING) to
avoid the import chain: seeds.py → app.graph.seed_processor → neo4j
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from app.db.connection import get_db, utc_now_iso as _utc_now_iso

if TYPE_CHECKING:
    from app.graph.seed_processor import SeedMaterial

logger = logging.getLogger(__name__)


class SeedRepository:
    """CRUD operations for seed material persistence."""

    async def save(self, seed: SeedMaterial) -> None:
        """Upsert a seed material into the database."""
        db = await get_db()
        now = _utc_now_iso()
        metadata = json.dumps(
            {
                "entity_count": seed.entity_count,
                "relationship_count": seed.relationship_count,
                "error_message": seed.error_message,
            }
        )

        await db.execute(
            """
            INSERT INTO seeds
                (id, filename, content_type, raw_content,
                 processed_content, status, metadata,
                 created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                filename = excluded.filename,
                content_type = excluded.content_type,
                raw_content = excluded.raw_content,
                processed_content = excluded.processed_content,
                status = excluded.status,
                metadata = excluded.metadata,
                updated_at = excluded.updated_at
            """,
            (
                seed.id,
                seed.filename,
                seed.content_type,
                seed.raw_content,
                seed.processed_content,
                seed.status,
                metadata,
                now,
                now,
            ),
        )
        await db.commit()

    async def get(self, seed_id: str) -> SeedMaterial | None:
        """Retrieve a seed material by ID."""
        from app.graph.seed_processor import SeedMaterial as _SeedMaterial

        db = await get_db()
        cursor = await db.execute(
            "SELECT id, filename, content_type, raw_content, processed_content,"
            " status, metadata FROM seeds WHERE id = ?",
            (seed_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        metadata = json.loads(row[6]) if row[6] else {}
        return _SeedMaterial(
            id=row[0],
            filename=row[1],
            content_type=row[2],
            raw_content=row[3],
            processed_content=row[4],
            status=row[5],
            entity_count=metadata.get("entity_count", 0),
            relationship_count=metadata.get("relationship_count", 0),
            error_message=metadata.get("error_message"),
        )

    async def list_all(self) -> list[dict]:
        """List summary info for all seed materials."""
        db = await get_db()
        cursor = await db.execute(
            "SELECT id, filename, content_type, status,"
            " metadata, created_at, updated_at"
            " FROM seeds ORDER BY updated_at DESC"
        )
        rows = await cursor.fetchall()
        return [
            {
                "id": row[0],
                "filename": row[1],
                "content_type": row[2],
                "status": row[3],
                "metadata": json.loads(row[4]) if row[4] else {},
                "created_at": row[5],
                "updated_at": row[6],
            }
            for row in rows
        ]

    async def delete(self, seed_id: str) -> bool:
        """Delete a seed material by ID."""
        db = await get_db()
        cursor = await db.execute(
            "DELETE FROM seeds WHERE id = ?",
            (seed_id,),
        )
        await db.commit()
        return cursor.rowcount > 0

    async def update(self, seed_id: str, **updates: object) -> SeedMaterial | None:
        """Update specific fields on a seed material."""
        existing = await self.get(seed_id)
        if existing is None:
            return None

        for key, value in updates.items():
            if hasattr(existing, key):
                object.__setattr__(existing, key, value)

        await self.save(existing)
        return existing
