"""Audit trail management with hash chain verification."""

import csv
import hashlib
import io
import json
import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.database import AuditTrailRepository

logger = logging.getLogger(__name__)

# Genesis hash for the first event in a chain
GENESIS_HASH = "0" * 64


class AuditEventType(str, Enum):
    """Types of audit events."""

    CONFIG_CHANGE = "config_change"
    SIMULATION_START = "simulation_start"
    SIMULATION_PAUSE = "simulation_pause"
    SIMULATION_RESUME = "simulation_resume"
    SIMULATION_COMPLETE = "simulation_complete"
    AGENT_DECISION = "agent_decision"
    REPORT_GENERATION = "report_generation"
    ANNOTATION_ADDED = "annotation_added"
    PARAMETER_CHANGE = "parameter_change"
    EXPORT = "export"


class AuditEvent(BaseModel):
    """A single audit event in the trail."""

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    simulation_id: str
    event_type: AuditEventType
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    actor: str
    details: dict[str, Any] = Field(default_factory=dict)
    previous_hash: str = GENESIS_HASH
    hash: str = ""

    def model_post_init(self, __context):
        """Compute hash after model initialization."""
        if not self.hash:
            self.hash = self._compute_hash()

    def _compute_hash(self) -> str:
        """Compute SHA-256 hash for this event.

        Hash = SHA256(previous_hash + event_id + event_type + timestamp
                      + json(details))
        """
        data = (
            self.previous_hash
            + self.event_id
            + self.event_type.value
            + self.timestamp
            + json.dumps(self.details, sort_keys=True)
        )
        return hashlib.sha256(data.encode()).hexdigest()


class AuditTrail(BaseModel):
    """Complete audit trail for a simulation."""

    simulation_id: str
    events: list[AuditEvent] = Field(default_factory=list)
    is_valid: bool = True
    integrity_check_message: str = ""


