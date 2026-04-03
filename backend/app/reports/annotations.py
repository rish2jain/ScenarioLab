"""Annotation management for simulations."""

import logging
import uuid
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel

from app.database import AnnotationRepository

logger = logging.getLogger(__name__)


class Annotation(BaseModel):
    """A user annotation on a simulation message."""

    id: str
    simulation_id: str
    agent_id: str | None = None
    message_id: str | None = None
    round_number: int
    content: str
    tag: Literal["agree", "disagree", "caveat"]
    annotator: str
    timestamp: str


class AnnotationCreate(BaseModel):
    """Request to create a new annotation."""

    simulation_id: str
    agent_id: str | None = None
    message_id: str | None = None
    round_number: int
    content: str
    tag: Literal["agree", "disagree", "caveat"]
    annotator: str


class AnnotationFilter(BaseModel):
    """Filter parameters for querying annotations."""

    tag: str | None = None
    annotator: str | None = None
    round: int | None = None


class AnnotationManager:
    """Manage annotations with in-memory storage and SQLite persistence."""

    def __init__(self):
        # In-memory storage: annotation_id -> Annotation
        self._annotations: dict[str, Annotation] = {}
        # Index by simulation_id for fast lookup
        self._by_simulation: dict[str, list[str]] = {}
        # SQLite repository for persistence
        self._repo = AnnotationRepository()

    async def create_annotation(
        self,
        simulation_id: str,
        agent_id: str | None,
        message_id: str | None,
        round_number: int,
        content: str,
        tag: Literal["agree", "disagree", "caveat"],
        annotator: str,
    ) -> Annotation:
        """Create a new annotation."""
        annotation_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()

        annotation = Annotation(
            id=annotation_id,
            simulation_id=simulation_id,
            agent_id=agent_id,
            message_id=message_id,
            round_number=round_number,
            content=content,
            tag=tag,
            annotator=annotator,
            timestamp=timestamp,
        )

        # Store in memory
        self._annotations[annotation_id] = annotation

        # Update index
        if simulation_id not in self._by_simulation:
            self._by_simulation[simulation_id] = []
        self._by_simulation[simulation_id].append(annotation_id)

        # Persist to DB
        try:
            await self._repo.save_annotation(annotation.model_dump())
        except Exception as e:
            logger.warning(f"Failed to save annotation to DB: {e}")

        logger.info(
            f"Created annotation {annotation_id} for "
            f"simulation {simulation_id}"
        )
        return annotation

    async def get_annotations(
        self,
        simulation_id: str,
        tag: str | None = None,
        annotator: str | None = None,
        round: int | None = None,
    ) -> list[Annotation]:
        """Get annotations for a simulation with optional filters."""
        # Try loading from DB first
        if simulation_id not in self._by_simulation:
            try:
                db_annotations = await self._repo.get_annotations(
                    simulation_id, tag, annotator, round
                )
                if db_annotations:
                    for a in db_annotations:
                        annotation = Annotation(**a)
                        self._annotations[a["id"]] = annotation
                        if a["simulation_id"] not in self._by_simulation:
                            self._by_simulation[a["simulation_id"]] = []
                        self._by_simulation[a["simulation_id"]].append(
                            a["id"]
                        )
            except Exception as e:
                logger.warning(f"Failed to load annotations from DB: {e}")

        if simulation_id not in self._by_simulation:
            return []

        annotations = []
        for aid in self._by_simulation[simulation_id]:
            annotation = self._annotations.get(aid)
            if not annotation:
                continue

            # Apply filters
            if tag and annotation.tag != tag:
                continue
            if annotator and annotation.annotator != annotator:
                continue
            if round is not None and annotation.round_number != round:
                continue

            annotations.append(annotation)

        # Sort by timestamp (newest first)
        annotations.sort(
            key=lambda a: a.timestamp, reverse=True
        )
        return annotations

    def get_annotation(self, annotation_id: str) -> Annotation | None:
        """Get a specific annotation by ID."""
        return self._annotations.get(annotation_id)

    async def delete_annotation(self, annotation_id: str) -> bool:
        """Delete an annotation by ID."""
        if annotation_id not in self._annotations:
            return False

        annotation = self._annotations[annotation_id]
        simulation_id = annotation.simulation_id

        # Remove from memory
        del self._annotations[annotation_id]

        # Remove from index
        if simulation_id in self._by_simulation:
            self._by_simulation[simulation_id] = [
                aid
                for aid in self._by_simulation[simulation_id]
                if aid != annotation_id
            ]

        # Delete from DB
        try:
            await self._repo.delete_annotation(annotation_id)
        except Exception as e:
            logger.warning(f"Failed to delete annotation from DB: {e}")

        logger.info(f"Deleted annotation {annotation_id}")
        return True

    async def export_annotations(self, simulation_id: str) -> dict:
        """Export all annotations for a simulation as JSON."""
        annotations = await self.get_annotations(simulation_id)
        return {
            "simulation_id": simulation_id,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "total_annotations": len(annotations),
            "annotations": [a.model_dump() for a in annotations],
        }

    def clear_simulation_annotations(self, simulation_id: str) -> int:
        """Clear all annotations for a simulation. Returns count deleted."""
        if simulation_id not in self._by_simulation:
            return 0

        count = len(self._by_simulation[simulation_id])
        for aid in self._by_simulation[simulation_id]:
            self._annotations.pop(aid, None)

        del self._by_simulation[simulation_id]
        logger.info(
            f"Cleared {count} annotations for simulation {simulation_id}"
        )
        return count


# Global annotation manager instance
annotation_manager = AnnotationManager()
