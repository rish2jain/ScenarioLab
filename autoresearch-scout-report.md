# AutoResearch Scout Report

**Scope:** Full ScenarioLab repo (backend + frontend)
**Domain:** all
**Date:** 2026-04-03 (rescan)
**Candidates found:** 9 scored 6+ / ~130 files scanned

## Terminology

- **Suggested mode** — How to steer an autoresearch loop. **Exploit** means doubling down on validating and scaling approaches that already look strong (tight feedback, fewer dead ends). **Explore** means deliberately testing new hypotheses, broader prompts, or alternative splits to surface diverse signals before converging. Pick exploit when you have a clear winner to harden; pick explore when uncertainty or novelty dominates.
- **Estimated rounds** — One **round** is one full Karpathy-style modify → evaluate → keep/discard cycle for the artifact (e.g., one code/doc change plus its checks). Treat the count as a budget: increase it when risk or ambiguity is high, decrease when cost or time is tight or when metrics plateau.

Throughout this report, **Suggested mode** and **Estimated rounds** refer to these definitions.

## Recommended Targets (ranked)

| Rank | Target | Score | Type | Key Issue |
|------|--------|-------|------|-----------|
| 1 | `frontend/src/lib/api.ts` | 8/9 | code | 1485-line god file, mock+real API interleaved, 25 dependents, zero tests |
| 2 | `backend/app/api_integrations/database.py` | 8/9 | code | NEW — 1040-line monolith DB layer, 8 dependents, no tests, duplicate DB connection pattern |
| 3 | `backend/app/simulation/engine.py` | 8/9 | code | Core orchestrator (428 lines), 10 importers, no dedicated tests, critical path |
| 4 | `backend/app/database.py` | 7/9 | code | 794-line monolith repository, all DB ops in one file, minimal tests (113 lines) |
| 5 | `backend/app/reports/exporters/miro.py` | 7/9 | code | 951 lines, external API integration, no tests, user-facing output |
| 6 | `backend/app/llm/factory.py` | 7/9 | code | Provider abstraction used by 16 modules, only 122-line test file, high fan-out |
| 7 | `backend/app/llm/database.py` | 7/9 | code | NEW — 732-line DB layer duplicating connection pattern from database.py, 4 dependents, no tests |
| 8 | `frontend/src/lib/types.ts` | 6/9 | code | 702 lines, 30 dependents, type definitions drive all frontend contracts |
| 9 | `backend/app/analytics/analytics_agent.py` | 6/9 | code | 652 lines, LLM-dependent analysis, no tests, user-facing reports |

---

## #1: `frontend/src/lib/api.ts`

| Dimension | Score | Evidence |
|-----------|-------|----------|
| Improvable | 3/3 | 1485 lines — god file mixing mock data, real API calls, error handling, and type coercion. Mock fallback logic interleaved with every function |
| Impactful | 3/3 | 25 files import it. Every frontend page depends on it. Breakage here breaks everything |
| Measurable | 2/3 | Can type-check with `tsc`, can test individual API functions, can measure file size reduction. No existing tests to baseline |

**Suggested eval criteria:**
1. File count after split (target: 4+ focused modules)
2. `tsc --noEmit` passes
3. Each extracted module has unit tests
4. Mock data isolated from real API calls

