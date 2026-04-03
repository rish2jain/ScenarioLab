"""SQLite persistence layer for MiroFish backend."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

from app.graph.seed_processor import SeedMaterial
from app.simulation.models import SimulationState

logger = logging.getLogger(__name__)

# Database file path (relative to backend dir)
_DB_DIR = Path(__file__).resolve().parent.parent / "data"
_DB_PATH = _DB_DIR / "mirofish.db"

# Module-level connection reference
_db: aiosqlite.Connection | None = None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def get_db() -> aiosqlite.Connection:
    """Return the active database connection, raising if not initialized."""
    if _db is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    return _db


async def init_database() -> None:
    """Initialize the SQLite database and create tables."""
    global _db  # noqa: PLW0603

    _DB_DIR.mkdir(parents=True, exist_ok=True)

    logger.info(f"Initializing SQLite database at {_DB_PATH}")
    _db = await aiosqlite.connect(str(_DB_PATH))
    _db.row_factory = aiosqlite.Row

    # Enable WAL mode for better concurrent read performance
    await _db.execute("PRAGMA journal_mode=WAL")

    await _db.executescript(
        """
        CREATE TABLE IF NOT EXISTS simulations (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            config TEXT NOT NULL,
            state TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS seeds (
            id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            content_type TEXT NOT NULL,
            raw_content TEXT NOT NULL,
            processed_content TEXT,
            status TEXT NOT NULL,
            metadata TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS audit_events (
            event_id TEXT PRIMARY KEY,
            simulation_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            actor TEXT NOT NULL,
            details TEXT NOT NULL,
            previous_hash TEXT NOT NULL,
            hash TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS scenario_branches (
            branch_id TEXT PRIMARY KEY,
            root_id TEXT NOT NULL,
            parent_id TEXT,
            name TEXT NOT NULL,
            description TEXT,
            config_diff TEXT NOT NULL,
            simulation_id TEXT,
            created_at TEXT NOT NULL,
            creator TEXT
        );

        CREATE TABLE IF NOT EXISTS annotations (
            id TEXT PRIMARY KEY,
            simulation_id TEXT NOT NULL,
            agent_id TEXT,
            message_id TEXT,
            round_number INTEGER,
            content TEXT NOT NULL,
            tag TEXT NOT NULL,
            annotator TEXT NOT NULL,
            timestamp TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS chat_history (
            id TEXT PRIMARY KEY,
            simulation_id TEXT NOT NULL,
            agent_id TEXT NOT NULL,
            agent_name TEXT,
            user_message TEXT NOT NULL,
            agent_response TEXT NOT NULL,
            timestamp TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS agent_memories (
            id TEXT PRIMARY KEY,
            simulation_id TEXT NOT NULL,
            agent_id TEXT NOT NULL,
            round_number INTEGER NOT NULL,
            content TEXT NOT NULL,
            memory_type TEXT NOT NULL,
            timestamp TEXT NOT NULL
        );
        """
    )
    await _db.commit()
    logger.info("Database tables initialized")


async def close_database() -> None:
    """Close the database connection."""
    global _db  # noqa: PLW0603
    if _db is not None:
        await _db.close()
        _db = None
        logger.info("Database connection closed")


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
        db = await get_db()
        cursor = await db.execute(
            "SELECT state FROM simulations WHERE id = ?",
            (simulation_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return SimulationState.model_validate_json(row[0])

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
        # Also patch the status inside the stored state JSON
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
        return SeedMaterial(
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
        return [
            {
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
            for row in rows
        ]

    async def delete_branch(self, branch_id: str) -> bool:
        """Delete a branch by ID."""
        db = await get_db()
        cursor = await db.execute(
            "DELETE FROM scenario_branches WHERE branch_id = ?",
            (branch_id,),
        )
        await db.commit()
        return cursor.rowcount > 0


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
        params = [simulation_id]

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


class ChatHistoryRepository:
    """CRUD operations for chat history persistence."""

    async def save_message(
        self,
        simulation_id: str,
        agent_id: str,
        agent_name: str | None,
        user_message: str,
        agent_response: str,
        timestamp: str,
    ) -> str:
        """Save a chat message exchange. Returns the message ID."""
        import uuid
        db = await get_db()
        msg_id = str(uuid.uuid4())
        await db.execute(
            """
            INSERT INTO chat_history
                (id, simulation_id, agent_id, agent_name, user_message,
                 agent_response, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                msg_id,
                simulation_id,
                agent_id,
                agent_name,
                user_message,
                agent_response,
                timestamp,
            ),
        )
        await db.commit()
        return msg_id

    async def get_history(self, simulation_id: str) -> list[dict]:
        """Retrieve chat history for a simulation."""
        db = await get_db()
        cursor = await db.execute(
            "SELECT id, simulation_id, agent_id, agent_name, user_message,"
            " agent_response, timestamp"
            " FROM chat_history WHERE simulation_id = ?"
            " ORDER BY timestamp ASC",
            (simulation_id,),
        )
        rows = await cursor.fetchall()
        return [
            {
                "id": row[0],
                "simulation_id": row[1],
                "agent_id": row[2],
                "agent_name": row[3],
                "user_message": row[4],
                "agent_response": row[5],
                "timestamp": row[6],
            }
            for row in rows
        ]

    async def clear_history(self, simulation_id: str) -> int:
        """Clear chat history for a simulation. Returns count deleted."""
        db = await get_db()
        cursor = await db.execute(
            "SELECT COUNT(*) FROM chat_history WHERE simulation_id = ?",
            (simulation_id,),
        )
        row = await cursor.fetchone()
        count = row[0] if row else 0

        await db.execute(
            "DELETE FROM chat_history WHERE simulation_id = ?",
            (simulation_id,),
        )
        await db.commit()
        return count


class AgentMemoryRepository:
    """CRUD operations for agent memory persistence."""

    async def save_memory(
        self,
        simulation_id: str,
        agent_id: str,
        round_number: int,
        content: str,
        memory_type: str,
        timestamp: str,
    ) -> str:
        """Save an agent memory. Returns the memory ID."""
        import uuid
        db = await get_db()
        memory_id = str(uuid.uuid4())
        await db.execute(
            """
            INSERT INTO agent_memories
                (id, simulation_id, agent_id, round_number, content,
                 memory_type, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                memory_id,
                simulation_id,
                agent_id,
                round_number,
                content,
                memory_type,
                timestamp,
            ),
        )
        await db.commit()
        return memory_id

    async def get_memories(
        self,
        simulation_id: str,
        agent_id: str,
        limit: int = 10,
    ) -> list[dict]:
        """Retrieve memories for an agent in a simulation."""
        db = await get_db()
        cursor = await db.execute(
            "SELECT id, simulation_id, agent_id, round_number, content,"
            " memory_type, timestamp"
            " FROM agent_memories"
            " WHERE simulation_id = ? AND agent_id = ?"
            " ORDER BY timestamp DESC LIMIT ?",
            (simulation_id, agent_id, limit),
        )
        rows = await cursor.fetchall()
        return [
            {
                "id": row[0],
                "simulation_id": row[1],
                "agent_id": row[2],
                "round_number": row[3],
                "content": row[4],
                "memory_type": row[5],
                "timestamp": row[6],
            }
            for row in rows
        ]

    async def search_memories(
        self,
        simulation_id: str,
        agent_id: str,
        query: str,
        limit: int = 5,
    ) -> list[dict]:
        """Search memories by content (simple LIKE search)."""
        db = await get_db()
        cursor = await db.execute(
            "SELECT id, simulation_id, agent_id, round_number, content,"
            " memory_type, timestamp"
            " FROM agent_memories"
            " WHERE simulation_id = ? AND agent_id = ?"
            " AND content LIKE ?"
            " ORDER BY timestamp DESC LIMIT ?",
            (simulation_id, agent_id, f"%{query}%", limit),
        )
        rows = await cursor.fetchall()
        return [
            {
                "id": row[0],
                "simulation_id": row[1],
                "agent_id": row[2],
                "round_number": row[3],
                "content": row[4],
                "memory_type": row[5],
                "timestamp": row[6],
            }
            for row in rows
        ]