class AuditTrailManager:
    """Manager for audit trails with hash chain verification.

    Provides in-memory storage of audit events per simulation with
    cryptographic hash chain for integrity verification.
    Persistence is handled via SQLite write-through cache.
    """

    def __init__(self):
        """Initialize the audit trail manager with in-memory storage."""
        self._trails: dict[str, list[AuditEvent]] = {}
        self._repo = AuditTrailRepository()

    async def log_event(
        self,
        simulation_id: str,
        event_type: AuditEventType,
        actor: str,
        details: dict[str, Any] | None = None,
    ) -> AuditEvent:
        """Log a new audit event.

        Args:
            simulation_id: The simulation ID.
            event_type: Type of the event.
            actor: Who or what triggered the event.
            details: Additional event details.

        Returns:
            The created AuditEvent.
        """
        # Get previous hash from in-memory or DB
        trail = self._trails.get(simulation_id, [])
        if trail:
            previous_hash = trail[-1].hash
        else:
            # Try loading from DB
            try:
                db_events = await self._repo.get_events(simulation_id)
                if db_events:
                    previous_hash = db_events[-1]["hash"]
                    # Cache in memory
                    self._trails[simulation_id] = [
                        AuditEvent(**e) for e in db_events
                    ]
                else:
                    previous_hash = GENESIS_HASH
            except Exception as e:
                logger.warning(f"Failed to load events from DB: {e}")
                previous_hash = GENESIS_HASH

        # Create event
        event = AuditEvent(
            simulation_id=simulation_id,
            event_type=event_type,
            actor=actor,
            details=details or {},
            previous_hash=previous_hash,
        )

        # Store in memory
        if simulation_id not in self._trails:
            self._trails[simulation_id] = []
        self._trails[simulation_id].append(event)

        # Persist to DB
        try:
            await self._repo.save_event(event.model_dump())
        except Exception as e:
            logger.warning(f"Failed to save audit event to DB: {e}")

        logger.info(
            f"Logged audit event: {event_type.value} for simulation "
            f"{simulation_id} by {actor}"
        )
        return event

    async def get_trail(self, simulation_id: str) -> AuditTrail:
        """Get the complete audit trail for a simulation.

        Args:
            simulation_id: The simulation ID.

        Returns:
            AuditTrail with all events.
        """
        # Try in-memory first
        if simulation_id in self._trails:
            return AuditTrail(
                simulation_id=simulation_id,
                events=list(self._trails[simulation_id]),
            )

        # Load from DB
        try:
            db_events = await self._repo.get_events(simulation_id)
            if db_events:
                events = [AuditEvent(**e) for e in db_events]
                self._trails[simulation_id] = events  # Cache
                return AuditTrail(
                    simulation_id=simulation_id,
                    events=events,
                )
        except Exception as e:
            logger.warning(f"Failed to load trail from DB: {e}")

        return AuditTrail(simulation_id=simulation_id, events=[])

    async def verify_integrity(self, simulation_id: str) -> tuple[bool, str]:
        """Verify the hash chain integrity of an audit trail.

        Args:
            simulation_id: The simulation ID.

        Returns:
            Tuple of (is_valid, message).
        """
        # Load from DB for verification
        try:
            is_valid, message = await self._repo.verify_integrity(
                simulation_id
            )
            return is_valid, message
        except Exception as e:
            logger.warning(f"DB integrity check failed, using in-memory: {e}")
            # Fall back to in-memory
            trail = self._trails.get(simulation_id, [])

            if not trail:
                return True, "No events to verify"

            expected_previous = GENESIS_HASH

            for i, event in enumerate(trail):
                # Check previous hash linkage
                if event.previous_hash != expected_previous:
                    return False, (
                        f"Hash chain broken at event {i}: "
                        f"expected previous_hash={expected_previous[:16]}..., "
                        f"got {event.previous_hash[:16]}..."
                    )

                # Verify event hash
                computed_hash = event._compute_hash()
                if event.hash != computed_hash:
                    return False, (
                        f"Event hash mismatch at event {i}: "
                        f"stored={event.hash[:16]}..., "
                        f"computed={computed_hash[:16]}..."
                    )

                expected_previous = event.hash

            return True, f"Verified {len(trail)} events successfully"

    async def export_trail(
        self, simulation_id: str, format: str = "json"
    ) -> str | bytes:
        """Export audit trail in the specified format.

        Args:
            simulation_id: The simulation ID.
            format: Export format ("json" or "csv").

        Returns:
            Exported data as string (json) or bytes (csv).

        Raises:
            ValueError: If format is not supported.
        """
        trail = await self.get_trail(simulation_id)

        if format == "json":
            return trail.model_dump_json(indent=2)

        if format == "csv":
            output = io.StringIO()
            writer = csv.writer(output)

            # Write header
            writer.writerow([
                "event_id",
                "simulation_id",
                "event_type",
                "timestamp",
                "actor",
                "details",
                "previous_hash",
                "hash",
            ])

            # Write events
            for event in trail.events:
                writer.writerow([
                    event.event_id,
                    event.simulation_id,
                    event.event_type.value,
                    event.timestamp,
                    event.actor,
                    json.dumps(event.details),
                    event.previous_hash,
                    event.hash,
                ])

            return output.getvalue()

        raise ValueError(f"Unsupported export format: {format}")

    def clear_trail(self, simulation_id: str) -> bool:
        """Clear the audit trail for a simulation.

        Args:
            simulation_id: The simulation ID.

        Returns:
            True if trail was cleared, False if no trail existed.
        """
        if simulation_id in self._trails:
            del self._trails[simulation_id]
            logger.info(f"Cleared audit trail for simulation {simulation_id}")
            return True
        return False

    def get_event_count(self, simulation_id: str) -> int:
        """Get the number of events in a trail.

        Args:
            simulation_id: The simulation ID.

        Returns:
            Number of events.
        """
        return len(self._trails.get(simulation_id, []))


# Global instance
audit_manager = AuditTrailManager()
