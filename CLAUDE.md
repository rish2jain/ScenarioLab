# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**[`AGENTS.md`](./AGENTS.md)** points here so Codex and other tools that expect `AGENTS.md` do not need a duplicated copy.

## Project Overview

ScenarioLab is an AI-powered war-gaming/simulation platform for strategy consultants. It enables users to create competitive simulations with AI-driven agents representing different stakeholders (competitors, regulators, customers, etc.) and generates analytical reports from simulation outcomes.

## Architecture

**Monorepo** with three main parts:

- **`backend/`** — Python (FastAPI + uv) API server on port 5001
- **`frontend/`** — TypeScript (Next.js 16 + Tailwind CSS + Zustand) on port 3000
- **Neo4j** — Graph database for knowledge graph / GraphRAG, runs via Docker on ports 7474/7687

The frontend proxies `/api/*` requests to the backend via Next.js rewrites (`next.config.mjs`). The backend degrades gracefully if Neo4j is unavailable (falls back to SQLite).

### Backend Modules (`backend/app/`)

| Module | Purpose |
|--------|---------|
| `simulation/` | Core simulation engine: agent orchestration, turn rules, branching scenarios, Monte Carlo, hallucination detection, visibility/fog-of-war, gamification, batch runs, objective auto-parsing, response sanitization, cross-round memory |
| `personas/` | Stakeholder persona archetypes, interview-based persona extraction, persona library |
| `playbooks/` | Simulation templates (M&A, pricing war, etc.), auto-template generation, copilot, vertical industry libraries |
| `graph/` | Neo4j client, entity extraction, GraphRAG, seed data processing, memory layer |
| `llm/` | Multi-provider LLM abstraction via factory pattern — see providers below |
| `analytics/` | Post-simulation analytics agent (LLM-based sentiment when available, keyword fallback), emergent pattern detection, cross-simulation learning, metrics export |
| `reports/` | Report generation agent (parallel LLM calls), objective assessment, narrative builder, deliverable templates, exporters (PDF, PPTX, etc.), SQLite persistence |
| `research/` | Autoresearch service: web search (Tavily), SEC EDGAR, EUR-Lex, LLM synthesis |
| `mcp/` | MCP (Model Context Protocol) server for tool-use integration |
| `seed/` | Multilanguage seed data support; uploaded documents injected into agent prompts |
| `cli.py` | CLI entry point (`scenariolab-sim`) for headless simulation runs |
| `cost_estimator.py` | LLM token cost estimation |

### Database Layer (`backend/app/db/`)

Recently refactored from a monolithic `database.py` into domain-specific repositories:

| Repository | File | Responsibility |
|---|---|---|
| `connection.py` | Shared connection utilities | `get_db()` (persistent), `get_fresh_db()` (per-request), `init_schema()` |
| `simulations.py` | SimulationRepository | CRUD for simulations table |
| `seeds.py` | SeedRepository | Seed document storage and linking |
| `audit.py` | AuditTrailRepository | Event logging with SHA-256 hashing |
| `chat.py` | ChatHistoryRepository | Session messages with flattening |
| `memories.py` | AgentMemoryRepository | Agent memory persistence |
| `reports.py` | ReportRepository | Report persistence to SQLite (survives restarts) |

**Import convention**: New code imports directly from domain modules (`from app.db.simulations import SimulationRepository`). The legacy `backend/app/database.py` is a backward-compat wrapper that re-exports everything — do not add new code there.

SQLite with WAL mode via `aiosqlite`. Schema initialization is concurrent-safe with file locking.

### LLM Providers (`backend/app/llm/`)

| Provider key | File | Notes |
|---|---|---|
| `openai` | `openai_provider.py` | Default; requires `LLM_API_KEY` |
| `anthropic` | `anthropic_provider.py` | Requires `LLM_API_KEY` |
| `ollama` | `ollama_provider.py` | Local; no key needed |
| `llamacpp` | `llamacpp_provider.py` | Local; no key needed |
| `cli-claude` | `cli_claude_provider.py` | Shells out to the Claude CLI (native installer) |
| `cli-chatgpt` | `cli_chatgpt_provider.py` | Shells out to the OpenAI CLI (`pip install openai`) |
| `cli-gemini` | `cli_gemini_provider.py` | Shells out to the Gemini CLI |

