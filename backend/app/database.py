"""SQLite persistence layer for ScenarioLab backend — backwards-compat wrapper.

All repository classes have been extracted into focused modules under
``app/db/``. This file re-exports everything so existing importers continue
working without modification.

New code should import directly from the domain modules:
    from app.db.simulations import SimulationRepository
    from app.db.seeds import SeedRepository
    etc.
"""

import logging

from app.db.annotations import AnnotationRepository
from app.db.audit import AuditTrailRepository
from app.db.branches import BranchRepository
from app.db.chat import ChatHistoryRepository
from app.db.connection import (
    close_database,
    get_db,
)
from app.db.connection import (
    init_schema as _init_schema,
)
from app.db.memories import AgentMemoryRepository
from app.db.seeds import SeedRepository
from app.db.simulations import SimulationRepository

logger = logging.getLogger(__name__)


async def init_database() -> None:
    """Initialize the SQLite database and create all tables.

    This is the entry point used by ``app.main`` at startup. It calls
    ``app.db.connection.init_schema`` which owns all DDL.
    """
    await _init_schema()
    logger.info("Database tables initialized")


__all__ = [
    # lifecycle
    "init_database",
    "close_database",
    "get_db",
    # repositories
    "SimulationRepository",
    "SeedRepository",
    "AuditTrailRepository",
    "BranchRepository",
    "AnnotationRepository",
    "ChatHistoryRepository",
    "AgentMemoryRepository",
]
