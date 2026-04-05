"""Audit trail repository.

Immutable audit event persistence with hash-chain integrity verification.
"""

import hashlib
import json
import logging

from app.db.connection import get_db

logger = logging.getLogger(__name__)

# Separates hash inputs so field boundaries cannot be confused across fields.
_AUDIT_HASH_FIELD_DELIM = "\x00"


def compute_audit_event_hash(
    *,
    previous_hash: str,
    event_id: str,
    event_type: str,
    timestamp: str,
    details: dict,
) -> str:
    """SHA-256 digest for one audit event.

    Must match ``AuditEvent._compute_hash`` in ``app.simulation.audit_trail``:
    ``SHA256`` of the UTF-8 encoding of the five fields joined by
    ``_AUDIT_HASH_FIELD_DELIM`` (``\\x00``): ``previous_hash``, ``event_id``,
    ``event_type``, ``timestamp``, and ``json(details)`` with
    ``json.dumps(..., sort_keys=True)``. The ``actor`` field is not part of
    the digest (same as runtime events).
    """
    payload = json.dumps(details or {}, sort_keys=True)
    data = _AUDIT_HASH_FIELD_DELIM.join((previous_hash, event_id, event_type, timestamp, payload))
    return hashlib.sha256(data.encode()).hexdigest()


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

    @staticmethod
    def compute_event_hash(event: dict) -> str:
        """Recompute digest for a row-shaped event dict (DB or API)."""
        et = event.get("event_type", "")
        if hasattr(et, "value"):
            et = et.value
        else:
            et = str(et)
        details = event.get("details") or {}
        if isinstance(details, str):
            details = json.loads(details) if details else {}
        return compute_audit_event_hash(
            previous_hash=event["previous_hash"],
            event_id=event["event_id"],
            event_type=et,
            timestamp=event["timestamp"],
            details=details,
        )

    async def verify_integrity(self, simulation_id: str) -> tuple[bool, str]:
        """Verify hash-chain integrity for a simulation's audit trail.

        Two checks are performed for each event in chronological order:

        1. **Hash recomputation** — the stored ``hash`` is compared against a
           freshly computed SHA-256 digest of the event payload.  A mismatch
           indicates the stored record was tampered with.
        2. **Chain linkage** — the event's ``previous_hash`` must equal the
           ``hash`` of the preceding event (or the genesis value of 64 zeros
           for the first event).
        """
        events = await self.get_events(simulation_id)
        if not events:
            return True, "No events to verify"

        genesis_hash = "0" * 64
        expected_previous = genesis_hash

        for i, event in enumerate(events):
            # --- check 1: recompute hash ---
            computed = self.compute_event_hash(event)
            if computed != event["hash"]:
                logger.warning(
                    "Audit integrity failure at event %d (%s): " "stored hash=%s, computed hash=%s",
                    i,
                    event.get("event_id", "?"),
                    event["hash"][:16],
                    computed[:16],
                )
                return False, (
                    f"Hash mismatch at event {i} ({event.get('event_id', '?')}): "
                    f"stored={event['hash'][:16]}..., "
                    f"computed={computed[:16]}..."
                )

            # --- check 2: chain linkage ---
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