All CLI providers wrap `proc.communicate()` with a **120 s `asyncio.wait_for` timeout** and properly terminate/kill/reap the subprocess on timeout. Set `LLM_PROVIDER=cli-claude` (or another cli-* value) in `.env` to use them.

### Frontend Structure (`frontend/src/`)

- `app/` — Next.js App Router pages: dashboard (`page.tsx`), `/simulations`, `/simulations/new` (5-step wizard), `/playbooks`, `/reports`, `/upload`
- `components/` — UI components (`ui/`), simulation views, report views, annotation tools, visualization
- `lib/api.ts` — API client; normalises backend `snake_case` responses into the frontend's `camelCase` types; falls back to mock data when backend is unavailable
- `lib/store.ts` — Zustand stores (`usePlaybookStore`, `useSimulationStore`)
- `lib/types.ts` — Shared TypeScript type definitions

### Simulation Creation Wizard (`/simulations/new`)

Five-step flow:
1. **Select Playbook** — lazy-loads full playbook detail (roster) on selection; stale-fetch guard via `cancelled` flag
2. **Configure Agents** — adjustable counts per role; total updates live
3. **Seed Documents** — optional; select previously uploaded docs or upload inline; passes `seedIds` to create request
4. **Set Parameters** — rounds, environment type, model, Monte Carlo iterations
5. **Review & Launch** — sends `CreateSimulationRequest` (typed, no `as any`) to backend

### API Wiring Notes

- `api.createSimulation()` maps the frontend `CreateSimulationRequest` → backend `SimulationCreateRequest` (snake_case, `agents[]`, `environment_type`)
- `api.getSimulations()` / `api.getSimulation()` normalise `SimulationState` (nested `config.*`, `current_round`) → flat `Simulation` type via `_normalizeSimulation()`
- `api.controlSimulation('stop')` maps to `DELETE /api/simulations/{id}` (backend has no `/stop` route)
- Agent panel in `/simulations/[id]` uses real agents from `currentSimulation.agents` (no longer hardcoded mock data)

### Configuration

All config via environment variables loaded from `.env` at project root (see `.env.example`):

| Variable | Purpose |
|---|---|
| `LLM_PROVIDER` | Provider key (see table above) |
| `LLM_API_KEY` | API key for cloud providers |
| `LLM_BASE_URL` | Override for Azure / local proxies |
| `LLM_MODEL_NAME` | Model sent to provider |
| `NEO4J_URI/USER/PASSWORD` | Graph database connection |
| `MIRO_API_TOKEN` / `MIRO_BOARD_ID` | Optional Miro board sync |
| `MCP_SERVER_ENABLED` | Toggle MCP server |
| `TAVILY_API_KEY` | Web search for autoresearch |
| `SEC_USER_AGENT` | SEC EDGAR API user-agent |
| `ALPHA_VANTAGE_API_KEY` | Market data |
| `NEWS_API_KEY` | News feed |
| `WHISPER_MODEL` / `TTS_VOICE` / `TTS_MODEL` | Voice/transcription |
| `FINE_TUNE_DATA_DIR` / `FINE_TUNE_OUTPUT_DIR` | Fine-tuning paths |

Backend settings managed via Pydantic `BaseSettings` in `backend/app/config.py`.

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
cd backend && uv run scenariolab-sim simulate --playbook <name> --seed <file>
cd backend && uv run scenariolab-sim list-playbooks

# Backend tests (pytest + pytest-asyncio)
cd backend && uv run pytest                          # all tests
cd backend && uv run pytest tests/test_config.py     # single file
cd backend && uv run pytest tests/test_config.py::test_function_name  # single test
cd backend && uv run pytest -x                       # stop on first failure
cd backend && uv run pytest -k "simulation"          # match by keyword

# Backend linting/formatting
cd backend && uv run ruff check .
cd backend && uv run black .
cd backend && uv run mypy app/

# Frontend linting/type checking
cd frontend && npm run lint
cd frontend && npx tsc --noEmit

# Frontend build
cd frontend && npm run build

