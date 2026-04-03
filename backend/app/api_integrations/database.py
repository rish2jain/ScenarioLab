"""SQLite persistence layer for API integrations."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite

logger = logging.getLogger(__name__)

# Database file path (same as main database)
_DB_PATH = (
    Path(__file__).resolve().parent.parent.parent / "data" / "mirofish.db"
)

# Lazy initialization flag
_initialized = False


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def get_db() -> aiosqlite.Connection:
    """Get a database connection."""
    db = await aiosqlite.connect(str(_DB_PATH))
    db.row_factory = aiosqlite.Row
    return db


async def init_integration_tables() -> None:
    """Initialize the integration tables."""
    global _initialized  # noqa: PLW0603

    if _initialized:
        return

    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"Initializing integration tables at {_DB_PATH}")
    db = await get_db()
    try:
        await db.executescript(
            """
            CREATE TABLE IF NOT EXISTS api_keys (
                key_id TEXT PRIMARY KEY,
                key_value TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                permissions TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_used_at TEXT,
                active BOOLEAN DEFAULT 1,
                metadata TEXT
            );

            CREATE TABLE IF NOT EXISTS webhooks (
                webhook_id TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                events TEXT NOT NULL,
                api_key_id TEXT NOT NULL,
                active BOOLEAN DEFAULT 1,
                created_at TEXT NOT NULL,
                last_triggered_at TEXT,
                failure_count INTEGER DEFAULT 0,
                metadata TEXT
            );

            CREATE TABLE IF NOT EXISTS webhook_deliveries (
                delivery_id TEXT PRIMARY KEY,
                webhook_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                url TEXT NOT NULL,
                status_code INTEGER,
                success BOOLEAN NOT NULL,
                error_message TEXT,
                timestamp TEXT NOT NULL,
                response_time_ms REAL
            );

            CREATE TABLE IF NOT EXISTS custom_personas (
                persona_id TEXT PRIMARY KEY,
                persona_data TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS counterpart_agents (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                brief TEXT NOT NULL,
                stakeholder_type TEXT NOT NULL,
                rehearsal_mode TEXT NOT NULL,
                persona_data TEXT NOT NULL,
                conversation_history TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS cross_simulation_data (
                simulation_id TEXT PRIMARY KEY,
                opted_in BOOLEAN DEFAULT 0,
                patterns TEXT,
                simulation_data TEXT,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS gamification_configs (
                simulation_id TEXT PRIMARY KEY,
                config TEXT NOT NULL,
                scores TEXT,
                leaderboard TEXT,
                updated_at TEXT NOT NULL
            );
            """
        )
        await db.commit()
        _initialized = True
        logger.info("Integration tables initialized")
    finally:
        await db.close()


async def ensure_tables() -> None:
    """Ensure tables are initialized (lazy initialization)."""
    await init_integration_tables()


class APIKeyRepository:
    """CRUD operations for API key persistence."""

    async def save(self, key_data: dict[str, Any]) -> None:
        """Save an API key to the database."""
        await ensure_tables()
        db = await get_db()
        try:
            await db.execute(
                """
                INSERT INTO api_keys
                    (key_id, key_value, name, permissions,
                     created_at, last_used_at, active, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(key_id) DO UPDATE SET
                    key_value = excluded.key_value,
                    name = excluded.name,
                    permissions = excluded.permissions,
                    last_used_at = excluded.last_used_at,
                    active = excluded.active,
                    metadata = excluded.metadata
                """,
                (
                    key_data["key_id"],
                    key_data["key"],
                    key_data["name"],
                    json.dumps(key_data.get("permissions", [])),
                    key_data.get("created_at", _utc_now_iso()),
                    key_data.get("last_used_at"),
                    1 if key_data.get("active", True) else 0,
                    json.dumps(key_data.get("metadata", {})),
                ),
            )
            await db.commit()
        except Exception as e:
            logger.warning(f"Failed to save API key to DB: {e}")
        finally:
            await db.close()

    async def get(self, key_id: str) -> dict[str, Any] | None:
        """Get an API key by ID."""
        await ensure_tables()
        db = await get_db()
        try:
            cursor = await db.execute(
                "SELECT * FROM api_keys WHERE key_id = ?", (key_id,)
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            return self._row_to_dict(row)
        except Exception as e:
            logger.warning(f"Failed to get API key from DB: {e}")
            return None
        finally:
            await db.close()

    async def get_by_key_value(self, key_value: str) -> dict[str, Any] | None:
        """Get an API key by key value."""
        await ensure_tables()
        db = await get_db()
        try:
            cursor = await db.execute(
                "SELECT * FROM api_keys WHERE key_value = ?", (key_value,)
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            return self._row_to_dict(row)
        except Exception as e:
            logger.warning(f"Failed to get API key by value from DB: {e}")
            return None
        finally:
            await db.close()

    async def list_all(self) -> list[dict[str, Any]]:
        """List all API keys."""
        await ensure_tables()
        db = await get_db()
        try:
            cursor = await db.execute("SELECT * FROM api_keys")
            rows = await cursor.fetchall()
            return [self._row_to_dict(row) for row in rows]
        except Exception as e:
            logger.warning(f"Failed to list API keys from DB: {e}")
            return []
        finally:
            await db.close()

    async def update_last_used(self, key_id: str) -> None:
        """Update last used timestamp."""
        await ensure_tables()
        db = await get_db()
        try:
            await db.execute(
                "UPDATE api_keys SET last_used_at = ? WHERE key_id = ?",
                (_utc_now_iso(), key_id),
            )
            await db.commit()
        except Exception as e:
            logger.warning(f"Failed to update last_used_at: {e}")
        finally:
            await db.close()

    async def update_active(self, key_id: str, active: bool) -> None:
        """Update active status."""
        await ensure_tables()
        db = await get_db()
        try:
            await db.execute(
                "UPDATE api_keys SET active = ? WHERE key_id = ?",
                (1 if active else 0, key_id),
            )
            await db.commit()
        except Exception as e:
            logger.warning(f"Failed to update active status: {e}")
        finally:
            await db.close()

    async def delete(self, key_id: str) -> bool:
        """Delete an API key."""
        await ensure_tables()
        db = await get_db()
        try:
            cursor = await db.execute(
                "DELETE FROM api_keys WHERE key_id = ?", (key_id,)
            )
            await db.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.warning(f"Failed to delete API key: {e}")
            return False
        finally:
            await db.close()

    def _row_to_dict(self, row: aiosqlite.Row) -> dict[str, Any]:
        return {
            "key_id": row["key_id"],
            "key": row["key_value"],
            "name": row["name"],
            "permissions": (
                json.loads(row["permissions"]) if row["permissions"] else []
            ),
            "created_at": row["created_at"],
            "last_used_at": row["last_used_at"],
            "active": bool(row["active"]),
            "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
        }


class WebhookRepository:
    """CRUD operations for webhook persistence."""

    async def save(self, webhook_data: dict[str, Any]) -> None:
        """Save a webhook to the database."""
        await ensure_tables()
        db = await get_db()
        try:
            await db.execute(
                """
                INSERT INTO webhooks
                    (webhook_id, url, events, api_key_id, active,
                     created_at, last_triggered_at, failure_count, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(webhook_id) DO UPDATE SET
                    url = excluded.url,
                    events = excluded.events,
                    active = excluded.active,
                    last_triggered_at = excluded.last_triggered_at,
                    failure_count = excluded.failure_count,
                    metadata = excluded.metadata
                """,
                (
                    webhook_data["webhook_id"],
                    webhook_data["url"],
                    json.dumps(webhook_data.get("events", [])),
                    webhook_data["api_key_id"],
                    1 if webhook_data.get("active", True) else 0,
                    webhook_data.get("created_at", _utc_now_iso()),
                    webhook_data.get("last_triggered_at"),
                    webhook_data.get("failure_count", 0),
                    json.dumps(webhook_data.get("metadata", {})),
                ),
            )
            await db.commit()
        except Exception as e:
            logger.warning(f"Failed to save webhook to DB: {e}")
        finally:
            await db.close()

    async def get(self, webhook_id: str) -> dict[str, Any] | None:
        """Get a webhook by ID."""
        await ensure_tables()
        db = await get_db()
        try:
            cursor = await db.execute(
                "SELECT * FROM webhooks WHERE webhook_id = ?", (webhook_id,)
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            return self._row_to_dict(row)
        except Exception as e:
            logger.warning(f"Failed to get webhook from DB: {e}")
            return None
        finally:
            await db.close()

    async def list_all(
        self, api_key_id: str | None = None
    ) -> list[dict[str, Any]]:
        """List all webhooks, optionally filtered by API key."""
        await ensure_tables()
        db = await get_db()
        try:
            if api_key_id:
                cursor = await db.execute(
                    "SELECT * FROM webhooks WHERE api_key_id = ?",
                    (api_key_id,),
                )
            else:
                cursor = await db.execute("SELECT * FROM webhooks")
            rows = await cursor.fetchall()
            return [self._row_to_dict(row) for row in rows]
        except Exception as e:
            logger.warning(f"Failed to list webhooks from DB: {e}")
            return []
        finally:
            await db.close()

    async def delete(self, webhook_id: str) -> bool:
        """Delete a webhook."""
        await ensure_tables()
        db = await get_db()
        try:
            cursor = await db.execute(
                "DELETE FROM webhooks WHERE webhook_id = ?", (webhook_id,)
            )
            await db.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.warning(f"Failed to delete webhook: {e}")
            return False
        finally:
            await db.close()

    async def save_delivery(self, delivery_data: dict[str, Any]) -> None:
        """Save a webhook delivery record."""
        await ensure_tables()
        db = await get_db()
        try:
            await db.execute(
                """
                INSERT INTO webhook_deliveries
                    (delivery_id, webhook_id, event_type, url,
                     status_code, success, error_message, timestamp,
                     response_time_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    delivery_data["delivery_id"],
                    delivery_data["webhook_id"],
                    delivery_data["event_type"],
                    delivery_data["url"],
                    delivery_data.get("status_code"),
                    1 if delivery_data.get("success", False) else 0,
                    delivery_data.get("error_message"),
                    delivery_data.get("timestamp", _utc_now_iso()),
                    delivery_data.get("response_time_ms"),
                ),
            )
            await db.commit()

            # Cap deliveries at 1000 per webhook
            await self._cap_deliveries(db, delivery_data["webhook_id"])
        except Exception as e:
            logger.warning(f"Failed to save delivery to DB: {e}")
        finally:
            await db.close()

    async def list_deliveries(
        self, webhook_id: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        """List delivery records."""
        await ensure_tables()
        db = await get_db()
        try:
            if webhook_id:
                cursor = await db.execute(
                    """
                    SELECT * FROM webhook_deliveries
                    WHERE webhook_id = ?
                    ORDER BY timestamp DESC LIMIT ?
                    """,
                    (webhook_id, limit),
                )
            else:
                cursor = await db.execute(
                    """
                    SELECT * FROM webhook_deliveries
                    ORDER BY timestamp DESC LIMIT ?
                    """,
                    (limit,),
                )
            rows = await cursor.fetchall()
            return [self._delivery_row_to_dict(row) for row in rows]
        except Exception as e:
            logger.warning(f"Failed to list deliveries from DB: {e}")
            return []
        finally:
            await db.close()

    async def _cap_deliveries(
        self, db: aiosqlite.Connection, webhook_id: str, max_count: int = 1000
    ) -> None:
        """Cap deliveries at max_count per webhook."""
        cursor = await db.execute(
            """
            SELECT COUNT(*) FROM webhook_deliveries WHERE webhook_id = ?
            """,
            (webhook_id,),
        )
        row = await cursor.fetchone()
        count = row[0] if row else 0

        if count > max_count:
            # Delete oldest deliveries
            await db.execute(
                """
                DELETE FROM webhook_deliveries
                WHERE webhook_id = ? AND delivery_id IN (
                    SELECT delivery_id FROM webhook_deliveries
                    WHERE webhook_id = ?
                    ORDER BY timestamp ASC
                    LIMIT ?
                )
                """,
                (webhook_id, webhook_id, count - max_count),
            )
            await db.commit()

    async def update_webhook_stats(
        self,
        webhook_id: str,
        last_triggered_at: str | None = None,
        increment_failure: bool = False,
    ) -> None:
        """Update webhook statistics."""
        await ensure_tables()
        db = await get_db()
        try:
            if increment_failure:
                await db.execute(
                    """
                    UPDATE webhooks SET
                        last_triggered_at = COALESCE(?, last_triggered_at),
                        failure_count = failure_count + 1
                    WHERE webhook_id = ?
                    """,
                    (last_triggered_at, webhook_id),
                )
            else:
                await db.execute(
                    """
                    UPDATE webhooks SET last_triggered_at = ?
                    WHERE webhook_id = ?
                    """,
                    (last_triggered_at, webhook_id),
                )
            await db.commit()
        except Exception as e:
            logger.warning(f"Failed to update webhook stats: {e}")
        finally:
            await db.close()

    def _row_to_dict(self, row: aiosqlite.Row) -> dict[str, Any]:
        return {
            "webhook_id": row["webhook_id"],
            "url": row["url"],
            "events": json.loads(row["events"]) if row["events"] else [],
            "api_key_id": row["api_key_id"],
            "active": bool(row["active"]),
            "created_at": row["created_at"],
            "last_triggered_at": row["last_triggered_at"],
            "failure_count": row["failure_count"],
            "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
        }

    def _delivery_row_to_dict(self, row: aiosqlite.Row) -> dict[str, Any]:
        return {
            "delivery_id": row["delivery_id"],
            "webhook_id": row["webhook_id"],
            "event_type": row["event_type"],
            "url": row["url"],
            "status_code": row["status_code"],
            "success": bool(row["success"]),
            "error_message": row["error_message"],
            "timestamp": row["timestamp"],
            "response_time_ms": row["response_time_ms"],
        }


class CustomPersonaRepository:
    """CRUD operations for custom persona persistence."""

    async def save(
        self, persona_id: str, persona_data: dict[str, Any]
    ) -> None:
        """Save a custom persona to the database."""
        await ensure_tables()
        db = await get_db()
        try:
            now = _utc_now_iso()
            await db.execute(
                """
                INSERT INTO custom_personas
                    (persona_id, persona_data, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(persona_id) DO UPDATE SET
                    persona_data = excluded.persona_data,
                    updated_at = excluded.updated_at
                """,
                (persona_id, json.dumps(persona_data), now, now),
            )
            await db.commit()
        except Exception as e:
            logger.warning(f"Failed to save custom persona to DB: {e}")
        finally:
            await db.close()

    async def get(self, persona_id: str) -> dict[str, Any] | None:
        """Get a custom persona by ID."""
        await ensure_tables()
        db = await get_db()
        try:
            cursor = await db.execute(
                "SELECT persona_data FROM custom_personas "
                "WHERE persona_id = ?",
                (persona_id,),
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            return json.loads(row["persona_data"])
        except Exception as e:
            logger.warning(f"Failed to get custom persona from DB: {e}")
            return None
        finally:
            await db.close()

    async def list_all(self) -> list[dict[str, Any]]:
        """List all custom personas."""
        await ensure_tables()
        db = await get_db()
        try:
            cursor = await db.execute(
                "SELECT persona_data FROM custom_personas"
            )
            rows = await cursor.fetchall()
            return [json.loads(row["persona_data"]) for row in rows]
        except Exception as e:
            logger.warning(f"Failed to list custom personas from DB: {e}")
            return []
        finally:
            await db.close()

    async def delete(self, persona_id: str) -> bool:
        """Delete a custom persona."""
        await ensure_tables()
        db = await get_db()
        try:
            cursor = await db.execute(
                "DELETE FROM custom_personas WHERE persona_id = ?",
                (persona_id,),
            )
            await db.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.warning(f"Failed to delete custom persona: {e}")
            return False
        finally:
            await db.close()


class CounterpartRepository:
    """CRUD operations for counterpart agent persistence."""

    async def save(self, counterpart_data: dict[str, Any]) -> None:
        """Save a counterpart agent to the database."""
        await ensure_tables()
        db = await get_db()
        try:
            await db.execute(
                """
                INSERT INTO counterpart_agents
                    (id, name, brief, stakeholder_type, rehearsal_mode,
                     persona_data, conversation_history, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    brief = excluded.brief,
                    stakeholder_type = excluded.stakeholder_type,
                    rehearsal_mode = excluded.rehearsal_mode,
                    persona_data = excluded.persona_data,
                    conversation_history = excluded.conversation_history
                """,
                (
                    counterpart_data["id"],
                    counterpart_data["name"],
                    counterpart_data.get("brief", ""),
                    counterpart_data["stakeholder_type"],
                    counterpart_data["mode"],
                    json.dumps(counterpart_data.get("persona_data", {})),
                    json.dumps(
                        counterpart_data.get("conversation_history", [])
                    ),
                    counterpart_data.get("created_at", _utc_now_iso()),
                ),
            )
            await db.commit()
        except Exception as e:
            logger.warning(f"Failed to save counterpart to DB: {e}")
        finally:
            await db.close()

    async def get(self, counterpart_id: str) -> dict[str, Any] | None:
        """Get a counterpart by ID."""
        await ensure_tables()
        db = await get_db()
        try:
            cursor = await db.execute(
                "SELECT * FROM counterpart_agents WHERE id = ?",
                (counterpart_id,),
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            return self._row_to_dict(row)
        except Exception as e:
            logger.warning(f"Failed to get counterpart from DB: {e}")
            return None
        finally:
            await db.close()

    async def list_all(self) -> list[dict[str, Any]]:
        """List all counterparts."""
        await ensure_tables()
        db = await get_db()
        try:
            cursor = await db.execute("SELECT * FROM counterpart_agents")
            rows = await cursor.fetchall()
            return [self._row_to_dict(row) for row in rows]
        except Exception as e:
            logger.warning(f"Failed to list counterparts from DB: {e}")
            return []
        finally:
            await db.close()

    async def save_conversation(
        self, counterpart_id: str, conversation_history: list[dict]
    ) -> None:
        """Save conversation history for a counterpart."""
        await ensure_tables()
        db = await get_db()
        try:
            await db.execute(
                """
                UPDATE counterpart_agents SET conversation_history = ?
                WHERE id = ?
                """,
                (json.dumps(conversation_history), counterpart_id),
            )
            await db.commit()
        except Exception as e:
            logger.warning(f"Failed to save conversation to DB: {e}")
        finally:
            await db.close()

    async def delete(self, counterpart_id: str) -> bool:
        """Delete a counterpart."""
        await ensure_tables()
        db = await get_db()
        try:
            cursor = await db.execute(
                "DELETE FROM counterpart_agents WHERE id = ?",
                (counterpart_id,),
            )
            await db.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.warning(f"Failed to delete counterpart: {e}")
            return False
        finally:
            await db.close()

    def _row_to_dict(self, row: aiosqlite.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "name": row["name"],
            "brief": row["brief"],
            "stakeholder_type": row["stakeholder_type"],
            "mode": row["rehearsal_mode"],
            "persona_data": (
                json.loads(row["persona_data"]) if row["persona_data"] else {}
            ),
            "conversation_history": (
                json.loads(row["conversation_history"])
                if row["conversation_history"] else []
            ),
            "created_at": row["created_at"],
        }


class CrossSimulationRepository:
    """CRUD operations for cross-simulation data persistence."""

    async def save_opt_in(self, simulation_id: str, opted_in: bool) -> None:
        """Save opt-in status for a simulation."""
        await ensure_tables()
        db = await get_db()
        try:
            now = _utc_now_iso()
            await db.execute(
                """
                INSERT INTO cross_simulation_data
                    (simulation_id, opted_in, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(simulation_id) DO UPDATE SET
                    opted_in = excluded.opted_in,
                    updated_at = excluded.updated_at
                """,
                (simulation_id, 1 if opted_in else 0, now),
            )
            await db.commit()
        except Exception as e:
            logger.warning(f"Failed to save opt-in status to DB: {e}")
        finally:
            await db.close()

    async def get_opt_in(self, simulation_id: str) -> bool:
        """Get opt-in status for a simulation."""
        await ensure_tables()
        db = await get_db()
        try:
            cursor = await db.execute(
                "SELECT opted_in FROM cross_simulation_data "
                "WHERE simulation_id = ?",
                (simulation_id,),
            )
            row = await cursor.fetchone()
            return bool(row["opted_in"]) if row else False
        except Exception as e:
            logger.warning(f"Failed to get opt-in status from DB: {e}")
            return False
        finally:
            await db.close()

    async def save_patterns(
        self,
        simulation_id: str,
        patterns: list[dict],
        simulation_data: dict | None = None,
    ) -> None:
        """Save patterns for a simulation."""
        await ensure_tables()
        db = await get_db()
        try:
            now = _utc_now_iso()
            await db.execute(
                """
                INSERT INTO cross_simulation_data
                    (simulation_id, patterns, simulation_data, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(simulation_id) DO UPDATE SET
                    patterns = excluded.patterns,
                    simulation_data = excluded.simulation_data,
                    updated_at = excluded.updated_at
                """,
                (
                    simulation_id,
                    json.dumps(patterns),
                    json.dumps(simulation_data) if simulation_data else None,
                    now,
                ),
            )
            await db.commit()
        except Exception as e:
            logger.warning(f"Failed to save patterns to DB: {e}")
        finally:
            await db.close()

    async def get_patterns(self, simulation_id: str) -> dict[str, Any] | None:
        """Get patterns for a simulation."""
        await ensure_tables()
        db = await get_db()
        try:
            cursor = await db.execute(
                "SELECT patterns, simulation_data, updated_at "
                "FROM cross_simulation_data WHERE simulation_id = ?",
                (simulation_id,),
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            return {
                "patterns": (
                    json.loads(row["patterns"]) if row["patterns"] else []
                ),
                "simulation_data": (
                    json.loads(row["simulation_data"])
                    if row["simulation_data"] else None
                ),
                "updated_at": row["updated_at"],
            }
        except Exception as e:
            logger.warning(f"Failed to get patterns from DB: {e}")
            return None
        finally:
            await db.close()

    async def list_opted_in(self) -> list[str]:
        """List all opted-in simulation IDs."""
        await ensure_tables()
        db = await get_db()
        try:
            cursor = await db.execute(
                "SELECT simulation_id FROM cross_simulation_data "
                "WHERE opted_in = 1"
            )
            rows = await cursor.fetchall()
            return [row["simulation_id"] for row in rows]
        except Exception as e:
            logger.warning(f"Failed to list opted-in simulations from DB: {e}")
            return []
        finally:
            await db.close()

    async def list_all_patterns(self) -> list[dict[str, Any]]:
        """List all patterns from opted-in simulations."""
        await ensure_tables()
        db = await get_db()
        try:
            cursor = await db.execute(
                "SELECT simulation_id, patterns FROM cross_simulation_data "
                "WHERE opted_in = 1 AND patterns IS NOT NULL"
            )
            rows = await cursor.fetchall()
            results = []
            for row in rows:
                patterns = (
                    json.loads(row["patterns"]) if row["patterns"] else []
                )
                for pattern in patterns:
                    pattern["simulation_id"] = row["simulation_id"]
                    results.append(pattern)
            return results
        except Exception as e:
            logger.warning(f"Failed to list all patterns from DB: {e}")
            return []
        finally:
            await db.close()


class GamificationRepository:
    """CRUD operations for gamification data persistence."""

    async def save_config(
        self, simulation_id: str, config: dict[str, Any]
    ) -> None:
        """Save gamification config for a simulation."""
        await ensure_tables()
        db = await get_db()
        try:
            now = _utc_now_iso()
            await db.execute(
                """
                INSERT INTO gamification_configs
                    (simulation_id, config, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(simulation_id) DO UPDATE SET
                    config = excluded.config,
                    updated_at = excluded.updated_at
                """,
                (simulation_id, json.dumps(config), now),
            )
            await db.commit()
        except Exception as e:
            logger.warning(f"Failed to save gamification config to DB: {e}")
        finally:
            await db.close()

    async def get_config(self, simulation_id: str) -> dict[str, Any] | None:
        """Get gamification config for a simulation."""
        await ensure_tables()
        db = await get_db()
        try:
            cursor = await db.execute(
                "SELECT config FROM gamification_configs "
                "WHERE simulation_id = ?",
                (simulation_id,),
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            return json.loads(row["config"])
        except Exception as e:
            logger.warning(f"Failed to get gamification config from DB: {e}")
            return None
        finally:
            await db.close()

    async def save_scores(
        self,
        simulation_id: str,
        scores: dict[str, Any],
        leaderboard: dict[str, Any],
    ) -> None:
        """Save scores and leaderboard for a simulation."""
        await ensure_tables()
        db = await get_db()
        try:
            now = _utc_now_iso()
            await db.execute(
                """
                INSERT INTO gamification_configs
                    (simulation_id, config, scores, leaderboard, updated_at)
                VALUES (?, '{}', ?, ?, ?)
                ON CONFLICT(simulation_id) DO UPDATE SET
                    scores = excluded.scores,
                    leaderboard = excluded.leaderboard,
                    updated_at = excluded.updated_at
                """,
                (
                    simulation_id,
                    json.dumps(scores),
                    json.dumps(leaderboard),
                    now,
                ),
            )
            await db.commit()
        except Exception as e:
            logger.warning(f"Failed to save scores to DB: {e}")
        finally:
            await db.close()

    async def get_scores(self, simulation_id: str) -> dict[str, Any] | None:
        """Get scores for a simulation."""
        await ensure_tables()
        db = await get_db()
        try:
            cursor = await db.execute(
                "SELECT scores FROM gamification_configs "
                "WHERE simulation_id = ?",
                (simulation_id,),
            )
            row = await cursor.fetchone()
            if row is None or row["scores"] is None:
                return None
            return json.loads(row["scores"])
        except Exception as e:
            logger.warning(f"Failed to get scores from DB: {e}")
            return None
        finally:
            await db.close()

    async def get_leaderboard(
        self, simulation_id: str
    ) -> dict[str, Any] | None:
        """Get leaderboard for a simulation."""
        await ensure_tables()
        db = await get_db()
        try:
            cursor = await db.execute(
                "SELECT leaderboard FROM gamification_configs "
                "WHERE simulation_id = ?",
                (simulation_id,),
            )
            row = await cursor.fetchone()
            if row is None or row["leaderboard"] is None:
                return None
            return json.loads(row["leaderboard"])
        except Exception as e:
            logger.warning(f"Failed to get leaderboard from DB: {e}")
            return None
        finally:
            await db.close()

    async def delete(self, simulation_id: str) -> bool:
        """Delete gamification data for a simulation."""
        await ensure_tables()
        db = await get_db()
        try:
            cursor = await db.execute(
                "DELETE FROM gamification_configs WHERE simulation_id = ?",
                (simulation_id,),
            )
            await db.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.warning(f"Failed to delete gamification data: {e}")
            return False
        finally:
            await db.close()


# Global repository instances
api_key_repo = APIKeyRepository()
webhook_repo = WebhookRepository()
custom_persona_repo = CustomPersonaRepository()
counterpart_repo = CounterpartRepository()
cross_simulation_repo = CrossSimulationRepository()
gamification_repo = GamificationRepository()
