# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MiroFish is an AI-powered war-gaming/simulation platform for strategy consultants. It enables users to create competitive simulations with AI-driven agents representing different stakeholders (competitors, regulators, customers, etc.) and generates analytical reports from simulation outcomes.

## Architecture

**Monorepo** with three main parts:

- **`backend/`** — Python (FastAPI + uv) API server on port 5001
- **`frontend/`** — TypeScript (Next.js 14 + Tailwind + Zustand) on port 3000
- **Neo4j** — Graph database for knowledge graph / GraphRAG, runs via Docker on ports 7474/7687

The frontend proxies `/api/*` requests to the backend via Next.js rewrites (`next.config.mjs`). The backend degrades gracefully if Neo4j is unavailable.

### Backend Modules (`backend/app/`)

| Module | Purpose |
|--------|---------|
| `simulation/` | Core simulation engine: agent orchestration, turn rules, branching scenarios, Monte Carlo, hallucination detection, visibility/fog-of-war, gamification, batch runs |
| `personas/` | Stakeholder persona archetypes, interview-based persona extraction, persona library |
| `playbooks/` | Simulation templates (M&A, pricing war, etc.), auto-template generation, copilot, vertical industry libraries |
| `graph/` | Neo4j client, entity extraction, GraphRAG, seed data processing, memory layer |
| `llm/` | Multi-provider LLM abstraction (OpenAI, Anthropic, Ollama, llama.cpp) via factory pattern |
| `analytics/` | Post-simulation analytics agent, emergent pattern detection, metrics export |
| `reports/` | Report generation agent, narrative builder, deliverable templates, exporters (PDF, PPTX, etc.) |
| `research/` | Autoresearch service: web search (Tavily), SEC EDGAR, EUR-Lex, LLM synthesis |
| `mcp/` | MCP (Model Context Protocol) server for tool-use integration |
| `seed/` | Multilanguage seed data support |
| `cli.py` | CLI entry point (`mirofish-sim`) for headless simulation runs |
| `cost_estimator.py` | LLM token cost estimation |

### Frontend Structure (`frontend/src/`)

- `app/` — Next.js App Router pages: dashboard (`page.tsx`), `/simulations`, `/playbooks`, `/reports`, `/upload`
- `components/` — UI components (`ui/`), simulation views, report views, annotation tools, visualization
- `lib/api.ts` — API client with mock data fallback when backend is unavailable
- `lib/store.ts` — Zustand stores for simulation and app state
- `lib/types.ts` — Shared TypeScript type definitions

### Configuration

All config via environment variables loaded from `.env` at project root (see `.env.example`):
- `LLM_PROVIDER` / `LLM_API_KEY` / `LLM_MODEL_NAME` — LLM backend selection
- `NEO4J_URI` / `NEO4J_USER` / `NEO4J_PASSWORD` — Graph database
- `MIRO_API_TOKEN` — Miro board integration
- `MCP_SERVER_ENABLED` — Toggle MCP server
- `TAVILY_API_KEY` — Web search for autoresearch (Tavily API)
- `SEC_USER_AGENT` — SEC EDGAR API user agent string

Backend settings are managed via Pydantic `BaseSettings` in `backend/app/config.py`.

## Common Commands

```bash
# Setup everything (install all deps)
npm run setup:all

# Start both backend + frontend (concurrent)
npm run dev

# Start with Neo4j + full stack
./start.sh                    # local mode
./start.sh --docker           # Docker Compose mode
./start.sh --no-neo4j         # skip Neo4j, backend degrades gracefully
./start.sh --skip-install     # skip dependency installation

# Backend only
cd backend && uv run uvicorn app.main:app --reload --port 5001

# Frontend only
cd frontend && npm run dev

# CLI simulation (headless)
cd backend && uv run mirofish-sim simulate --playbook <name> --seed <file>
cd backend && uv run mirofish-sim list-playbooks

# Backend linting/formatting
cd backend && uv run ruff check .
cd backend && uv run black .
cd backend && uv run mypy app/

# Frontend linting/type checking
cd frontend && npm run lint
cd frontend && npx tsc --noEmit

# Frontend build
cd frontend && npm run build
```

## Key Design Decisions

- **LLM Provider Abstraction**: `backend/app/llm/` uses a factory pattern (`factory.py`) with a base `provider.py` protocol. Adding a new LLM provider means implementing the protocol and registering in the factory.
- **Mock Data Fallback**: The frontend API client (`frontend/src/lib/api.ts`) includes extensive mock data so the UI is functional without a running backend.
- **Simulation Engine**: Multi-turn agent simulation with branching scenarios, Monte Carlo analysis, and fog-of-war visibility rules. The `simulation/engine.py` orchestrates turns; `simulation/agent.py` handles individual agent behavior.
- **GraphRAG**: The graph module combines Neo4j knowledge graph with LLM-based entity extraction for retrieval-augmented generation over structured relationships.
- **No test suite yet**: There are no existing tests. When adding tests, use `pytest` for backend and configure a test runner for the frontend.
