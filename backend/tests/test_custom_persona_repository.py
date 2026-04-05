"""Tests for CustomPersonaRepository (custom_personas in api_integrations)."""

import json
from unittest.mock import patch

import pytest

import app.api_integrations.database as ai_db
import app.db.connection as conn_mod


@pytest.fixture
async def custom_persona_repo(tmp_path):
    """Isolated integration DB and a reset CustomPersonaRepository."""
    db_path = tmp_path / "test.db"
    with (
        patch.object(conn_mod, "_DB_DIR", tmp_path),
        patch.object(conn_mod, "DB_PATH", db_path),
    ):
        await conn_mod.close_database()
        ai_db._initialized = False
        await ai_db.init_integration_tables()
        yield ai_db.custom_persona_repo
        ai_db._initialized = False
        await conn_mod.close_database()


@pytest.mark.asyncio
async def test_get_missing_returns_none(custom_persona_repo):
    assert await custom_persona_repo.get("nonexistent-persona-id") is None


@pytest.mark.asyncio
async def test_get_returns_saved_persona(custom_persona_repo):
    data = {"id": "p1", "name": "N", "role": "R"}
    await custom_persona_repo.save("p1", data)
    assert await custom_persona_repo.get("p1") == data


@pytest.mark.asyncio
async def test_get_does_not_swallow_invalid_json(custom_persona_repo):
    """Corrupt rows must raise (e.g. JSONDecodeError), not return None."""
    payload = {"id": "bad", "name": "x", "role": "y"}
    await custom_persona_repo.save("bad", payload)
    db = await conn_mod.get_fresh_db()
    try:
        await db.execute(
            "UPDATE custom_personas SET persona_data = ? WHERE persona_id = ?",
            ("not-json", "bad"),
        )
        await db.commit()
    finally:
        await db.close()

    with pytest.raises(json.JSONDecodeError):
        await custom_persona_repo.get("bad")
