import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.analytics.router import router as analytics_router
from app.api_integrations.router import router as api_v1_router
from app.config import settings
from app.db.connection import close_database, get_db, init_schema
from app.graph.graphiti_service import start_graphiti, stop_graphiti
from app.graph.neo4j_client import Neo4jClient, register_application_neo4j_client
from app.graph.router import (
    reset_graphrag_cache,
    start_seed_extraction_lock_cleanup_task,
    stop_seed_extraction_lock_cleanup_task,
)
from app.graph.router import (
    router as graph_router,
)
from app.llm.database import init_llm_tables
from app.llm.router import router as llm_router
from app.mcp.router import router as mcp_router
from app.mcp.server import mcp_server
from app.middleware_auth import SharedSecretAuthMiddleware
from app.middleware_request_id import RequestIdMiddleware
from app.personas.router import router as personas_router
from app.playbooks.router import router as playbooks_router
from app.reports.router import router as reports_router
from app.research.router import router as research_router
from app.simulation.advanced_router import router as advanced_router
from app.simulation.router import router as simulation_router
from app.simulation.voice_router import router as voice_router

# Allowed origins for CORS - restrict in production
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Configure logging (request middleware adds structured request lines)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global Neo4j client instance
neo4j_client: Neo4jClient | None = None

_WEAK_NEO4J_PASSWORDS = frozenset({"", "password", "changeme", "neo4j"})


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan handler for startup and shutdown events."""
    global neo4j_client
    logger.info("ScenarioLab backend starting up...")

    # Initialize SQLite database
    await init_schema()
    logger.info("Database tables initialized")

    # Initialize LLM tables
    try:
        await init_llm_tables()
        logger.info("LLM tables initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize LLM tables: {e}")

    # Initialize Neo4j connection (shared with graph router via register_application_neo4j_client)
    neo4j_password = (settings.neo4j_password or "").strip()
    if neo4j_password.lower() in _WEAK_NEO4J_PASSWORDS:
        logger.warning(
            "NEO4J_PASSWORD is unset or weak; skipping Neo4j connect. "
            "Set a strong NEO4J_PASSWORD in .env to enable graph features."
        )
        neo4j_client = None
    else:
        try:
            neo4j_client = Neo4jClient(
                uri=settings.neo4j_uri,
                user=settings.neo4j_user,
                password=neo4j_password,
            )
            await neo4j_client.connect()
            logger.info("Neo4j connection established")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            logger.warning("Continuing without Neo4j - graph features unavailable")
            neo4j_client = None

    register_application_neo4j_client(neo4j_client)

    start_seed_extraction_lock_cleanup_task()

    try:
        await start_graphiti()
    except Exception as e:
        logger.warning("Graphiti startup skipped: %s", e)

    if (settings.api_shared_secret or "").strip():
        logger.info("API shared-secret auth is ENABLED for /api/*")
    else:
        logger.warning("API shared-secret auth is DISABLED (API_SHARED_SECRET unset) — " "suitable for local lab only")

    yield

    # Shutdown
    logger.info("ScenarioLab backend shutting down...")
    try:
        await mcp_server.shutdown_background_simulation()
    except Exception as e:
        logger.warning("MCP background simulation shutdown: %s", e)
    await stop_seed_extraction_lock_cleanup_task()
    try:
        await stop_graphiti()
    except Exception as e:
        logger.warning("Graphiti shutdown: %s", e)
    await close_database()
    reset_graphrag_cache()
    if neo4j_client:
        await neo4j_client.close()
        logger.info("Neo4j connection closed")
    register_application_neo4j_client(None)


_docs_enabled = bool(settings.debug)
app = FastAPI(
    title="ScenarioLab API",
    description="AI war-gaming platform for strategy consultants",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if _docs_enabled else None,
    redoc_url="/redoc" if _docs_enabled else None,
    openapi_url="/openapi.json" if _docs_enabled else None,
)

# CORS middleware - restricted origins (extend ALLOWED_ORIGINS for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "X-API-Key",
        "X-ScenarioLab-Secret",
        "X-Request-ID",
        "X-Client-Upload-Id",
    ],
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(self), geolocation=()"
        return response


# Middleware order: last added runs first on the request (outermost).
# SecurityHeaders must be outermost so 401s from SharedSecretAuth still get headers.
app.add_middleware(SharedSecretAuthMiddleware)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

@app.get("/api/health", tags=["health"])
async def health_check():
    """Liveness probe — process is up."""
    return {"status": "ok", "service": "scenariolab-backend"}


@app.get("/api/ready", tags=["health"])
async def readiness_check():
    """Readiness probe — SQLite reachable; Neo4j optional."""
    checks: dict[str, str] = {}
    overall = "ok"

    try:
        db = await get_db()
        await db.execute("SELECT 1")
        checks["sqlite"] = "ok"
    except Exception as e:
        logger.warning("Readiness sqlite check failed: %s", e)
        checks["sqlite"] = "error"
        overall = "degraded"

    if neo4j_client is not None:
        try:
            if not neo4j_client.is_connected:
                checks["neo4j"] = "skipped"
            else:
                await neo4j_client.verify_connectivity()
                checks["neo4j"] = "ok"
        except Exception as e:
            logger.warning("Readiness neo4j check failed: %s", e)
            checks["neo4j"] = "error"
            overall = "degraded"
    else:
        checks["neo4j"] = "skipped"

    status_code = 200 if overall == "ok" else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": overall,
            "service": "scenariolab-backend",
            "checks": checks,
        },
    )


# Include routers
app.include_router(llm_router)
app.include_router(graph_router)
app.include_router(personas_router)
app.include_router(playbooks_router)
app.include_router(simulation_router)
app.include_router(advanced_router)
app.include_router(analytics_router)
app.include_router(reports_router)
app.include_router(mcp_router)
app.include_router(voice_router)
app.include_router(api_v1_router)
app.include_router(research_router)


@app.get("/")
async def root():
    """Root endpoint."""
    payload = {
        "message": "Welcome to ScenarioLab API",
        "health": "/api/health",
        "ready": "/api/ready",
        "personas": "/api/personas",
        "playbooks": "/api/playbooks",
        "simulations": "/api/simulations",
        "reports": "/api/reports",
        "mcp": "/api/mcp",
    }
    if _docs_enabled:
        payload["docs"] = "/docs"
    return payload
