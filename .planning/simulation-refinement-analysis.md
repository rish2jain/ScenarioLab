# Simulation Refinement Analysis

Date: 2026-04-05
Status: **ALL 4 PHASES COMPLETE** (17 commits merged to main)

## Implementation Status

| Phase | Status | Commits | Branch |
| --- | --- | --- | --- |
| 1: Core Reliability | DONE | 4 | `fix/phase1-core-reliability` |
| 2: Agent Intelligence | DONE | 4 | `fix/phase2-agent-intelligence` |
| 3: Report Quality | DONE | 4 | `fix/phase3-report-quality` |
| 4: Analytics & Persistence | DONE | 5 | `fix/phase4-analytics-persistence` |

### What Was Delivered

| # | Fix | Status |
| --- | --- | --- |
| 1 | Vote parsing -- regex-first with safe fallback ordering | DONE |
| 2 | Response sanitization -- think-tag stripping, hallucination detection | DONE |
| 3 | Stance update retry with cumulative context | DONE |
| 4 | Server-side objective auto-parse on create | DONE |
| 5 | Cross-round memory retrieval wired into agent turns | DONE |
| 6 | Full current-round conversation history + prior-round bridge | DONE |
| 7 | Role-differentiated phase instructions (boardroom) | DONE |
| 8 | Phase-aware closing prompts with format guidance | DONE |
| 9 | Report context expanded to all rounds with vote outcomes | DONE |
| 10 | Objective assessment (already existed; enhanced to use all messages) | DONE |
| 11 | Narrative context expanded + report LLM calls parallelized | DONE |
| 12 | Monte Carlo runs before report generation | DONE |
| 13 | Decision outcome vocabulary normalized | DONE |
| 14 | LLM-based sentiment analysis with keyword fallback | DONE |
| 15 | Report persistence to SQLite | DONE |
| 16 | Cross-simulation learning auto-triggered | DONE |
| -- | datetime.utcnow() deprecation fixed in report models | DONE |

### Remaining (Not Addressed)

These scored 6–7/9 but were lower priority:

- Coalition detection requires agent name mention (semantic matching would improve)
- Compliance violation detection is word-overlap (needs LLM)
- Custom personas lack INSTRUCTIONS section vs built-in archetypes
- Seed document truncation is character-based, not token-based
- Message type classification is naive (`"?" in content`)
- Untyped `parameters` dict on SimulationConfig

---

## Part 1: Objective vs. Reality

### User's Objective (sim `2af8271d`)

> "How can Hello improve its revenue by $50M. It is currently close to a targeted $110M"

The system parsed this well -- 6 success metrics, 8 hypotheses, stop conditions, 12 key actors.

### What Actually Happened

- **Sim `2af8271d` (with objective):** Round 1 was excellent -- deeply specific Hello/Colgate strategy with named SKUs, trust infrastructure, premium positioning. Rounds 2-10 degraded: vote parsing broke (all abstain), CFO hallucinated Chinese text about Shell/oil in Round 2. All final stances empty.
- **Sim `0483be43` (no objective):** Better mechanically -- proper votes all 10 rounds, coherent consensus building, fully populated final stances. But discussed completely generic strategy, not Hello at all.

### Completed Simulations

| Sim ID | Name | Objective | Rounds | Vote Quality | Final Stances |
| --- | --- | --- | --- | --- | --- |
| `2af8271d` | Competitive Response War Game 4/4 | $50M revenue growth for Hello | 10 | Broke after R1 | Empty |
| `0483be43` | Competitive Response War Game 4/4 | None set | 10 | All valid | Fully populated |
| `52412ec4` | Competitive Response War Game 4/3 | None set | -- | -- | -- |
| `48c71966` | Boardroom Decision Rehearsal 4/3 | None set | -- | -- | -- |
| `ca95557a` | Boardroom Decision Rehearsal 4/3 | None set | -- | -- | -- |

---

## Part 2: AutoResearch Scout Report (historical)

