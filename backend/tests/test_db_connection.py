"""Tests for the shared DB connection utilities (app.db.connection).

Verifies that:
- utc_now_iso() returns a valid ISO-8601 UTC string
- get_fresh_db() opens a real aiosqlite connection to a temp DB
- init_schema() creates all expected core tables
- get_db() raises before init_schema() is called
- get_db() returns the connection after init_schema()
- close_database() tears down the persistent connection
- DB_PATH is consistent across all three DB layers' imports
"""

import asyncio
import threading
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

import app.db.connection as conn_mod

# ---------------------------------------------------------------------------
# utc_now_iso
# ---------------------------------------------------------------------------


def test_utc_now_iso_is_valid_iso():
    ts = conn_mod.utc_now_iso()
    # Must parse without error
    dt = datetime.fromisoformat(ts)
    assert dt.tzinfo is not None, "timestamp must include timezone info"
    assert dt.tzinfo == timezone.utc or dt.utcoffset().total_seconds() == 0


def test_utc_now_iso_returns_string():
    assert isinstance(conn_mod.utc_now_iso(), str)


def test_get_db_init_lock_is_singleton_across_threads():
    """Concurrent OS threads must not create duplicate asyncio.Lock instances."""
    original = conn_mod._db_init_lock
    try:
        conn_mod._db_init_lock = None
        results: list[asyncio.Lock] = []
        barrier = threading.Barrier(32)

        def worker() -> None:
            barrier.wait()
            results.append(conn_mod._get_db_init_lock())

        threads = [threading.Thread(target=worker) for _ in range(32)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len({id(x) for x in results}) == 1
    finally:
        conn_mod._db_init_lock = original


# ---------------------------------------------------------------------------
# get_fresh_db
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_fresh_db_returns_connection(tmp_path):
    db_path = tmp_path / "test.db"
    with patch.object(conn_mod, "DB_PATH", db_path), patch.object(conn_mod, "_DB_DIR", tmp_path):
        db = await conn_mod.get_fresh_db()
        try:
            # Basic sanity: can execute a simple query
            cursor = await db.execute("SELECT 1")
            row = await cursor.fetchone()
            assert row[0] == 1
        finally:
            await db.close()


# ---------------------------------------------------------------------------
# init_schema / get_db / close_database
# ---------------------------------------------------------------------------


@pytest.fixture
async def initialized_db(tmp_path):
    """Initialize a schema in a temp directory, yield, then close.

    Uses only the public close_database() API to reset state rather than
    directly assigning to the private conn_mod._db attribute.
    """
    db_path = tmp_path / "test.db"
    with patch.object(conn_mod, "DB_PATH", db_path), patch.object(conn_mod, "_DB_DIR", tmp_path):
        # Ensure we start with no connection using the public teardown API.
        await conn_mod.close_database()
        await conn_mod.init_schema()
        yield
        await conn_mod.close_database()


@pytest.mark.asyncio
async def test_get_db_raises_before_init(tmp_path):
    """get_db() must raise RuntimeError when called before init_schema()."""
    db_path = tmp_path / "pre_init_test.db"
    with patch.object(conn_mod, "DB_PATH", db_path), patch.object(conn_mod, "_DB_DIR", tmp_path):
        # Tear down any open connection so we start from an uninitialised state.
        await conn_mod.close_database()
        with pytest.raises(RuntimeError, match="not initialized"):
            await conn_mod.get_db()


@pytest.mark.asyncio
async def test_get_db_returns_connection_after_init(initialized_db):
    db = await conn_mod.get_db()
    assert db is not None


@pytest.mark.asyncio
async def test_init_schema_creates_core_tables(initialized_db):
    """All core tables must exist after init_schema()."""
    db = await conn_mod.get_db()
    cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = {row[0] for row in await cursor.fetchall()}

    expected = {
        "simulations",
        "seeds",
        "audit_events",
        "scenario_branches",
        "annotations",
        "chat_history",
        "agent_memories",
    }
    missing = expected - tables
    assert not missing, f"Missing tables after init_schema: {missing}"


@pytest.mark.asyncio
async def test_close_database_resets_connection(tmp_path):
    db_path = tmp_path / "close_test.db"
    with patch.object(conn_mod, "DB_PATH", db_path), patch.object(conn_mod, "_DB_DIR", tmp_path):
        await conn_mod.close_database()  # ensure clean start
        await conn_mod.init_schema()
        assert conn_mod._db is not None

        await conn_mod.close_database()
        assert conn_mod._db is None


# ---------------------------------------------------------------------------
# DDL constants sanity
# ---------------------------------------------------------------------------


def test_integration_ddl_is_non_empty():
    assert len(conn_mod.INTEGRATION_DDL.strip()) > 0


def test_llm_ddl_is_non_empty():
    assert len(conn_mod.LLM_DDL.strip()) > 0


def test_integration_ddl_contains_api_keys_table():
    assert "api_keys" in conn_mod.INTEGRATION_DDL


def test_llm_ddl_contains_fine_tuning_jobs():
    assert "fine_tuning_jobs" in conn_mod.LLM_DDL


# ---------------------------------------------------------------------------
# DB_PATH consistency — all three DB layers must point to the same file
# ---------------------------------------------------------------------------


def test_db_path_consistent_across_layers():
    """All three DB layers resolve to the same database file path."""
    # app.db.connection is the source of truth
    _ = conn_mod.DB_PATH  # ensure module exposes a concrete path

    # api_integrations/database.py uses get_fresh_db from conn_mod → same path
    import app.api_integrations.database as ai_db

    # Verify it imports from app.db.connection (not a local _DB_PATH copy)
    assert not hasattr(ai_db, "_DB_PATH"), (
        "api_integrations/database.py should not define its own _DB_PATH — " "it must delegate to app.db.connection"
    )

    # llm/database.py uses get_fresh_db from conn_mod → same path
    import app.llm.database as llm_db

    assert not hasattr(llm_db, "_DB_PATH"), (
        "llm/database.py should not define its own _DB_PATH — " "it must delegate to app.db.connection"
    )
