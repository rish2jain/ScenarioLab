"""Shared SQLite connection utilities for MiroFish.

Single source of truth for:
- DB file path resolution
- Connection creation (persistent and per-request)
- UTC timestamp helper

Usage
-----
Persistent connection (main app lifecycle):
    from app.db.connection import get_db, init_schema, close_database
    await init_schema()          # call once at startup
    db = await get_db()          # reuse throughout the process

Per-request connection (api_integrations / llm patterns):
    from app.db.connection import get_fresh_db
    async with await get_fresh_db() as db:
        ...
"""

import asyncio
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Path — single definition used by all DB layers
# ---------------------------------------------------------------------------
_DB_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DB_PATH = _DB_DIR / "mirofish.db"

# ---------------------------------------------------------------------------
# Persistent connection (used by the main app lifecycle)
# ---------------------------------------------------------------------------
_db: aiosqlite.Connection | None = None

# Lock that serialises concurrent calls to init_schema() / close_database().
# Once _db is set it is only mutated by close_database(), so get_db() can
# read it without the lock (a None check after init is always safe because
# Python reference reads are atomic under the GIL, and asyncio is
# single-threaded).
# Initialized lazily (None here) to avoid binding to the import-time event loop.
_db_init_lock: asyncio.Lock | None = None
# Serialises creation of ``_db_init_lock`` across OS threads (asyncio alone is not enough).
_db_init_lock_creation_guard = threading.Lock()


def _get_db_init_lock() -> asyncio.Lock:
    """Return the module-level DB init lock, creating it on first call.

    Creating the Lock inside a running coroutine ensures it is bound to
    the active event loop rather than whichever loop (if any) existed at
    import time.

    The ``threading.Lock`` guard ensures only one thread assigns
    ``_db_init_lock``; without it, two threads could each create a different
    ``asyncio.Lock`` and one assignment would be lost.
    """
    global _db_init_lock  # noqa: PLW0603
    if _db_init_lock is None:
        with _db_init_lock_creation_guard:
            if _db_init_lock is None:
                _db_init_lock = asyncio.Lock()
    return _db_init_lock


def utc_now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


async def get_db() -> aiosqlite.Connection:
    """Return the persistent database connection.

    Raises
    ------
    RuntimeError
        If ``init_schema()`` has not been called first.
    """
    if _db is None:
        raise RuntimeError("Database not initialized. Call init_schema() (or init_database()) first.")
    return _db


async def get_fresh_db() -> aiosqlite.Connection:
    """Open and return a *new* per-call database connection.

    The caller is responsible for closing it (use ``async with`` or call
    ``await db.close()`` explicitly).  This is the connection pattern used
    by the api_integrations and llm DB layers.

    WAL mode note
    -------------
    SQLite's WAL journal mode is a *database-level* property stored in the
    database file itself.  Once ``init_schema()`` has set
    ``PRAGMA journal_mode=WAL``, every subsequent connection to the same
    file — including fresh per-request connections opened here — automatically
    operates in WAL mode without needing to re-issue the PRAGMA.  If
    ``get_fresh_db`` is called before ``init_schema()`` (e.g., in isolated
    unit tests against a temp file), the connection will use the default
    DELETE journal mode for that session; this is intentional for test
    isolation.
    """
    _DB_DIR.mkdir(parents=True, exist_ok=True)
    db = await aiosqlite.connect(str(DB_PATH))
    db.row_factory = aiosqlite.Row
    return db


async def init_schema(extra_ddl: str = "") -> None:
    """Initialize the persistent connection and create core tables.

    Concurrent callers are serialised via ``_db_init_lock``; the second
    caller exits early once it acquires the lock and sees ``_db`` is already
    set (idempotent).

    Parameters
    ----------
    extra_ddl:
        Optional additional ``CREATE TABLE IF NOT EXISTS`` statements to
        execute in the same transaction. Subsystems pass their own DDL here
        at startup so all schemas are created atomically.
    """
    global _db  # noqa: PLW0603

    if _db is not None:
        return

    async with _get_db_init_lock():
        if _db is not None:
            logger.warning("init_schema called but database already initialized")
            return

        _DB_DIR.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initializing SQLite database at {DB_PATH}")

        conn = await aiosqlite.connect(str(DB_PATH))

        try:
            conn.row_factory = aiosqlite.Row
            await conn.execute("PRAGMA journal_mode=WAL")
            await conn.executescript(_CORE_DDL + extra_ddl)
            await conn.commit()
            logger.info("Database schema initialized")
            _db = conn
        except Exception as e:
            await conn.close()
            logger.error(f"Database initialization failed: {e}")
            raise


# Keep legacy alias used by app/main.py
init_database = init_schema


async def close_database() -> None:
    """Close the persistent database connection."""
    global _db  # noqa: PLW0603
    async with _get_db_init_lock():
        if _db is not None:
            await _db.close()
            _db = None
            logger.info("Database connection closed")


# ---------------------------------------------------------------------------
# Core DDL — tables owned by app.database (simulations and related)
# ---------------------------------------------------------------------------
_CORE_DDL = """
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

CREATE TABLE IF NOT EXISTS reports (
    id TEXT PRIMARY KEY,
    simulation_id TEXT NOT NULL,
    simulation_name TEXT NOT NULL,
    status TEXT NOT NULL,
    report_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

# ---------------------------------------------------------------------------
# Integration-layer DDL (api_integrations subsystem)
# ---------------------------------------------------------------------------
INTEGRATION_DDL = """
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

# ---------------------------------------------------------------------------
# LLM-layer DDL
# ---------------------------------------------------------------------------
LLM_DDL = """
CREATE TABLE IF NOT EXISTS fine_tuning_jobs (
    job_id TEXT PRIMARY KEY,
    dataset_id TEXT,
    base_model TEXT NOT NULL,
    lora_config TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    progress REAL DEFAULT 0.0,
    created_at TEXT NOT NULL,
    completed_at TEXT,
    metrics TEXT,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS fine_tuning_datasets (
    dataset_id TEXT PRIMARY KEY,
    data_type TEXT NOT NULL,
    num_examples INTEGER DEFAULT 0,
    format TEXT DEFAULT 'jsonl',
    preview_samples TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS lora_adapters (
    adapter_id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    base_model TEXT NOT NULL,
    domain TEXT NOT NULL,
    size_mb REAL DEFAULT 0.0,
    created_at TEXT NOT NULL,
    performance_metrics TEXT,
    active BOOLEAN DEFAULT 0
);

CREATE TABLE IF NOT EXISTS fine_tuning_benchmarks (
    benchmark_id TEXT PRIMARY KEY,
    domain TEXT NOT NULL,
    questions TEXT NOT NULL,
    evaluation_criteria TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS market_intelligence_configs (
    simulation_id TEXT PRIMARY KEY,
    config TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS market_intelligence_cache (
    simulation_id TEXT PRIMARY KEY,
    data TEXT NOT NULL,
    injected_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS voice_conversations (
    id TEXT PRIMARY KEY,
    simulation_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    messages TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS voice_audio_cache (
    audio_id TEXT PRIMARY KEY,
    simulation_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    audio_data BLOB NOT NULL,
    created_at TEXT NOT NULL
);
"""
