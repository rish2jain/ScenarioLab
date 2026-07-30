"""API key hashing at rest + validate/revoke durability."""

from unittest.mock import AsyncMock, patch

import pytest

from app.api_integrations.auth import APIKey, APIKeyManager, hash_api_key


@pytest.mark.asyncio
async def test_validate_key_loads_from_db_on_cold_start():
    manager = APIKeyManager()
    plaintext = "abcdef0123456789"
    stored = {
        "key_id": "kid-1",
        "key": hash_api_key(plaintext),
        "name": "cold-start",
        "permissions": ["read:simulations"],
        "created_at": "2026-01-01T00:00:00",
        "last_used_at": None,
        "active": True,
        "metadata": {"key_prefix": "abcd...6789"},
    }

    with (
        patch("app.api_integrations.auth.ensure_tables", new=AsyncMock()),
        patch(
            "app.api_integrations.auth.api_key_repo.list_all",
            new=AsyncMock(return_value=[stored]),
        ),
        patch(
            "app.api_integrations.auth.api_key_repo.update_last_used",
            new=AsyncMock(),
        ),
    ):
        result = await manager.validate_key(plaintext)

    assert result is not None
    assert result.key_id == "kid-1"
    assert manager._initialized is True


@pytest.mark.asyncio
async def test_validate_migrates_legacy_plaintext_row():
    manager = APIKeyManager()
    plaintext = "legacyplaintextkey01"
    stored = {
        "key_id": "kid-legacy",
        "key": plaintext,
        "name": "legacy",
        "permissions": [],
        "created_at": "2026-01-01T00:00:00",
        "last_used_at": None,
        "active": True,
        "metadata": {},
    }
    save = AsyncMock()

    with (
        patch("app.api_integrations.auth.ensure_tables", new=AsyncMock()),
        patch(
            "app.api_integrations.auth.api_key_repo.list_all",
            new=AsyncMock(return_value=[stored]),
        ),
        patch("app.api_integrations.auth.api_key_repo.save", save),
        patch(
            "app.api_integrations.auth.api_key_repo.update_last_used",
            new=AsyncMock(),
        ),
    ):
        result = await manager.validate_key(plaintext)
        # Allow migration task to schedule
        await asyncio_sleep_zero()

    assert result is not None
    assert result.key_id == "kid-legacy"
    save.assert_awaited_once()
    saved = save.await_args.args[0]
    assert saved["key"] == hash_api_key(plaintext)
    assert saved["key"] != plaintext


async def asyncio_sleep_zero():
    import asyncio

    await asyncio.sleep(0)


@pytest.mark.asyncio
async def test_revoke_key_awaits_db_update():
    manager = APIKeyManager()
    manager._initialized = True
    plaintext = "fedcba9876543210"
    digest = hash_api_key(plaintext)
    key = APIKey(
        key_id="kid-2",
        key="",
        key_prefix="fedc...3210",
        name="to-revoke",
        permissions=[],
        active=True,
    )
    manager._keys[key.key_id] = key
    manager._key_lookup[digest] = key.key_id

    update = AsyncMock()
    with patch("app.api_integrations.auth.api_key_repo.update_active", update):
        ok = await manager.revoke_key(key.key_id)

    assert ok is True
    update.assert_awaited_once_with(key.key_id, False)
    assert key.active is False
    assert digest not in manager._key_lookup


@pytest.mark.asyncio
async def test_generate_persists_hash_not_plaintext():
    manager = APIKeyManager()
    manager._initialized = True
    save = AsyncMock()

    with patch("app.api_integrations.auth.api_key_repo.save", save):
        api_key = manager.generate_key("n", ["read:simulations"])
        await asyncio_sleep_zero()

    assert api_key.key  # plaintext returned once
    assert save.await_count == 1
    saved = save.await_args.args[0]
    assert saved["key"] == hash_api_key(api_key.key)
    assert saved["key"] != api_key.key


@pytest.mark.asyncio
async def test_generate_scrubs_plaintext_from_cache_and_get_key():
    manager = APIKeyManager()
    manager._initialized = True

    with patch("app.api_integrations.auth.api_key_repo.save", new=AsyncMock()):
        created = manager.generate_key("once", ["read:simulations"])

    assert created.key  # one-time plaintext in creation response
    cached = manager._keys[created.key_id]
    assert cached.key == ""
    assert cached.key_prefix == created.key_prefix
    assert cached.key_prefix != ""

    fetched = await manager.get_key(created.key_id)
    assert fetched is not None
    assert fetched.key == ""
    assert fetched.key_prefix == created.key_prefix
    assert fetched.name == "once"
    # Lookup by hash still works with the returned plaintext.
    validated = await manager.validate_key(created.key)
    assert validated is not None
    assert validated.key_id == created.key_id
    assert validated.key == ""


@pytest.mark.asyncio
async def test_verify_api_key_dependency_loads_before_validate():
    from app.api_integrations.auth import verify_api_key

    manager = APIKeyManager()
    plaintext = "deadbeefcafebabe"
    stored = {
        "key_id": "kid-3",
        "key": hash_api_key(plaintext),
        "name": "dep",
        "permissions": ["read:simulations"],
        "created_at": "2026-01-01T00:00:00",
        "last_used_at": None,
        "active": True,
        "metadata": {"key_prefix": "dead...babe"},
    }

    with (
        patch("app.api_integrations.auth.api_key_manager", manager),
        patch("app.api_integrations.auth.ensure_tables", new=AsyncMock()),
        patch(
            "app.api_integrations.auth.api_key_repo.list_all",
            new=AsyncMock(return_value=[stored]),
        ),
        patch(
            "app.api_integrations.auth.api_key_repo.update_last_used",
            new=AsyncMock(),
        ),
    ):
        result = await verify_api_key(x_api_key=plaintext)

    assert result.key_id == "kid-3"
