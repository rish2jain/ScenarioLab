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
| 9 | [Personas](#9-personas) | P1 | 3 min |
| 10 | [Reports](#10-reports) | P1 | 3 min |
| 11 | [Analytics](#11-analytics) | P2 | 3 min |
| 12 | [API Keys](#12-api-keys) | P2 | 2 min |
| 13 | [CLI](#13-cli) | P1 | 3 min |
| 14 | [LLM Provider Switch](#14-llm-provider-switch) | P1 | 3 min |
| 15 | [Graceful Degradation](#15-graceful-degradation) | P1 | 3 min |
| 16 | [Backend API Docs](#16-backend-api-docs) | P2 | 1 min |

**Total estimated time**: ~45 minutes for full pass

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
| Chat | `/simulations/[id]/chat` | Chat input works; agent responds |
| Sensitivity | `/simulations/[id]/sensitivity` | Chart renders or "not available" message |
| Network | `/simulations/[id]/network` | Network graph visualization renders |
| ZOPA | `/simulations/[id]/zopa` | Zone analysis displays |
| Fairness | `/simulations/[id]/fairness` | Fairness metrics render |
| Timeline | `/simulations/[id]/timeline` | Events shown chronologically |
| Audit Trail | `/simulations/[id]/audit-trail` | Event log with hashes |
| Report | `/simulations/[id]/report` | Narrative report generated |
| Market Intel | `/simulations/[id]/market-intel` | Data displays or placeholder |
| Voice | `/simulations/[id]/voice` | Audio controls present |
| Attribution | `/simulations/[id]/attribution` | Source tracking shown |

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

**Goal**: Persona browsing and creation work.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 9.1 | Navigate to `/personas` | Persona library loads |
| 9.2 | Browse persona cards | Each shows role, traits, description |
| 9.3 | Navigate to `/personas/designer` | Designer interface renders |
| 9.4 | Navigate to `/personas/axioms` | Axioms page renders |

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
