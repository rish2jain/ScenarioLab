"""API key authentication for third-party integrations."""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

from app.api_integrations.database import api_key_repo, ensure_tables

logger = logging.getLogger(__name__)


class APIKey(BaseModel):
    """An API key with metadata."""

    key_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    key: str = Field(
        default_factory=lambda: str(uuid.uuid4()).replace("-", "")
    )
    name: str
    permissions: list[str] = []  # e.g. ["read:simulations"]
    created_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )
    last_used_at: str | None = None
    active: bool = True
    metadata: dict[str, Any] = {}


class APIKeyManager:
    """Manages API keys for third-party access.

    Uses SQLite persistence with in-memory cache for performance.
    """

    def __init__(self):
        self._keys: dict[str, APIKey] = {}  # key_id -> APIKey
        self._key_lookup: dict[str, str] = {}  # key value -> key_id
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
                    api_key = APIKey(**key_data)
                    self._keys[api_key.key_id] = api_key
                    if api_key.active:
                        self._key_lookup[api_key.key] = api_key.key_id
                self._initialized = True
                logger.info(f"Loaded {len(self._keys)} API keys from database")
            except Exception as e:
                logger.warning(f"Failed to load API keys from DB: {e}")

    def generate_key(
        self,
        name: str,
        permissions: list[str],
        metadata: dict[str, Any] | None = None,
    ) -> APIKey:
        """Generate a new API key.

        Args:
            name: Human-readable name for the key
            permissions: List of permissions granted to this key
            metadata: Optional additional metadata

        Returns:
            The generated APIKey
        """
        api_key = APIKey(
            name=name,
            permissions=permissions,
            metadata=metadata or {},
        )

        # Store key in memory
        self._keys[api_key.key_id] = api_key
        self._key_lookup[api_key.key] = api_key.key_id

        # Persist to database (async fire-and-forget)
        asyncio.create_task(self._save_key(api_key))

        logger.info(f"Generated API key {api_key.key_id} for '{name}'")
        return api_key

    async def _save_key(self, api_key: APIKey) -> None:
        """Save API key to database."""
        try:
            await api_key_repo.save(api_key.model_dump())
        except Exception as e:
            logger.warning(f"Failed to persist API key to DB: {e}")

    def validate_key(self, key: str) -> APIKey | None:
        """Validate an API key.

        Args:
            key: The API key value to validate

        Returns:
            APIKey if valid, None otherwise
        """
        key_id = self._key_lookup.get(key)
        if not key_id:
            return None

        api_key = self._keys.get(key_id)
        if not api_key:
            return None

        if not api_key.active:
            return None

        # Update last used in memory
        api_key.last_used_at = datetime.utcnow().isoformat()

        # Update last used in DB (async fire-and-forget)
        asyncio.create_task(
            api_key_repo.update_last_used(api_key.key_id)
        )

        return api_key

    def revoke_key(self, key_id: str) -> bool:
        """Revoke an API key.

        Args:
            key_id: The ID of the key to revoke

        Returns:
            True if revoked, False if not found
        """
        api_key = self._keys.get(key_id)
        if not api_key:
            return False

        api_key.active = False
        # Remove from lookup
        if api_key.key in self._key_lookup:
            del self._key_lookup[api_key.key]

        # Update in DB (async fire-and-forget)
        asyncio.create_task(api_key_repo.update_active(key_id, False))

        logger.info(f"Revoked API key {key_id}")
        return True

    async def list_keys(self) -> list[dict[str, Any]]:
        """List all API keys (with masked key values).

        Returns:
            List of API key info dictionaries
        """
        await self._ensure_loaded()
        result = []
        for api_key in self._keys.values():
            # Mask the key value
            masked_key = (
                api_key.key[:4] + "..." + api_key.key[-4:]
                if len(api_key.key) > 8
                else "****"
            )
            result.append({
                "key_id": api_key.key_id,
                "name": api_key.name,
                "key": masked_key,
                "permissions": api_key.permissions,
                "created_at": api_key.created_at,
                "last_used_at": api_key.last_used_at,
                "active": api_key.active,
            })
        return result

    async def get_key(self, key_id: str) -> APIKey | None:
        """Get a specific API key by ID.

        Args:
            key_id: The key ID

        Returns:
            APIKey or None
        """
        await self._ensure_loaded()
        return self._keys.get(key_id)


# Global API key manager instance
api_key_manager = APIKeyManager()

# API Key header scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(
    x_api_key: str = Depends(api_key_header),
) -> APIKey:
    """FastAPI dependency to verify API key.

    Args:
        x_api_key: The API key from the X-API-Key header

    Returns:
        The validated APIKey

    Raises:
        HTTPException: If API key is missing or invalid
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Include X-API-Key header.",
        )

    api_key = api_key_manager.validate_key(x_api_key)
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API key.",
        )

    return api_key


def check_permission(api_key: APIKey, permission: str) -> bool:
    """Check if an API key has a specific permission.

    Args:
        api_key: The API key to check
        permission: The permission to verify

    Returns:
        True if permission is granted
    """
    # Admin permission grants all access
    if "admin" in api_key.permissions:
        return True

    # Check for wildcard permission
    resource = permission.split(":")[0] if ":" in permission else permission
    if f"{resource}:*" in api_key.permissions:
        return True

    return permission in api_key.permissions


def require_permission(permission: str):
    """Create a dependency that requires a specific permission.

    Args:
        permission: The required permission

    Returns:
        Dependency function
    """
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
