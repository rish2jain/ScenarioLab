"""Audit trail repository.

Immutable audit event persistence with hash-chain integrity verification.
"""

import json
import logging

from app.db.connection import get_db

logger = logging.getLogger(__name__)


class AuditTrailRepository:
    """CRUD operations for audit trail persistence."""

    async def save_event(self, event: dict) -> None:
        """Save an audit event to the database."""
        db = await get_db()
        await db.execute(
            """
            INSERT INTO audit_events
                (event_id, simulation_id, event_type, timestamp,
                 actor, details, previous_hash, hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event["event_id"],
                event["simulation_id"],
                event["event_type"],
                event["timestamp"],
                event["actor"],
                json.dumps(event.get("details", {})),
                event["previous_hash"],
                event["hash"],
            ),
        )
        await db.commit()

    async def get_events(self, simulation_id: str) -> list[dict]:
        """Retrieve all events for a simulation, ordered by timestamp."""
        db = await get_db()
        cursor = await db.execute(
            "SELECT event_id, simulation_id, event_type, timestamp,"
            " actor, details, previous_hash, hash"
            " FROM audit_events WHERE simulation_id = ?"
            " ORDER BY timestamp ASC",
            (simulation_id,),
        )
        rows = await cursor.fetchall()
        return [
            {
                "event_id": row[0],
                "simulation_id": row[1],
                "event_type": row[2],
                "timestamp": row[3],
                "actor": row[4],
                "details": json.loads(row[5]) if row[5] else {},
                "previous_hash": row[6],
                "hash": row[7],
            }
            for row in rows
        ]

    async def verify_integrity(self, simulation_id: str) -> tuple[bool, str]:
        """Verify hash chain integrity for a simulation's audit trail."""
        events = await self.get_events(simulation_id)
        if not events:
            return True, "No events to verify"

        genesis_hash = "0" * 64
        expected_previous = genesis_hash

        for i, event in enumerate(events):
            if event["previous_hash"] != expected_previous:
                return False, (
                    f"Hash chain broken at event {i}: "
                    f"expected previous_hash={expected_previous[:16]}..., "
                    f"got {event['previous_hash'][:16]}..."
                )
            expected_previous = event["hash"]

        return True, f"Verified {len(events)} events successfully"

    async def export_events(self, simulation_id: str) -> list[dict]:
        """Export all events for a simulation."""
        return await self.get_events(simulation_id)
