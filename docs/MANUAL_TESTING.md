# ScenarioLab End-to-End Manual Testing Guide

This guide walks through every major feature for manual verification. Use it after deployment, after major changes, or as a QA checklist.

---

## Prerequisites

- Platform running via `./start.sh` (or `npm run dev`)
- Frontend at http://localhost:3000
- Backend at http://localhost:5001
- Valid `LLM_API_KEY` in `.env` for cloud-provider tests
- (Optional) Neo4j running for graph features

---

## Test Matrix

| # | Area | Priority | Est. Time |
|---|------|----------|-----------|
| 1 | [Platform Startup](#1-platform-startup) | P0 | 2 min |
| 2 | [Dashboard](#2-dashboard) | P1 | 1 min |
| 3 | [Playbook Browsing](#3-playbook-browsing) | P0 | 2 min |
| 4 | [Simulation Wizard](#4-simulation-wizard) | P0 | 5 min |
| 5 | [Simulation Execution](#5-simulation-execution) | P0 | 5 min |
| 6 | [Simulation Controls](#6-simulation-controls) | P0 | 3 min |
| 7 | [Simulation Sub-Pages](#7-simulation-sub-pages) | P1 | 5 min |
| 8 | [Seed Document Upload](#8-seed-document-upload) | P1 | 3 min |
| 9 | [Personas](#9-personas) | P1 | 5 min |
| 10 | [Reports](#10-reports) | P1 | 3 min |
| 11 | [Analytics](#11-analytics) | P2 | 3 min |
| 12 | [API Keys](#12-api-keys) | P2 | 2 min |
| 13 | [CLI](#13-cli) | P1 | 3 min |
| 14 | [LLM Provider Switch](#14-llm-provider-switch) | P1 | 3 min |
| 15 | [Graceful Degradation](#15-graceful-degradation) | P1 | 3 min |
| 16 | [Backend API Docs](#16-backend-api-docs) | P2 | 1 min |
| 17 | [Scenario Branching & Compare](#17-scenario-branching--compare) | P1 | 4 min |
| 18 | [Backtesting](#18-backtesting) | P1 | 3 min |
| 19 | [Rehearsal & Counterpart Agents](#19-rehearsal--counterpart-agents) | P1 | 4 min |
| 20 | [Annotations](#20-annotations) | P2 | 3 min |
| 21 | [Regulatory Scenario Generator](#21-regulatory-scenario-generator) | P2 | 3 min |
| 22 | [Fine-Tuning](#22-fine-tuning) | P2 | 3 min |
| 23 | [Graphiti Temporal Memory](#23-graphiti-temporal-memory) | P2 | 3 min |
| 24 | [External API v1](#24-external-api-v1) | P2 | 4 min |
| 25 | [WebSocket Real-Time Updates](#25-websocket-real-time-updates) | P2 | 2 min |
| 26 | [Dual-Create & Preset Simulations](#26-dual-create--preset-simulations) | P2 | 3 min |

**Total estimated time**: ~80 minutes for full pass

---

## 1. Platform Startup

**Goal**: Verify the full stack starts cleanly.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1.1 | Run `./start.sh` | No errors in terminal output |
| 1.2 | Open http://localhost:3000 | Dashboard loads, no blank page |
| 1.3 | Open http://localhost:5001/docs | Swagger UI loads with all endpoints |
| 1.4 | Check terminal | Both `uvicorn` and `next dev` logs visible |

**Skip-install variant**: Run `./start.sh --skip-install` on subsequent runs. Verify it starts faster.

**No-Neo4j variant**: Run `./start.sh --no-neo4j`. Verify backend starts with a warning about Neo4j being unavailable.

---

## 2. Dashboard

**Goal**: Home page renders correctly.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 2.1 | Navigate to `/` | Dashboard renders with sidebar |
| 2.2 | Check sidebar links | All navigation items present: Simulations, Playbooks, Personas, Upload, Reports, Analytics |
| 2.3 | Verify responsiveness | Resize browser; layout adapts without overflow |

---

## 3. Playbook Browsing

**Goal**: Playbook library loads and displays correctly.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 3.1 | Navigate to `/playbooks` | Playbook grid/list renders |
| 3.2 | Click a playbook card | Detail view shows description, agent roster, and environment type |
| 3.3 | Verify icons/badges | Each playbook shows its icon and category |

---

## 4. Simulation Wizard

**Goal**: End-to-end simulation creation via the 5-step wizard.

### Step 1: Select Playbook

| Step | Action | Expected Result |
|------|--------|-----------------|
| 4.1 | Navigate to `/simulations/new` | Wizard opens at Step 1 |
| 4.2 | Click a playbook | Playbook highlights; roster loads (may show brief spinner) |
| 4.3 | Rapidly switch playbooks | No stale data from previous selection (race condition guard) |
| 4.4 | Click Next | Advances to Step 2 |

### Step 2: Configure Agents

| Step | Action | Expected Result |
|------|--------|-----------------|
| 4.5 | Adjust agent count sliders | Total count updates live |
| 4.6 | Try exceeding max agents (48) | Error or slider cap prevents exceeding limit |
| 4.7 | Set all counts to 0 | Next button disabled or shows validation error |
| 4.8 | Click Next | Advances to Step 3 |

### Step 3: Seed Documents

| Step | Action | Expected Result |
|------|--------|-----------------|
| 4.9 | Skip (no documents) | Next button is enabled; step is optional |
| 4.10 | Select existing documents | Checkboxes toggle; selected count updates |
| 4.11 | Click Next | Advances to Step 4 |

### Step 4: Parameters

| Step | Action | Expected Result |
|------|--------|-----------------|
| 4.12 | Adjust rounds slider | Value updates (1-50 range) |
| 4.13 | Change environment type | Dropdown shows all 4 options |
| 4.14 | Toggle Monte Carlo | Iterations field enables/disables |
| 4.15 | Check cost estimate | Cost figure displayed and updates with config changes |
| 4.16 | Click Next | Advances to Step 5 |

### Step 5: Review and Launch

| Step | Action | Expected Result |
|------|--------|-----------------|
| 4.17 | Review summary | All configured values displayed correctly |
| 4.18 | Click Launch | Loading state shown; redirected to simulation page |
| 4.19 | Check backend logs | `POST /api/simulations` logged with 200/201 status |

---

## 5. Simulation Execution

**Goal**: Simulation runs and agents produce output.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 5.1 | On simulation detail page, click Start | Status changes to "running" |
| 5.2 | Watch round progress | Round counter increments (1/N, 2/N, ...) |
| 5.3 | Check agent panels | Each agent shows reasoning/actions per round |
| 5.4 | Wait for completion | Status changes to "completed"; all rounds shown |
| 5.5 | Verify no errors | No error toasts or blank agent panels |

**Note**: A 10-round simulation with 5-6 agents typically takes 2-5 minutes depending on LLM provider latency.

---

## 6. Simulation Controls

**Goal**: Pause, resume, and delete work correctly.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 6.1 | Start a new simulation | Status: running |
| 6.2 | Click Pause (during execution) | Status changes to "paused"; current round completes first |
| 6.3 | Click Resume | Execution continues from where it paused |
| 6.4 | Click Delete | Confirmation dialog appears |
| 6.5 | Confirm delete | Simulation removed; redirected to list |
| 6.6 | Verify deletion | Simulation no longer appears in `/simulations` list |

---

## 7. Simulation Sub-Pages

**Goal**: All simulation detail tabs render without errors.

After a simulation completes, visit each tab:

| Tab | Path | Verify |
|-----|------|--------|
| Chat | `/simulations/[id]/chat` | Chat input works; agent responds; history persists on reload |
| Sensitivity | `/simulations/[id]/sensitivity` | Tornado chart renders with parameter impact rankings |
| Network | `/simulations/[id]/network` | Force-directed graph renders; nodes clickable; edges show sentiment colors |
| ZOPA | `/simulations/[id]/zopa` | Zone of Possible Agreement visualization with party ranges and overlap |
| Fairness | `/simulations/[id]/fairness` | Bias/fairness audit results with permutation test outcomes |
| Timeline | `/simulations/[id]/timeline` | Events shown chronologically; scrub slider works; bookmarks saveable |
| Audit Trail | `/simulations/[id]/audit-trail` | Event log with SHA-256 hashes; verify integrity button works |
| Report | `/simulations/[id]/report` | Narrative report with exec summary, risk register, scenario matrix, heatmap |
| Market Intel | `/simulations/[id]/market-intel` | Market intelligence feed displays or placeholder if not configured |
| Voice | `/simulations/[id]/voice` | Audio controls present; transcribe and TTS work (requires OpenAI key) |
| Attribution | `/simulations/[id]/attribution` | Shapley value attribution with confidence intervals |
| Rehearsal | `/simulations/[id]/rehearsal` | Counterpart agent interaction; objection generation works |

**Pass criteria**: Each page loads without JavaScript errors (check browser console).

---

## 8. Seed Document Upload

**Goal**: Upload, view, and link documents to simulations.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 8.1 | Navigate to `/upload` | Upload page renders with drop zone |
| 8.2 | Drag a PDF onto the drop zone | File accepted; processing indicator shown |
| 8.3 | Wait for processing | Document appears in the document list |
| 8.4 | Upload a TXT file | Same behavior as PDF |
| 8.5 | Navigate to `/simulations/new` Step 3 | Uploaded documents appear in selection list |
| 8.6 | Select a document and launch simulation | Verify in agent prompts (check backend logs) that seed content is injected |

---

## 9. Personas

**Goal**: Persona browsing, designer CRUD, counterpart agents, and axioms work.

### Persona Library

| Step | Action | Expected Result |
|------|--------|-----------------|
| 9.1 | Navigate to `/personas` | Persona library loads |
| 9.2 | Browse persona cards | Each shows role, traits, description |
| 9.3 | Click a persona card | Detail view shows authority level, risk tolerance, decision speed, coalition tendencies |

### Persona Designer

| Step | Action | Expected Result |
|------|--------|-----------------|
| 9.4 | Navigate to `/personas/designer` | Designer interface renders |
| 9.5 | Create a custom persona (fill role, traits, objectives) | Persona saved; appears in designer list |
| 9.6 | `GET /api/personas/designer` | Returns list including new persona |
| 9.7 | Edit the persona | Changes persist after reload |
| 9.8 | Click "Refresh Research" on a designer persona | Web evidence re-fetched and merged; updated data shown |
| 9.9 | Validate persona coherence (`POST /api/personas/designer/validate`) | Returns coherence score and any warnings |
| 9.10 | Delete the persona | Removed from list; `GET /api/personas/designer/{id}` returns 404 |

### Axioms

| Step | Action | Expected Result |
|------|--------|-----------------|
| 9.11 | Navigate to `/personas/axioms` | Axioms page renders |
| 9.12 | Extract axioms from sample historical data (`POST /api/personas/axioms/extract`) | Returns extracted axioms with confidence scores |
| 9.13 | Validate axioms against holdout data (`POST /api/personas/axioms/validate`) | Returns validation results with accuracy metrics |

---

## 10. Reports

**Goal**: Reports generate and export correctly.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 10.1 | Navigate to `/reports` | Report list renders |
| 10.2 | Open a completed simulation's Report tab | Narrative report displays |
| 10.3 | Check report sections | Executive Summary, Risk Register, Scenario Matrix present |
| 10.4 | Export as PDF (if available) | Download initiates; file is valid PDF |
| 10.5 | Export as PPTX (if available) | Download initiates; file opens in PowerPoint |
| 10.6 | Export as interactive deck (`GET /api/reports/{id}/export/interactive-deck`) | Self-contained HTML file downloads; opens in browser with embedded JS |
| 10.7 | Add `?logo_url=...&primary_color=%23007bff&company_name=Acme` to deck export | Branding applied in the deck |
| 10.8 | Create a review checkpoint (`POST /api/reports/{id}/checkpoint`) | Checkpoint created; appears in report metadata |
| 10.9 | Update checkpoint status (`PATCH /api/reports/{id}/checkpoint/{checkpoint_id}`) | Status updates (e.g., approved/rejected) |

---

## 11. Analytics

**Goal**: Analytics pages render and process data.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 11.1 | Navigate to `/analytics` | Analytics dashboard renders |
| 11.2 | Select a completed simulation | Analytics data loads |
| 11.3 | Navigate to `/analytics/cross-simulation` | Cross-simulation view renders |
| 11.4 | Select multiple simulations | Comparison data displays |

---

## 12. API Keys

**Goal**: API key management works with admin authentication.

**Prerequisite**: Set `ADMIN_API_KEY=test-secret-123` in `.env` and restart backend.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 12.1 | Navigate to `/api-keys` | Auth prompt appears |
| 12.2 | Enter wrong admin key | Error message shown |
| 12.3 | Enter correct admin key | Key management UI loads |
| 12.4 | Create a new API key | Key generated and displayed |
| 12.5 | List API keys | New key appears in list |
| 12.6 | Revoke the key | Key removed from list |

---

## 13. CLI

**Goal**: Headless simulation runs via the command line.

```bash
cd backend
```

| Step | Command | Expected Result |
|------|---------|-----------------|
| 13.1 | `uv run scenariolab-sim list-playbooks` | Playbook list printed to stdout |
| 13.2 | `uv run scenariolab-sim simulate --playbook mna-culture-clash --rounds 3` | Simulation runs; progress to stderr; results to stdout |
| 13.3 | `uv run scenariolab-sim status <id>` (from 13.2 output) | Status JSON printed |
| 13.4 | `uv run scenariolab-sim results <id> --output json` | Full results in JSON |
| 13.5 | `uv run scenariolab-sim results <id> --section executive_summary` | Summary section only |

---

## 14. LLM Provider Switch

**Goal**: Switching providers works without code changes.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 14.1 | Set `LLM_PROVIDER=openai` in `.env`, restart backend | `POST /api/llm/test` returns success |
| 14.2 | Set `LLM_PROVIDER=anthropic`, update `LLM_API_KEY` | `/api/llm/test` returns success |
| 14.3 | Set `LLM_PROVIDER=ollama` (with Ollama running) | `/api/llm/test` returns success |
| 14.4 | Run a short simulation with each provider | Agents produce coherent output |
| 14.5 | Check `/api/llm/config` | Returns current provider and model |

---

## 15. Graceful Degradation

**Goal**: Platform handles missing services gracefully.

### Without Neo4j

| Step | Action | Expected Result |
|------|--------|-----------------|
| 15.1 | Stop Neo4j container (`docker stop scenariolab-neo4j`) | |
| 15.2 | Restart backend | Starts with warning; no crash |
| 15.3 | Run a simulation | Completes successfully (SQLite fallback) |
| 15.4 | Check graph features | Shows "unavailable" or empty state; no errors |

### Without Backend

| Step | Action | Expected Result |
|------|--------|-----------------|
| 15.5 | Stop the backend process | |
| 15.6 | Refresh frontend | UI loads with mock data; no blank page |
| 15.7 | Attempt simulation creation | Error toast or message; no crash |

### Invalid LLM Key

| Step | Action | Expected Result |
|------|--------|-----------------|
| 15.8 | Set `LLM_API_KEY=invalid` in `.env`, restart | |
| 15.9 | Run `POST /api/llm/test` | Returns error with clear message |
| 15.10 | Attempt simulation | Fails gracefully with user-visible error |

---

## 16. Backend API Docs

**Goal**: Swagger UI is accessible and functional.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 16.1 | Open http://localhost:5001/docs | Swagger UI renders |
| 16.2 | Expand `/api/simulations` section | All endpoints listed |
| 16.3 | Try "Try it out" on `GET /api/simulations` | Returns 200 with simulation list |
| 16.4 | Try `POST /api/llm/test` | Returns provider status |

---

## 17. Scenario Branching & Compare

**Goal**: Create scenario branches and compare outcomes side-by-side.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 17.1 | Complete a simulation | Status: completed |
| 17.2 | Create a branch (`POST /api/branches`) with modified config | Branch created; returns branch ID |
| 17.3 | Get scenario tree (`GET /api/branches/tree/{root_id}`) | Tree structure with root and branch(es) |
| 17.4 | Get branch lineage (`GET /api/branches/{id}/lineage`) | Returns lineage chain |
| 17.5 | Compare two branches (`POST /api/branches/compare`) | Side-by-side metrics comparison returned |
| 17.6 | Config diff (`GET /api/branches/{a}/diff/{b}`) | Returns diff of configuration changes |
| 17.7 | Navigate to `/simulations/compare` | Compare page renders |
| 17.8 | Select two completed simulations | Comparison data displays side-by-side |

---

## 18. Backtesting

**Goal**: Run simulations against historical outcomes.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 18.1 | Navigate to `/simulations/backtest` | Backtest page renders |
| 18.2 | List bundled backtest cases (`GET /api/simulations/backtest/cases`) | Returns available historical cases |
| 18.3 | Run a backtest (`POST /api/simulations/backtest`) | Backtest executes; results compare simulated vs. actual outcomes |
| 18.4 | Review accuracy metrics | Stakeholder stance, timeline, and outcome direction scores displayed |

---

## 19. Rehearsal & Counterpart Agents

**Goal**: Create counterpart agents and run rehearsal sessions.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 19.1 | Create a counterpart agent (`POST /api/personas/counterpart/create`) | Agent created from base archetype |
| 19.2 | List counterpart agents (`GET /api/personas/counterpart`) | New agent appears in list |
| 19.3 | Run a rehearsal turn (`POST /api/personas/counterpart/{id}/rehearse`) | Agent responds with in-character pushback |
| 19.4 | Generate objections (`POST /api/personas/counterpart/{id}/objections`) | Returns 5+ relevant objections |
| 19.5 | Get feedback summary (`GET /api/personas/counterpart/{id}/feedback`) | Returns structured rehearsal feedback |
| 19.6 | Navigate to `/simulations/[id]/rehearsal` | Rehearsal page renders with interaction UI |
| 19.7 | Delete counterpart (`DELETE /api/personas/counterpart/{id}`) | Agent removed; 404 on subsequent GET |

---

## 20. Annotations

**Goal**: Add and manage inline annotations on simulation events.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 20.1 | Create an annotation (`POST /api/annotations`) with agree/disagree/caveat tag | Annotation saved; returns annotation ID |
| 20.2 | List annotations for a simulation (`GET /api/simulations/{id}/annotations`) | Annotations returned with tags and content |
| 20.3 | Filter annotations by tag type | Only matching annotations returned |
| 20.4 | Export annotations (`GET /api/simulations/{id}/annotations/export`) | JSON export with all annotation data |
| 20.5 | Delete annotation (`DELETE /api/annotations/{id}`) | Annotation removed from list |

---

## 21. Regulatory Scenario Generator

**Goal**: Auto-generate simulation scenarios from regulatory text.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 21.1 | Navigate to `/simulations/new/regulatory` | Regulatory scenario generator page renders |
| 21.2 | Submit regulatory text (`POST /api/regulatory/generate`) | Returns generated scenario with agent roster and expected impacts |
| 21.3 | Review auto-generated agent roster | Roster appropriate for regulation type |
| 21.4 | Launch simulation from generated scenario | Simulation created and starts normally |

---

## 22. Fine-Tuning

**Goal**: Fine-tuning interface and API work correctly.

**Prerequisite**: Appropriate model and training data available.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 22.1 | Navigate to `/fine-tuning` | Fine-tuning page renders |
| 22.2 | Prepare dataset (`POST /api/llm/fine-tune/prepare-dataset`) | Dataset prepared; confirmation returned |
| 22.3 | Start fine-tuning job (`POST /api/llm/fine-tune/start`) | Job starts; returns job ID |
| 22.4 | Check job status (`GET /api/llm/fine-tune/status/{job_id}`) | Returns progress and status |
| 22.5 | List jobs (`GET /api/llm/fine-tune/jobs`) | All jobs listed with statuses |
| 22.6 | List adapters (`GET /api/llm/fine-tune/adapters`) | Available LoRA adapters listed |
| 22.7 | Activate adapter (`POST /api/llm/fine-tune/activate/{adapter_id}`) | Adapter activated for inference |
| 22.8 | Create domain benchmark (`POST /api/llm/fine-tune/benchmark`) | Benchmark results returned |

---

## 23. Graphiti Temporal Memory

**Goal**: Temporal memory integration works when enabled.

**Prerequisite**: `GRAPHITI_ENABLED=true`, Neo4j running, `GRAPHITI_OPENAI_API_KEY` set.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 23.1 | Check status (`GET /api/graph/temporal-memory-status`) | Returns enabled status and connection info |
| 23.2 | Run a short simulation (3 rounds) | Simulation completes; rounds ingested as Graphiti episodes |
| 23.3 | Search temporal memory (`POST /api/graph/temporal/search`) with `simulation_id` and `query` | Returns relevant facts from simulation history |
| 23.4 | Delete the simulation | Graphiti partition cleaned up; search returns empty |
| 23.5 | Set `GRAPHITI_INJECT_AGENT_CONTEXT=true`, run another simulation | Agent prompts include retrieved temporal facts (check backend logs) |

---

## 24. External API v1

**Goal**: External API with key-based authentication works.

**Prerequisite**: `ADMIN_API_KEY=test-secret-123` in `.env`.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 24.1 | Create API key (`POST /api/v1/api-keys` with admin Bearer token) | API key created with scopes |
| 24.2 | List API keys (`GET /api/v1/api-keys` with admin token) | New key in list |
| 24.3 | Create simulation via external API (`POST /api/v1/simulations` with API key) | Simulation created; requires `write:simulations` scope |
| 24.4 | Get simulation (`GET /api/v1/simulations/{id}` with API key) | Returns simulation data; requires `read:simulations` scope |
| 24.5 | Start simulation (`POST /api/v1/simulations/{id}/start` with API key) | Simulation starts |
| 24.6 | Get results (`GET /api/v1/simulations/{id}/results` with API key) | Returns results after completion |
| 24.7 | Get report (`GET /api/v1/reports/{id}` with API key) | Returns report; requires `read:reports` scope |
| 24.8 | Create webhook (`POST /api/v1/webhooks` with API key) | Webhook registered |
| 24.9 | List webhooks (`GET /api/v1/webhooks`) | Webhook in list |
| 24.10 | Revoke API key (`DELETE /api/v1/api-keys/{id}` with admin token) | Key revoked; subsequent API calls with that key return 401 |

---

## 25. WebSocket Real-Time Updates

**Goal**: WebSocket connection delivers live simulation updates.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 25.1 | Connect to `ws://localhost:5001/api/simulations/ws/{id}` | WebSocket connection established |
| 25.2 | Start the simulation | Round progress events received via WebSocket |
| 25.3 | Verify message format | Messages include round number, agent actions, status changes |
| 25.4 | Pause and resume | Pause/resume events received |
| 25.5 | Disconnect and reconnect | No crash; reconnection succeeds |

---

## 26. Dual-Create & Preset Simulations

**Goal**: Dual-create rollback safety and preset preview work.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 26.1 | Preview two presets (`POST /api/simulations/dual-run-preset`) | Returns two simulation payloads as JSON (no persistence) |
| 26.2 | Create two simulations (`POST /api/simulations/dual-create`) | Both simulations created; both appear in list |
| 26.3 | Verify rollback: trigger a failure on second creation | First simulation rolled back (deleted); neither appears in list |
| 26.4 | Preview + create (`POST /api/simulations/dual-run-preset-create`) | Both previewed and created in one call |

---

## Automated E2E Tests

For repeatable testing, ScenarioLab includes Playwright tests:

```bash
# Ensure the stack is running first (./start.sh or npm run dev)

npm run test:e2e              # Full suite
npm run test:e2e:p0           # P0 priority only
npm run test:e2e:headed       # Visible browser
npm run test:e2e:ui           # Playwright UI mode

# Against a deployed environment
PLAYWRIGHT_BASE_URL=https://staging.example.com npm run test:e2e
```

---

## Defect Reporting Template

When a test fails, file a bug with:

```
## Bug Report

**Test #**: (e.g., 4.18)
**Area**: (e.g., Simulation Wizard - Launch)
**Steps to Reproduce**:
1. ...
2. ...

**Expected**: ...
**Actual**: ...
**Screenshots/Logs**: (attach)
**Environment**: (browser, OS, LLM provider)
```