**Suggested mode** (see [Terminology](#terminology)): exploit
**Estimated rounds** (see [Terminology](#terminology)): 5

---

## #2: `backend/app/api_integrations/database.py` *(NEW)*

| Dimension | Score | Evidence |
|-----------|-------|----------|
| Improvable | 3/3 | 1040 lines — single file housing ALL integration persistence (webhooks, auth, API keys, rate limits). Duplicates `get_db()` connection pattern from `database.py` and `llm/database.py`. Uses global mutable `_initialized` flag |
| Impactful | 3/3 | 8 files import it including auth, webhooks, personas, gamification. Integrations are user-configurable — data integrity matters |
| Measurable | 2/3 | Pure CRUD functions against SQLite — highly testable. No existing tests. Can validate schema, parameterization, and query correctness |

**Suggested eval criteria:**
1. Split into per-domain repositories (webhooks, auth, API keys)
2. Consolidate DB connection pattern with `database.py`
3. Each repository has CRUD tests
4. No raw SQL without parameterization

**Suggested mode** (see [Terminology](#terminology)): exploit
**Estimated rounds** (see [Terminology](#terminology)): 4

---

## #3: `backend/app/simulation/engine.py`

| Dimension | Score | Evidence |
|-----------|-------|----------|
| Improvable | 3/3 | Core orchestrator pulling from 10+ modules. Turn execution, agent coordination, scenario branching all in one class. No separation of concerns |
| Impactful | 3/3 | THE critical path — every simulation runs through this. 10 files import it including backtesting, routers, monte carlo, batch |
| Measurable | 2/3 | Can add integration tests, measure turn execution correctness, validate agent output format. Only basic backend tests exist (5 files, 497 total lines) |

**Suggested eval criteria:**
1. Test coverage >80%
2. Engine methods <50 lines each
3. Simulation runs produce deterministic output given fixed seed
4. Error paths tested

**Suggested mode** (see [Terminology](#terminology)): exploit
**Estimated rounds** (see [Terminology](#terminology)): 5-7

---

## #4: `backend/app/database.py`

| Dimension | Score | Evidence |
|-----------|-------|----------|
| Improvable | 3/3 | 794 lines, single file housing ALL core repository operations (simulations, reports, playbooks, personas). Connection pattern duplicated across 3 DB files |
| Impactful | 2/3 | 8 files import it. Data integrity depends on it. But it's internal plumbing, not directly user-facing |
| Measurable | 2/3 | `test_database.py` exists (113 lines) — provides a baseline. Can verify via CRUD tests, measure file split, check query patterns |

**Suggested eval criteria:**
1. Split into per-domain repositories
2. Unify DB connection pattern across `database.py`, `api_integrations/database.py`, `llm/database.py`
3. Each repo has unit tests
4. No raw SQL without parameterization

**Suggested mode** (see [Terminology](#terminology)): exploit
**Estimated rounds** (see [Terminology](#terminology)): 4

---

## #5: `backend/app/reports/exporters/miro.py`

| Dimension | Score | Evidence |
|-----------|-------|----------|
| Improvable | 2/3 | 951 lines, external Miro API integration. Likely has hardcoded layouts, complex board construction logic |
| Impactful | 3/3 | Client-facing deliverable — exports simulation results to Miro boards. Visible to end users/clients |
| Measurable | 2/3 | Can mock Miro API, validate board structure, test layout calculations. No existing tests |

**Suggested eval criteria:**
1. Board output matches expected structure
2. Error handling for API failures
3. File <500 lines after refactor
4. Layout functions tested with snapshots

**Suggested mode** (see [Terminology](#terminology)): explore
**Estimated rounds** (see [Terminology](#terminology)): 4

---

## #6: `backend/app/llm/factory.py`

| Dimension | Score | Evidence |
|-----------|-------|----------|
| Improvable | 2/3 | Provider abstraction layer. Factory pattern but 16 modules depend on it — any inconsistency in provider protocol propagates everywhere |
| Impactful | 3/3 | Every LLM call in the system routes through this. Wrong provider selection = broken simulations |
| Measurable | 2/3 | `test_llm_factory.py` exists (122 lines). Can expand: test each provider instantiation, verify protocol conformance, test fallback behavior |

**Suggested eval criteria:**
1. All providers pass protocol conformance tests
2. Factory handles missing credentials gracefully
3. 100% branch coverage on provider selection

**Suggested mode** (see [Terminology](#terminology)): exploit
**Estimated rounds** (see [Terminology](#terminology)): 3

---

## #7: `backend/app/llm/database.py` *(NEW)*

| Dimension | Score | Evidence |
|-----------|-------|----------|
| Improvable | 3/3 | 732 lines — third copy of the SQLite persistence pattern. Duplicates `get_db()` and `_utc_now_iso()` from main `database.py`. Houses fine-tuning, prompt history, and model config in one file |
| Impactful | 2/3 | 4 files import it (main, market_intelligence, fine_tuning, voice_router). Supports LLM ops but not on the hottest critical path |
| Measurable | 2/3 | Pure CRUD — easy to test. No existing tests. Can validate schema and consolidation with other DB layers |

**Suggested eval criteria:**
1. Consolidate DB connection pattern with `database.py` and `api_integrations/database.py`
2. Split into focused repositories (fine-tuning, prompt history, model config)
3. Each repository has CRUD tests
4. Shared DB utilities extracted to common module

**Suggested mode** (see [Terminology](#terminology)): exploit
**Estimated rounds** (see [Terminology](#terminology)): 3

---

## #8: `frontend/src/lib/types.ts`

| Dimension | Score | Evidence |
|-----------|-------|----------|
| Improvable | 2/3 | 702 lines, all types in a single file. Could be split by domain (simulation, report, persona, etc.) |
| Impactful | 2/3 | 30 dependents — every component and page imports from here. Structural foundation of the frontend |
| Measurable | 2/3 | `tsc --noEmit` validates correctness. Can measure type coverage and file organization |

**Suggested eval criteria:**
1. Split into domain-specific type modules
2. `tsc --noEmit` passes after split
3. No `any` types remaining
4. All API response types match backend schemas

**Suggested mode** (see [Terminology](#terminology)): exploit
**Estimated rounds** (see [Terminology](#terminology)): 3

---

## #9: `backend/app/analytics/analytics_agent.py`

| Dimension | Score | Evidence |
|-----------|-------|----------|
| Improvable | 2/3 | 652 lines, LLM-dependent analysis logic. Prompt construction and result parsing likely tightly coupled |
| Impactful | 2/3 | Generates post-simulation analytics shown to users. Quality directly affects consulting deliverables |
| Measurable | 2/3 | Can test prompt templates, validate output structure, snapshot test analysis results |

**Suggested eval criteria:**
1. Prompt templates extracted and tested independently
2. Output parsing has unit tests with fixture data
3. File <400 lines after extracting prompts
4. Analytics results match expected schema

**Suggested mode** (see [Terminology](#terminology)): explore
**Estimated rounds** (see [Terminology](#terminology)): 4

---

## Not Recommended

- `backend/app/personas/archetypes.py` (835 lines, 5/9) — Mostly data definitions, not logic
- `backend/app/reports/exporters/interactive_deck.py` (787 lines, 5/9) — Large but self-contained HTML template generation, only 2 dependents, low blast radius
- `backend/app/simulation/backtesting.py` (719 lines, 5/9) — Contains bundled test case data inflating line count; moderate complexity, 1 dependent
- `backend/app/llm/fine_tuning.py` (699 lines, 5/9) — Single-purpose module, 1 dependent, improvable but low impact
- `backend/app/simulation/advanced_router.py` (680 lines, 5/9) — Router layer, improvable but measurability limited without integration tests
- `backend/app/analytics/fairness.py` (641 lines, 5/9) — Specialized analysis, low fan-out
- Config files, `__init__.py` — trivial, no iteration value

---

## Key Observations

- **Zero project-specific TODOs/FIXMEs** — the codebase looks clean on the surface
- **Severely under-tested**: 5 test files (497 total test lines) for ~130 source files
- **God files** remain the biggest wins: `api.ts` (1485), `api_integrations/database.py` (1040), `miro.py` (951)
- **No frontend tests at all** — entire UI layer is untested
- **Database layer fragmentation**: 3 separate DB files (`database.py`, `api_integrations/database.py`, `llm/database.py`) totaling 2,566 lines with duplicated connection patterns — consolidation would be high-impact
- **NEW since last scan**: `api_integrations/database.py` (1040 lines) and `llm/database.py` (732 lines) are significant new god files

---

## Quick Start

In environments that expose it (for example Claude Code), **`/autoresearch`** is a slash command that drives **AutoResearch**: an automated, iterative research-and-transformation loop over a target file or directory (code, docs, prompts, etc.). The optional **`--metric`** string is **human-readable guidance** for what “better” means—the agent interprets it and typically breaks it into evaluable checks (tests, linters, PASS/FAIL rubrics); it is **not** a fixed machine schema. Prefix the value with **`measurable:`** when you state explicit thresholds or commands (line counts, coverage %, named scripts), or **`goal:`** when you describe architectural outcomes the loop should steer toward without a single parser-friendly number.

```bash
/autoresearch frontend/src/lib/api.ts --metric "goal: file split into <400-line modules with isolated mock data"
/autoresearch backend/app/api_integrations/database.py --metric "goal: split into domain repos with unified DB connection, each with CRUD tests"
/autoresearch backend/app/simulation/engine.py --metric "measurable: pytest coverage >80% on engine module; goal: deterministic turn output via fixtures"
/autoresearch backend/app/database.py --metric "goal: consolidated DB layer, split into domain repositories"
```
