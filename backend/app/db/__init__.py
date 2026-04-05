"""Database connection package for ScenarioLab backend.

Exposes only the connection utilities. Repository classes are imported
directly from their submodules to avoid loading heavy dependencies eagerly.

Usage
-----
Connection utilities:
    from app.db import get_db, get_fresh_db, init_schema, close_database

Repository classes (import from submodules directly):
    from app.db.simulations import SimulationRepository
    from app.db.seeds import SeedRepository
    from app.db.audit import AuditTrailRepository
    from app.db.branches import BranchRepository
    from app.db.annotations import AnnotationRepository
    from app.db.chat import ChatHistoryRepository
    from app.db.memories import AgentMemoryRepository
"""

from app.db.connection import (
    DB_PATH,
    INTEGRATION_DDL,
    LLM_DDL,
    close_database,
    get_db,
    get_fresh_db,
    init_schema,
    utc_now_iso,
)

__all__ = [
    "DB_PATH",
    "INTEGRATION_DDL",
    "LLM_DDL",
    "close_database",
    "get_db",
    "get_fresh_db",
    "init_schema",
    "utc_now_iso",
]
