import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.analytics.router import router as analytics_router
from app.api_integrations.router import router as api_v1_router
from app.config import settings
from app.database import close_database, init_database
from app.graph.neo4j_client import Neo4jClient
from app.graph.router import router as graph_router
from app.llm.database import init_llm_tables
from app.llm.router import router as llm_router
from app.mcp.router import router as mcp_router
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global Neo4j client instance
neo4j_client: Neo4jClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan handler for startup and shutdown events."""
    global neo4j_client
    logger.info("MiroFish backend starting up...")

    # Initialize SQLite database
    await init_database()

    # Initialize LLM tables
    try:
        await init_llm_tables()
        logger.info("LLM tables initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize LLM tables: {e}")

    # Initialize Neo4j connection
    try:
        neo4j_client = Neo4jClient(
            uri=settings.neo4j_uri,
            user=settings.neo4j_user,
            password=settings.neo4j_password,
        )
        await neo4j_client.connect()
        logger.info("Neo4j connection established")
    except Exception as e:
        logger.error(f"Failed to connect to Neo4j: {e}")
        logger.warning("Continuing without Neo4j - graph features unavailable")
        neo4j_client = None

    yield

    # Shutdown
    logger.info("MiroFish backend shutting down...")
    await close_database()
    if neo4j_client:
        await neo4j_client.close()
        logger.info("Neo4j connection closed")


app = FastAPI(
    title="MiroFish API",
    description="AI war-gaming platform for strategy consultants",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware - restricted origins (extend ALLOWED_ORIGINS for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )
        return response


app.add_middleware(SecurityHeadersMiddleware)


@app.get("/api/health", tags=["health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "mirofish-backend"}


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
    return {
        "message": "Welcome to MiroFish API",
        "docs": "/docs",
        "health": "/api/health",
        "personas": "/api/personas",
        "playbooks": "/api/playbooks",
        "simulations": "/api/simulations",
        "reports": "/api/reports",
        "mcp": "/api/mcp",
    }
