"""API key authentication for third-party integrations."""

import asyncio
import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

from app.api_integrations.database import api_key_repo, ensure_tables
from app.config import settings

logger = logging.getLogger(__name__)


def hash_api_key(plaintext: str) -> str:
    """SHA-256 hex digest of an API key (never store plaintext at rest)."""
    return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()


def _mask_prefix(plaintext: str) -> str:
    if len(plaintext) <= 8:
        return "****"
    return f"{plaintext[:4]}...{plaintext[-4:]}"


def _looks_like_sha256_hex(value: str) -> bool:
    if len(value) != 64:
        return False
    return all(c in "0123456789abcdef" for c in value.lower())


class APIKey(BaseModel):
    """An API key with metadata.

    ``key`` holds plaintext only immediately after generation (returned once to
    the caller). Persisted storage and ``_key_lookup`` use SHA-256 hashes.
    """

    key_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    key: str = ""  # plaintext only at creation time; empty after load
    key_prefix: str = ""  # masked display form e.g. abcd...wxyz
    name: str
    permissions: list[str] = []  # e.g. ["read:simulations"]
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_used_at: str | None = None
    active: bool = True
    metadata: dict[str, Any] = {}


class APIKeyManager:
    """Manages API keys for third-party access.

    Uses SQLite persistence with in-memory cache for performance.
    """

    def __init__(self):
        self._keys: dict[str, APIKey] = {}  # key_id -> APIKey
        self._key_lookup: dict[str, str] = {}  # key hash -> key_id
        self._initialized = False
        self._init_lock = asyncio.Lock()

    async def _ensure_loaded(self) -> None:
        """Ensure keys are loaded from database."""
        if self._initialized:
            return
        async with self._init_lock:
            if self._initialized:
                return
            try:
                await ensure_tables()
                keys = await api_key_repo.list_all()
                for key_data in keys:
                    stored = str(key_data.get("key") or "")
                    meta = dict(key_data.get("metadata") or {})
                    prefix = str(meta.get("key_prefix") or "****")
                    api_key = APIKey(
                        key_id=key_data["key_id"],
                        key="",  # never keep plaintext from DB
                        key_prefix=prefix,
                        name=key_data["name"],
                        permissions=key_data.get("permissions") or [],
                        created_at=key_data.get("created_at") or datetime.now(timezone.utc).isoformat(),
                        last_used_at=key_data.get("last_used_at"),
                        active=bool(key_data.get("active", True)),
                        metadata=meta,
                    )
                    self._keys[api_key.key_id] = api_key
                    if not api_key.active or not stored:
                        continue
                    if _looks_like_sha256_hex(stored):
                        self._key_lookup[stored.lower()] = api_key.key_id
                    else:
                        # Legacy plaintext row — index by hash and rewrite at rest.
                        digest = hash_api_key(stored)
                        self._key_lookup[digest] = api_key.key_id
                        if not api_key.key_prefix or api_key.key_prefix == "****":
                            api_key.key_prefix = _mask_prefix(stored)
                            api_key.metadata["key_prefix"] = api_key.key_prefix
                        asyncio.create_task(self._persist_hashed_key(api_key, digest))
                self._initialized = True
                logger.info(f"Loaded {len(self._keys)} API keys from database")
            except Exception as e:
                logger.warning(f"Failed to load API keys from DB: {e}")

    async def _persist_hashed_key(self, api_key: APIKey, digest: str) -> None:
        try:
            payload = api_key.model_dump()
            payload["key"] = digest
            payload["metadata"] = {
                **api_key.metadata,
                "key_prefix": api_key.key_prefix,
            }
            await api_key_repo.save(payload)
        except Exception as e:
            logger.warning(f"Failed to migrate API key {api_key.key_id} to hash: {e}")

    def generate_key(
        self,
        name: str,
        permissions: list[str],
        metadata: dict[str, Any] | None = None,
    ) -> APIKey:
        """Generate a new API key.

        Returns the plaintext key once; only the SHA-256 hash is persisted.
        The in-memory cache is scrubbed immediately so ``get_key`` never
        re-exposes plaintext.
        """
        plaintext = secrets.token_hex(16)
        digest = hash_api_key(plaintext)
        prefix = _mask_prefix(plaintext)
        meta = dict(metadata or {})
        meta["key_prefix"] = prefix
        api_key = APIKey(
            name=name,
            key="",  # never retain plaintext in cache
            key_prefix=prefix,
            permissions=permissions,
            metadata=meta,
        )

        self._keys[api_key.key_id] = api_key
        self._key_lookup[digest] = api_key.key_id

        asyncio.create_task(self._save_key(api_key, digest))

        logger.info(f"Generated API key {api_key.key_id} for '{name}'")
        # One-time plaintext for the creation response only.
        return api_key.model_copy(update={"key": plaintext})

    async def _save_key(self, api_key: APIKey, digest: str) -> None:
        """Save API key hash to database."""
        try:
            payload = api_key.model_dump()
            payload["key"] = digest
            payload["metadata"] = {
                **api_key.metadata,
                "key_prefix": api_key.key_prefix,
            }
            await api_key_repo.save(payload)
        except Exception as e:
            logger.warning(f"Failed to persist API key to DB: {e}")

    async def validate_key(self, key: str) -> APIKey | None:
        """Validate an API key by hashing the provided secret and looking it up."""
        await self._ensure_loaded()

        digest = hash_api_key(key)
        key_id = self._key_lookup.get(digest)
        if not key_id:
            return None

        api_key = self._keys.get(key_id)
        if not api_key or not api_key.active:
            return None

        api_key.last_used_at = datetime.now(timezone.utc).isoformat()

        try:
            await api_key_repo.update_last_used(api_key.key_id)
        except Exception as e:
            logger.warning(f"Failed to update last_used for API key {api_key.key_id}: {e}")

        return api_key

    async def revoke_key(self, key_id: str) -> bool:
        """Revoke an API key and await DB durability."""
        await self._ensure_loaded()

        api_key = self._keys.get(key_id)
        if not api_key:
            return False

        api_key.active = False
        for digest, kid in list(self._key_lookup.items()):
            if kid == key_id:
                del self._key_lookup[digest]

        await api_key_repo.update_active(key_id, False)

        logger.info(f"Revoked API key {key_id}")
        return True

    async def list_keys(self) -> list[dict[str, Any]]:
        """List all API keys (with masked key values)."""
        await self._ensure_loaded()
        result = []
        for api_key in self._keys.values():
            result.append(
                {
                    "key_id": api_key.key_id,
                    "name": api_key.name,
                    "key": api_key.key_prefix or "****",
                    "permissions": api_key.permissions,
                    "created_at": api_key.created_at,
                    "last_used_at": api_key.last_used_at,
                    "active": api_key.active,
                }
            )
        return result

    async def get_key(self, key_id: str) -> APIKey | None:
        """Get a specific API key by ID (never includes plaintext)."""
        await self._ensure_loaded()
        api_key = self._keys.get(key_id)
        if api_key is None:
            return None
        if api_key.key:
            # Defensive scrub for any pre-fix in-memory entries.
            api_key.key = ""
        return api_key


