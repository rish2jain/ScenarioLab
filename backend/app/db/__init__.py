"""Shared database utilities for MiroFish backend.

This package provides a single source of truth for SQLite connection
management. All DB layers (core, api_integrations, llm) import from here.
"""

from app.db.connection import (
    DB_PATH,
    close_database,
    get_db,
    get_fresh_db,
    init_schema,
    utc_now_iso,
)

__all__ = [
    "DB_PATH",
    "close_database",
    "get_db",
    "get_fresh_db",
    "init_schema",
    "utc_now_iso",
]