**Temporal status:** This section is an **initial AutoResearch scout snapshot** (pre-remediation). The **Problem** bullets below keep the original wording where useful; they describe **historical** behavior at scan time, not a current regression audit. Phased work in [Implementation Status](#implementation-status) is **complete**; **What Was Delivered** lists **DONE** fixes that correspond to many of these findings. Items that remain open or lower priority are in [Remaining (Not Addressed)](#remaining-not-addressed).

**Scope:** Simulation engine, report generation, analytics, prompt engineering, data flow  
**Domain:** code + prompts + data integrity  
**Candidates found:** 23 scored 6+ / 26 total scanned

---

### Tier 1: CRITICAL (Score 9/9) — Core Simulation Integrity (historical)

#### 1.1 Vote Parsing Was Dangerously Fragile (historical)

- **Score:** Improvable 3 | Impactful 3 | Measurable 3 = **9/9**
- **File:** `backend/app/simulation/agent.py:350-357`
- **Problem:** Substring matching on entire response. `"for" in content` matches "before", "information", "unfortunately for us". `"no" in content` matches "note", "notable". Because `for` is checked first, almost any English response votes "for".
- **Evidence:** Sim `0483be43` Round 5 -- CEO's reasoning says "the proposal is still not board-ready for capital release" (clearly opposed), yet vote recorded as "for" because "for" appears in the sentence.
- **Fix:** Parse the `VOTE: [for/against/abstain]` format the prompt already requests. Use regex `r'VOTE:\s*(for|against|abstain)'` with fallback to structured extraction.
- **Eval criteria:** Run vote parser against corpus of actual agent responses; measure accuracy vs. human-labeled votes.

#### 1.2 CFO Hallucination / No Output Validation (historical)

- **Score:** Improvable 3 | Impactful 3 | Measurable 3 = **9/9**
- **File:** `backend/app/simulation/agent.py`
- **Problem:** No output validation or language enforcement. Sim `2af8271d` Round 2 CFO response switched to Chinese, discussed Shell Oil's investment strategy. Also leaked `</think>` tags (model chain-of-thought exposed).
- **Fix:** Post-generation validation: language detection, topic coherence check, think-tag stripping. Retry on failure.
- **Eval criteria:** Count hallucination rate across simulation runs; detect language switches and off-topic responses.

#### 1.3 Report Context Was Severely Truncated (historical)

- **Score:** Improvable 3 | Impactful 3 | Measurable 3 = **9/9**
- **File:** `backend/app/reports/report_agent.py:504-533`
- **Problem:** `_build_simulation_context()` only includes last 3 rounds, 5 messages per round, content truncated to 100 chars. For a 10-round sim with 190 messages, the report LLM sees ~1,500 chars total. Early-round dynamics, initial positions, pivotal decisions -- all invisible.
- **Note:** Helper functions (extract_key_findings, extract_risk_signals) DO see all messages via `_get_all_messages()`, but the LLM narrative prompts only get the truncated context.
- **Fix:** Summarize all rounds into a structured briefing. Use hierarchical summarization if full content exceeds context window.
- **Eval criteria:** Compare report quality (assessed by LLM judge) with 3-round vs. all-round context.

---

### Tier 2: HIGH (Score 8/9) — Agent Intelligence & Memory (historical)

#### 2.1 Memories Were Written But Never Read (historical)

- **Score:** Improvable 3 | Impactful 3 | Measurable 2 = **8/9**
- **Files:** `backend/app/simulation/engine.py` (missing call), `backend/app/graph/memory.py:174` (`get_agent_context()` exists but never called)
- **Problem:** 294 memories stored in the DB. `get_agent_context()` method exists and returns formatted memories, but is never called anywhere in the simulation loop. Agents have zero recall of earlier rounds beyond the last 10 visible messages in the current round.
- **Fix:** Call `get_agent_context()` in `_process_agent_turn()` and inject into prompt.

#### 2.2 Conversation History Was Capped at 10 Messages (historical)

- **Score:** Improvable 3 | Impactful 3 | Measurable 2 = **8/9**
- **File:** `backend/app/simulation/agent.py:257-265`
- **Problem:** `visible_messages[-10:]` is hardcoded. With 6 agents and 5 phases, one round produces ~19 messages. By Round 3, agents only see the tail of the current round -- zero cross-round context.
- **Fix:** Dynamic window based on token budget. Or use memory retrieval (2.1) for cross-round context.

#### 2.3 Stance Updates Were Lossy and Ephemeral (historical)

- **Score:** Improvable 3 | Impactful 3 | Measurable 2 = **8/9**
- **File:** `backend/app/simulation/agent.py:386-429`
- **Problem:** `update_stance` looks at last 5 messages, produces 1-2 sentence summary (128 max tokens), overwrites previous stance entirely. Stance is the ONLY cross-round memory mechanism, and it's lossy. In sim `2af8271d`, all stances were empty (update_stance failed silently due to catch-all exception handler).
- **Fix:** Cumulative stance with history. Log stance update failures instead of swallowing.

#### 2.4 Objective Was Not Injected Into Agent Prompts (historical)

- **Score:** Improvable 3 | Impactful 3 | Measurable 2 = **8/9**
- **Files:** `backend/app/simulation/engine.py:278`, `backend/app/simulation/agent.py:110-114`
- **Problem:** `config.description` (where the objective lives) is never passed into `customization["context"]` during `_initialize_agents()`. Default context is `"You are participating in a strategic war-game simulation."` Sim `0483be43` had empty description -- agents had no idea what to discuss.
- **Note:** `format_simulation_objective_for_prompt()` exists in `objectives.py:142-171` and IS called at `engine.py:278`, but only if `parameters` contains `parsedObjective`. The connection is entirely client-side -- if the frontend doesn't round-trip the parsed objective, it's lost.
- **Fix:** Server-side auto-parse on create. Always inject `config.description` as base context.

#### 2.5 No Round Evolution or Escalation (historical)

- **Score:** Improvable 3 | Impactful 3 | Measurable 2 = **8/9**
- **Files:** `backend/app/simulation/environments/boardroom.py`, `engine.py`
- **Problem:** Every round runs the identical 5-phase cycle. The vote always passes the first 200 chars of the Round 1 presentation -- by Round 5+, agents vote on an outdated, truncated proposal rather than the evolved position.
- **Fix:** Round-aware phase selection. Use parsed hypotheses as per-round agendas (the `build_round_agenda_line()` function exists but the hypothesis cycling is underutilized).

#### 2.6 Reports Did Not Evaluate Against Objective (historical)

- **Score:** Improvable 3 | Impactful 3 | Measurable 2 = **8/9**
- **Files:** `backend/app/reports/report_agent.py`, `backend/app/reports/models.py`
- **Problem:** Executive summary asks for "strategic implications" but never references the simulation's objective. No "Objective Assessment" section in report model. Narrative generator (`narrative.py`) doesn't include `config.description` at all.
- **Fix:** Add `ObjectiveAssessment` to report model. Prompt LLM to evaluate findings against stated goals/metrics.

#### 2.7 Report LLM Calls Were Sequential (historical)

- **Score:** Improvable 3 | Impactful 2 | Measurable 3 = **8/9**
- **File:** `backend/app/reports/report_agent.py:71-83`
- **Problem:** Four independent LLM calls (exec summary, risk register, scenario matrix, stakeholder heatmap) run sequentially. 12-20 seconds when it could be 3-5 with `asyncio.gather`.
- **Fix:** `asyncio.gather(*[self.generate_executive_summary(), ...])`.

#### 2.8 Decision Outcome Vocabulary Mismatch (historical)

- **Score:** Improvable 3 | Impactful 2 | Measurable 3 = **8/9**
- **Files:** `backend/app/simulation/environments/boardroom.py`, `backend/app/analytics/analytics_agent.py`
- **Problem:** Environment returns `"proposal_accepted"` but analytics checks for `"approved"`, `"accepted"`, `"adopted"`. Every decision outcome is classified as `"pending"`.
- **Fix:** Normalize outcome vocabulary. Use enum or constant.

#### 2.9 Sentiment Analysis Was Bag-of-Words Only (historical)

- **Score:** Improvable 3 | Impactful 2 | Measurable 3 = **8/9**
- **File:** `backend/app/analytics/analytics_agent.py:284-326`
- **Problem:** 30 positive words, 34 negative words. "risk" = negative, so CRO saying "we mitigated the risk" scores negative. The analytics agent has an `llm_provider` but NEVER uses it -- all analytics are keyword heuristics.
- **Fix:** Use the LLM provider for semantic sentiment analysis. Or at minimum, use context-aware scoring.

#### 2.10 Turning Point Detection Used Keyword Matching (historical)

- **Score:** Improvable 3 | Impactful 2 | Measurable 3 = **8/9**
- **File:** `backend/app/reports/narrative.py:277-288`
- **Problem:** Every message containing "but" or "however" is flagged as a "major" turning point. These words appear in virtually every substantive response. Massive false positive rate.
- **Fix:** LLM-based turning point detection comparing round-over-round stance changes.

#### 2.11 Agent Memories Were Low-Quality / Garbage Data (historical)

- **Score:** Improvable 3 | Impactful 2 | Measurable 3 = **8/9**
- **File:** `backend/app/graph/memory.py:88-100`
- **Problem:** 100% of 294 memories are either error messages ("Error code: 401") or identical 150-char truncated dumps -- every agent gets the same memory per round. No agent-specific reflection.
- **Fix:** Agent-specific memory with reflection: what did THIS agent learn? How does it affect their stance?

#### 2.12 Empty Stances Observed in Completed Simulations (historical)

- **Score:** Improvable 2 | Impactful 3 | Measurable 3 = **8/9**
- **File:** `backend/app/simulation/agent.py:429` (catch-all exception handler)
- **Problem:** Sim `2af8271d` completed 10 rounds with all stances empty. `update_stance` failed silently. The catch-all exception handler swallowed the error.
- **Fix:** Log stance update failures. Retry with backoff. Never allow empty stances in completed sims.

---

### Tier 3: HIGH (Score 7–8/9) — Prompt Engineering & Data Flow (historical)

#### 3.1 Phase Instructions Were Not Role-Differentiated (historical)

- **Score:** Improvable 3 | Impactful 2 | Measurable 2 = **7/9**
- **Files:** All environment files in `backend/app/simulation/environments/`
- **Problem:** `get_phase_instruction(phase, agent_role)` accepts `agent_role` but NEVER uses it. A CEO and a CFO get identical instructions. The Integration environment defines `_resolve_phase_instruction` but it's never called from the base class.
- **Fix:** Role-specific instruction templates. CFO should be told "evaluate financial viability", CEO should be told "assess strategic alignment".

#### 3.2 Agent Final Prompt Was Critically Weak (historical)

- **Score:** Improvable 3 | Impactful 2 | Measurable 2 = **7/9**
- **File:** `backend/app/simulation/agent.py:282`
- **Problem:** Final prompt is just `"Provide your response as your character would speak."` No guidance on response length, format, whether to address other agents, reference prior arguments, or introduce new information.
- **Fix:** Phase-specific closing instructions with format guidance. E.g., "Respond in 2-3 paragraphs. Address at least one prior argument by name."

#### 3.3 Reports Were Stored Only In-Memory (historical)

- **Score:** Improvable 2 | Impactful 3 | Measurable 2 = **7/9**
- **File:** `backend/app/reports/router.py:44`
- **Problem:** `_report_store: dict[str, SimulationReport] = {}`. All reports lost on server restart. On-demand reports via `POST /api/simulations/{id}/report` are ephemeral.
- **Fix:** Persist to SQLite alongside simulation state.

#### 3.4 Monte Carlo Ran After Report Generation (historical)

- **Score:** Improvable 2 | Impactful 3 | Measurable 2 = **7/9**
- **File:** `backend/app/simulation/engine.py:588-589`
- **Problem:** `_maybe_post_run_artifacts()` (report) runs before `_maybe_run_inline_monte_carlo()`. Report has zero knowledge of MC variance data.
- **Fix:** Reorder: run MC first, pass results to report generator.

#### 3.5 Coalition Detection Required Name Mentions (historical)

- **Score:** Improvable 2 | Impactful 2 | Measurable 2 = **6/9**
- **File:** `backend/app/analytics/analytics_agent.py:421-468`
- **Problem:** Requires agent to mention another agent BY NAME alongside alignment keywords. LLM responses say "the CFO's concern" or "the financial perspective" -- real coalitions go undetected.

#### 3.6 Compliance Violation Detection Used Word Overlap (historical)

- **Score:** Improvable 3 | Impactful 2 | Measurable 2 = **7/9**
- **File:** `backend/app/analytics/analytics_agent.py:190-258`
- **Problem:** Extracts "policies" from persona prompts via regex, checks if message content contains matching terms. "never take unnecessary risks" -> flags any message with "take" + "risk".

#### 3.7 Custom Personas Lacked INSTRUCTIONS Section (historical)

- **Score:** Improvable 2 | Impactful 2 | Measurable 2 = **6/9**
- **File:** `backend/app/personas/designer.py:487-594`
- **Problem:** Custom personas get structural metadata (authority, risk tolerance) but no behavioral INSTRUCTIONS, unlike the 17 built-in archetypes. Custom personas behave more generically.

#### 3.8 Cross-Sim Learning Was Not Auto-Triggered (historical)

- **Score:** Improvable 2 | Impactful 2 | Measurable 2 = **6/9**
- **File:** `backend/app/analytics/cross_simulation.py`
- **Problem:** `extract_patterns()` must be called manually via analytics router. No automatic post-simulation trigger.

#### 3.9 Seed Document Truncation Was Silent (historical)

- **Score:** Improvable 2 | Impactful 2 | Measurable 2 = **6/9**
- **File:** `backend/app/simulation/engine.py:192-198`
- **Problem:** Hard truncation at 24K chars (character-based, not token-based). No warning about how much was cut. A 100-page PDF loses most content silently.

---

### Not Recommended (Score < 6) (historical)

- Message type classification (5/9) -- naive `"?" in content` check, but low impact
- `datetime.utcnow()` deprecation (5/9) -- easy fix but low impact
- Untyped `parameters` dict (6/9) -- borderline; helps but doesn't change simulation quality

---

## Part 3: Recommended Implementation Phases

### Phase 1: Core Reliability (P0)

Fix the foundation so simulations produce trustworthy data.

| # | Fix | Files |
| --- | --- | --- |
| 1 | Vote parsing -- regex-first extraction of VOTE format | `agent.py:350-357` |
| 2 | Output validation -- language detection, think-tag stripping, retry | `agent.py` (post-generation) |
| 3 | Stance update error handling -- log failures, retry | `agent.py:386-429` |
| 4 | Objective injection -- server-side auto-parse, always inject into context | `engine.py:278`, `objectives.py`, `agent.py:110` |

### Phase 2: Agent Intelligence (P1)

Make agents actually remember and reason across rounds.

| # | Fix | Files |
| --- | --- | --- |
| 5 | Wire up memory retrieval -- call `get_agent_context()` in simulation loop | `engine.py`, `memory.py` |
| 6 | Expand conversation history -- dynamic window or summarization | `agent.py:257` |
| 7 | Role-differentiated phase instructions | `environments/*.py` |
| 8 | Stronger closing prompts with format guidance | `agent.py:282` |

### Phase 3: Report Quality (P1)

Make reports answer "so what?" relative to the user's objective.

| # | Fix | Files |
| --- | --- | --- |
| 9 | Expand report context -- hierarchical summarization of all rounds | `report_agent.py:504-533` |
| 10 | Add Objective Assessment section to report model and prompts | `models.py`, `report_agent.py` |
| 11 | Inject objective into narrative generator | `narrative.py` |
| 12 | Parallelize report LLM calls with asyncio.gather | `report_agent.py:71-83` |
| 13 | Fix MC/report ordering -- run MC before report | `engine.py:588-589` |

### Phase 4: Analytics & Persistence (P2)

Make analytics meaningful and data durable.

| # | Fix | Files |
| --- | --- | --- |
| 14 | LLM-based sentiment and turning point detection | `analytics_agent.py`, `narrative.py` |
| 15 | Fix decision outcome vocabulary mismatch | `boardroom.py`, `analytics_agent.py` |
| 16 | Persist reports to SQLite | `reports/router.py` |
| 17 | Auto-trigger cross-sim learning after completion | `engine.py`, `cross_simulation.py` |

*(Phase 4 table #17 aligns with “What Was Delivered” #16 — Cross-simulation learning auto-triggered.)*

---

## Part 4: Key Code Locations Reference

| Area | File | Lines | Issue |
| --- | --- | --- | --- |
| Vote parsing | `backend/app/simulation/agent.py` | 350-357 | Substring matching, not format parsing |
| Vote prompt | `backend/app/simulation/agent.py` | 303-310 | Asks for VOTE format but doesn't parse it |
| Persona prompts | `backend/app/personas/archetypes.py` | all | No scenario grounding, no output format |
| Phase instructions | `backend/app/simulation/environments/boardroom.py` | 239-260 | Not role-differentiated |
| Agent prompt assembly | `backend/app/simulation/agent.py` | 219-282 | 10-msg cap, weak closing |
| Stance update | `backend/app/simulation/agent.py` | 386-429 | Lossy, silent failures |
| Memory write | `backend/app/graph/memory.py` | 88-100 | 150-char truncation |
| Memory read (unused) | `backend/app/graph/memory.py` | 174-206 | Never called |
| Objective injection | `backend/app/simulation/engine.py` | 278 | Client-side only |
| Objective parsing | `backend/app/simulation/objectives.py` | 59-136 | Fire-and-forget |
| Report context | `backend/app/reports/report_agent.py` | 504-533 | Last 3 rounds, 100 chars |
| Report prompts | `backend/app/reports/report_agent.py` | 110-464 | No objective reference |
| Narrative prompts | `backend/app/reports/narrative.py` | 84-443 | Too short, no objective |
| Turning points | `backend/app/reports/narrative.py` | 277-288 | Keyword matching |
| Sentiment | `backend/app/analytics/analytics_agent.py` | 284-326 | Bag-of-words |
| Compliance | `backend/app/analytics/analytics_agent.py` | 190-258 | Word-overlap |
| Coalition | `backend/app/analytics/analytics_agent.py` | 421-468 | Requires name mention |
| Decision outcomes | `backend/app/analytics/analytics_agent.py` | -- | Vocab mismatch |
| Report storage | `backend/app/reports/router.py` | 44 | In-memory only |
| MC ordering | `backend/app/simulation/engine.py` | 588-589 | Report before MC |
| Seed truncation | `backend/app/simulation/engine.py` | 192-198 | 24K chars, silent |