# Global API key manager instance
api_key_manager = APIKeyManager()

# API Key header scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_admin_api_key(
    authorization: str | None = Header(None),
) -> None:
    """Require ``Authorization: Bearer`` matching ``settings.admin_api_key``."""
    expected = (settings.admin_api_key or "").strip()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API key management is disabled. Set ADMIN_API_KEY on the server.",
        )
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization: Bearer <admin key> required for API key management.",
        )
    # Prefix length matches case-insensitive "bearer " (validated above).
    token = authorization.removeprefix(authorization[:7]).strip()
    if not secrets.compare_digest(
        token.encode("utf-8"),
        expected.encode("utf-8"),
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin API key.",
        )


async def verify_api_key(
    x_api_key: str = Depends(api_key_header),
) -> APIKey:
    """FastAPI dependency to verify API key."""
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Include X-API-Key header.",
        )

    api_key = await api_key_manager.validate_key(x_api_key)
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API key.",
        )

    return api_key


def check_permission(api_key: APIKey, permission: str) -> bool:
    """Check if an API key has a specific permission."""
    if "admin" in api_key.permissions:
        return True

    resource = permission.split(":")[0] if ":" in permission else permission
    if f"{resource}:*" in api_key.permissions:
        return True

    return permission in api_key.permissions


def require_permission(permission: str):
    """Create a dependency that requires a specific permission."""

    async def permission_checker(
        api_key: APIKey = Depends(verify_api_key),
    ) -> APIKey:
        if not check_permission(api_key, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Required: {permission}",
            )
        return api_key

    return permission_checker