# E2E (Playwright) — from repo root; start the stack first (./start.sh or npm run dev).
# A global pre-check (e2e/global-setup.ts) fails fast if the app is not reachable.
# Optional: PLAYWRIGHT_BASE_URL=https://staging.example.com npm run test:e2e
npm run test:e2e
npm run test:e2e:p0              # P0 priority tests only
npm run test:e2e:headed          # visible browser
npm run test:e2e:ui              # Playwright UI mode
```

`PLAYWRIGHT_BASE_URL` defaults to `http://localhost:3000` in `playwright.config.ts`; set it when running tests against a deployed or non-default frontend. See `e2e/README.md` for why `webServer` is not enabled by default.

## Key Design Decisions

- **LLM Provider Abstraction**: `backend/app/llm/` uses a factory pattern (`factory.py`) with a base `provider.py` protocol. Adding a new LLM provider means implementing the protocol and registering in the factory. CLI providers all use a 120 s subprocess timeout.
- **Mock Data Fallback**: The frontend API client (`frontend/src/lib/api.ts`) includes extensive mock data so the UI is functional without a running backend. The normalisation layer (`_normalizeSimulation`) translates backend snake_case shapes to frontend camelCase types.
- **Simulation Engine**: Multi-turn agent simulation with branching scenarios, Monte Carlo analysis, and fog-of-war visibility rules. `simulation/engine.py` orchestrates turns; `simulation/agent.py` handles individual agent behaviour. `simulation/router.py` exposes REST endpoints including `/start`, `/pause`, `/resume` (no `/stop` — use `DELETE /api/simulations/{id}`).
- **Objective Pipeline**: User objectives are auto-parsed server-side on simulation create (`engine.py:_ensure_parsed_objective`). Structured fields (success_metrics, hypotheses, stop_conditions, key_actors) are injected into agent prompts via `objectives.py:format_simulation_objective_for_prompt`. Reports evaluate findings against the stated objective via `ObjectiveAssessment`.
- **Agent Intelligence**: Agents receive cross-round memory via `memory_manager.get_agent_context()` injected in `base.py:_process_agent_turn`. Conversation history shows full current round + last 5 from prior round (not a flat 10-message cap). Phase instructions are role-differentiated in boardroom (CFO gets financial probes, CRO gets risk focus, etc.). Closing prompts are phase-specific with format/length guidance.
- **Response Sanitization**: All agent responses pass through `agent.py:sanitize_llm_response()` which strips `<think>` blocks and detects non-English hallucinations (>40% non-Latin chars). Vote parsing uses regex-first extraction of `VOTE:` format with safe fallback ordering (against checked before for).
- **Stance Resilience**: `agent.py:update_stance()` retries up to 2x on empty/hallucinated results, includes cumulative stance context, and preserves prior stance on total failure.
- **Report Persistence**: Reports are persisted to SQLite via `db/reports.py:ReportRepository` with in-memory cache. Reports survive server restarts. Report generation runs all sections in parallel via `asyncio.gather`.
- **Analytics**: Sentiment analysis uses LLM when provider is available (keyword fallback otherwise). Decision outcome vocabulary is normalized across boardroom environment and analytics. Cross-simulation learning auto-triggers after simulation completion.
- **GraphRAG**: The graph module combines Neo4j knowledge graph with LLM-based entity extraction for retrieval-augmented generation over structured relationships. Falls back to SQLite if Neo4j is unavailable.
- **Seed Documents**: Users upload documents (via `/upload`) which are stored and can be linked to simulations. The wizard passes `seedIds`; the backend injects selected document content into every agent's system prompt.
- **TypeScript strictness**: `CreateSimulationRequest` interface is defined in `simulations/new/page.tsx`; no `as any` casts on API calls. The `useEffect` loading playbook details uses a `cancelled` flag to prevent stale-fetch races.
- **Backend testing**: Uses `pytest` + `pytest-asyncio`. Tests in `backend/tests/` with fixtures in `conftest.py`. Neo4j is stubbed when unavailable.
- **Code quality**: Backend enforces `black` (88-char lines), `ruff` (E,F,I,N,W rules), and `mypy` (strict mode) — all configured in `pyproject.toml`.
- **Security middleware**: `main.py` applies CORS (localhost:3000 only) and custom `SecurityHeadersMiddleware` (X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, Referrer-Policy, Permissions-Policy).
