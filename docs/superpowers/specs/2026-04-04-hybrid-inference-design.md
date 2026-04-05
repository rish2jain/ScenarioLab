# Hybrid Inference: Cloud-Primed Local LLM Execution

**Date**: 2026-04-04
**Status**: Implemented (retrospective spec)

**Author**: Rishabh + Claude

> **Note**: This document describes shipped hybrid-inference behavior and was finalized alongside implementation, not as a pre-code design-only draft. Section 12 is a **retrospective** inventory of files as they landed in the repo at that time—not a pending checklist.

---

## 1. Problem

MiroFish simulations are LLM-call-intensive. A 6-agent boardroom simulation generates ~12 LLM calls per round across response generation, voting, and stance updates. With 10 rounds, that is ~120 calls per simulation. Monte Carlo batches of 25 multiply this to ~3,000 calls. All calls currently route to a single cloud provider with a concurrency cap of 4, creating both a speed bottleneck and significant API cost.

The user's hardware (MacBook Pro M5 Max, 128GB unified memory) can run capable local models (Qwen 3 14B-70B) at competitive token throughput, but local models produce lower-quality output than frontier cloud models on complex strategic reasoning. The challenge is leveraging local hardware for speed without degrading simulation quality.

## 2. Solution

A **cloud-primed hybrid inference** strategy:

1. **Round 1** runs entirely on the cloud provider, producing high-quality exemplar outputs for every agent (responses, votes, stances).
2. **Rounds 2+** run on the local model, with round-1 outputs injected as few-shot exemplars into each agent's prompt. This anchors the local model to each agent's established voice, reasoning depth, and strategic position.
3. **Post-simulation tasks** (analytics, reports) always use the cloud provider regardless of mode.
4. **Monte Carlo batches** share the exemplars from the first simulation copy's round 1. Copies 2-25 run entirely local, primed by copy 1's exemplars.

The system auto-detects whether local inference is available. If it is, the user sees a toggle in the simulation wizard. If not, the option is hidden and everything runs on cloud -- identical to current behavior.

## 3. Goals and Non-Goals

### Goals

- Reduce simulation wall-clock time by 40-60% on capable hardware.
- Reduce cloud API cost by 60-85% per simulation.
- Maintain aggregate simulation quality within 5% of cloud-only baseline.
- Zero behavioral change when local hardware is not available (cloud-only default).
- Simple UX: one toggle, auto-detected, hidden when irrelevant.

### Non-Goals

- Dynamic per-prompt complexity routing (RouteLLM). This is a future optimization; the initial implementation uses static task-type routing.
- Semantic caching layer. High-value but independent of the hybrid inference work. Can be layered on later.
- Speculative decoding. Requires framework-level changes to the local inference server, not the application layer.
- Supporting multiple simultaneous local models (e.g., small model for votes, large for responses). One local model per simulation keeps the design simple.

## 4. Architecture

### 4.1 System Diagram

```
Frontend Wizard (Step 4)
  │
  │  GET /api/llm/capabilities
  │  ← { hybrid_available, local_model, ... }
  │
  │  [if hybrid_available: show toggle]
  │  User toggles "Use local hardware" → inference_mode: "hybrid"
  │
  ▼
SimulationEngine.create_simulation()
  │
  │  await InferenceRouter.create(cloud_provider, local_provider, mode, ...)
  │
  ▼
SimulationEngine.run_simulation()
  │
  ├─ Round 1 ──► InferenceRouter → cloud provider
  │     │
  │     └─ After round 1: store exemplars per agent
  │
  ├─ Rounds 2..N ──► InferenceRouter → local provider
  │     │              (exemplars injected into prompts)
  │     └─ Post-sim analytics/reports → cloud provider
  │
  └─ Monte Carlo copies 2..25
        │
        └─ All rounds → local provider (reuse copy-1 exemplars)
```

### 4.2 Inference Modes

Three internal modes exist. Only two are user-facing.

| Mode | Exposed To | Behavior |
| --- | --- | --- |
| `cloud` | Default (no toggle shown, or toggle off) | All calls use cloud provider. Identical to current behavior. |
| `hybrid` | Toggle on (only visible when local is available) | Round 1 cloud, rounds 2+ local with exemplars. Reports/analytics always cloud. |
| `local` | `.env` only (developer/testing) | All calls use local provider. No cloud calls. No exemplar priming. |

### 4.3 Component Overview

| Component | Location | Responsibility |
| --- | --- | --- |
| `InferenceRouter` | `backend/app/llm/inference_router.py` (new) | Routes calls to cloud or local based on mode, round number, and task type. Stores and injects exemplars. |
| `get_local_llm_provider()` | `backend/app/llm/factory.py` (modified) | Creates local provider instance from `LOCAL_LLM_*` config. |
| `InferenceCapabilities` | `backend/app/llm/router.py` (modified) | New endpoint: `GET /api/llm/capabilities`. |
| `Settings` | `backend/app/config.py` (modified) | New config vars for local provider and inference mode. |
| `SimulationAgent` | `backend/app/simulation/agent.py` (modified) | Accepts `InferenceRouter` instead of single `LLMProvider`. Passes round number and task type to router. |
| `SimulationEngine` | `backend/app/simulation/engine.py` (modified) | Initializes router with both providers. Stores exemplars after priming round. Passes shared exemplars to Monte Carlo copies. |
| Wizard Step 4 | `frontend/src/app/simulations/new/page.tsx` (modified) | Conditionally renders hybrid toggle based on capabilities endpoint. |

## 5. Detailed Design

### 5.1 Configuration

New settings in `backend/app/config.py`:

```python
# Hybrid inference
inference_mode: str = "cloud"
local_llm_provider: str = ""              # empty = disabled; set to "ollama" or "llamacpp" to enable
local_llm_base_url: str = "http://localhost:11434/v1"
local_llm_model_name: str = "qwen3:14b"
hybrid_cloud_rounds: int = 1
```

New entries in `.env.example`:

```bash
# Hybrid Inference (optional — enables local hardware acceleration)
# INFERENCE_MODE=cloud          # cloud | hybrid | local
# LOCAL_LLM_PROVIDER=ollama     # ollama | llamacpp
# LOCAL_LLM_BASE_URL=http://localhost:11434/v1
# LOCAL_LLM_MODEL_NAME=qwen3:14b
# HYBRID_CLOUD_ROUNDS=1         # Number of cloud-primed rounds
```

All new settings have safe defaults. Omitting them entirely produces identical behavior to the current system.

### 5.2 InferenceRouter

```
File: backend/app/llm/inference_router.py
```

**Class: `InferenceRouter`**

Responsibilities:
- Hold references to both cloud and local `LLMProvider` instances.
- Route `get_provider(round_number, task_type)` calls to the correct provider.
- Store round-1 agent outputs as exemplars.
- Build exemplar prompt fragments for injection into local-tier calls.
- Handle fallback: if local provider is unreachable at init time, degrade to cloud-only with a logged warning.

**Construction**: Prefer the async factory; do not rely on the synchronous constructor for production paths.

```
InferenceRouter(
    cloud: LLMProvider,
    local: LLMProvider | None,
    mode: str,                    # "cloud" | "hybrid" | "local"
    cloud_rounds: int = 1,
)
```

The synchronous `__init__` does not probe the local provider. Validation and local reachability checks run only in the async factory below.

Validation is not done in `__init__` (which is synchronous). Instead, provide an async class method:

```python
@classmethod
async def create(cls, cloud, local, mode, cloud_rounds=1) -> "InferenceRouter":
```

This factory method calls `local.test_connection()` (5-second timeout, matching `OllamaProvider` / `LlamaCppProvider`) when `mode` is `hybrid` or `local`. If the local provider is `None` or unreachable, hybrid mode degrades to `mode = "cloud"` with a warning. The simulation proceeds without error. **All production call sites use `await InferenceRouter.create(...)`** — do not instantiate `InferenceRouter(...)` directly unless you are constructing test doubles or a fully validated router (e.g. `with_preloaded_exemplars()`).

**Routing logic** (`get_provider`):

```
def get_provider(self, round_number: int, task_type: str) -> LLMProvider:
```

| Mode | Round <= cloud_rounds | Round > cloud_rounds | task_type = "analytics" or "report" |
| --- | --- | --- | --- |
| `cloud` | cloud | cloud | cloud |
| `hybrid` | cloud | local | cloud (always) |
| `local` | local | local | local |

`task_type` is one of: `"response"`, `"vote"`, `"stance"`, `"analytics"`, `"report"`.

**Exemplar storage** (`store_exemplar`):

```
def store_exemplar(self, agent_id: str, messages: list[SimulationMessage]) -> None:
```

Called once per agent after the priming round(s) complete. Stores the agent's response, vote, and stance outputs from round 1. These are plain `SimulationMessage` objects already present in `RoundState.messages`.

Storage is an in-memory dict: `dict[str, list[SimulationMessage]]` keyed by `agent_id`. No persistence needed -- exemplars live only for the duration of the simulation run (or Monte Carlo batch).

**Exemplar prompt building** (`build_exemplar_messages`):

```
def build_exemplar_messages(self, agent_id: str) -> list[LLMMessage]:
```

Returns a list of 0-2 `LLMMessage` objects to prepend to the agent's prompt when using the local provider. Returns empty list if no exemplars exist for this agent or if mode is not `hybrid`.

The exemplar content follows this structure:

```
role: user
content: |
  STYLE CALIBRATION (from your Round 1 performance):

  Your response style:
  "{agent's round-1 response, truncated to 500 chars}"

  Your voting style:
  "{agent's round-1 vote + reasoning, if available}"

  Your stance summary:
  "{agent's round-1 stance update}"

  Maintain this voice, reasoning depth, and perspective.
```

This is a single user message, ~200-400 tokens. It is inserted after the system message and before the simulation context message in the prompt stack built by `SimulationAgent._build_prompt()`.

**Token budget**: Per-field truncation limits are response 500 characters, vote reasoning 300 characters, stance 200 characters (up to **1,000 characters** of quoted exemplar text before headings and boilerplate). The composed STYLE CALIBRATION body is also capped at **~2,400 characters** in code so the overall prompt stays bounded (order ~600 tokens at ~4 characters per token for that block). The per-field limits and the total body cap are consistent: the sum of the three quoted fields cannot exceed 1,000 characters, and the full message including labels may be trimmed to the overall cap.

### 5.3 Factory Changes

New function in `backend/app/llm/factory.py`:

```
def get_local_llm_provider(*, model_override: str | None = None) -> LLMProvider | None:
```

Reads `settings.local_llm_provider` and creates the corresponding provider using `settings.local_llm_base_url` and `settings.local_llm_model_name`. Returns `None` if `local_llm_provider` is empty (the default), requiring explicit opt-in.

Only `ollama` and `llamacpp` are valid local providers. Both use OpenAI-compatible APIs, so this function creates `OllamaProvider` or `LlamaCppProvider` with the local-specific URL and model.

### 5.4 SimulationAgent Changes

**Constructor change**: Accept `InferenceRouter` instead of `LLMProvider`.

```python
def __init__(
    self,
    config: AgentConfig,
    archetype: ArchetypeDefinition,
    inference_router: InferenceRouter,   # was: llm_provider: LLMProvider
    memory_manager=None,
):
    self.router = inference_router
```

**`_throttled_generate` change**: Accept `round_number` and `task_type`, use router to select provider, inject exemplars.

```python
async def _throttled_generate(
    self,
    messages: list[LLMMessage],
    temperature: float = 0.7,
    max_tokens: int = 2048,
    *,
    round_number: int = 1,
    task_type: str = "response",
) -> LLMResponse:
    provider = self.router.get_provider(round_number, task_type)
    # Inject exemplars when using local provider in hybrid mode (see should_inject_exemplars in impl.)
    if self.router.should_inject_exemplars(self.id, round_number, task_type):
        exemplar_msgs = self.router.build_exemplar_messages(self.id)
        if exemplar_msgs:
            if not isinstance(messages, list):
                logger.warning("Hybrid exemplar injection skipped: messages is not a list")
            elif not messages:
                messages = list(exemplar_msgs)
            elif getattr(messages[0], "role", None) == "system":
                messages = [messages[0]] + exemplar_msgs + messages[1:]
            else:
                logger.warning(
                    "Hybrid exemplar injection: first message is not system; prepending exemplars"
                )
                messages = list(exemplar_msgs) + list(messages)
    async with _llm_limit_semaphore():
        return await provider.generate(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
```

**Concurrency (cloud vs local — actual behavior)**:

There is **no separate semaphore for local providers**. Every `LLMProvider.generate` (cloud OpenAI/Anthropic, local Ollama/llama.cpp, CLI providers, etc.) acquires the **same process-wide** `asyncio.Semaphore` defined in `backend/app/llm/provider.py` as `_llm_semaphore`, currently sized to **3** concurrent in-flight `generate` calls. **Local and cloud share that limit** — hybrid mode does not add a second pool.

Two layers stack:

| Layer | Where | Default cap | Configurable? |
| --- | --- | --- | --- |
| Simulation agent | `_llm_limit_semaphore()` in `backend/app/simulation/agent.py` | **`simulation_llm_parallelism`** (default **4**) | Yes — **`SIMULATION_LLM_PARALLELISM`** in `.env` (see `.env.example`) |
| Provider `generate()` | `_llm_semaphore` in `backend/app/llm/provider.py` | **3** | **No** env hook today; change `Semaphore(3)` / `MAX_CONCURRENT_LLM_CALLS` in code if you need a different global cap |

Effective in-flight LLM calls are bounded by **both** (nested `async with`): tasks **queue** on whichever semaphore is saturated first; nothing is rejected by these semaphores (no “server busy” short-circuit here — callers await until a slot frees). The **tighter** of the two limits dominates for steady-state throughput (today, **3** from the provider layer when parallelism ≥ 3).

**Monte Carlo / “25 copies”**: Inline and batch Monte Carlo in `MonteCarloRunner.run` execute iterations **sequentially** (`for i in range(config.iterations): await run_simulation(...)`). There are **not** 25 parallel simulations hammering the semaphores at once from that loop; each copy runs to completion before the next starts. Separate user-driven simulations on the same process would still share `_llm_semaphore` and `_llm_limit_semaphore()` as above.

**Operator guidance**:

- Raise **`SIMULATION_LLM_PARALLELISM`** if agents within **one** simulation should issue more concurrent `generate` calls (subject to the hard **3** cap at the provider until that constant is raised).
- To allow more than **3** concurrent HTTP/subprocess LLM calls **process-wide** (e.g. a large local server with many parallel slots), increase **`_llm_semaphore`** / **`MAX_CONCURRENT_LLM_CALLS`** in `provider.py` and retest — that is the knob tied directly to `provider.generate` for all backends, including Ollama/llama.cpp pointed at `LOCAL_LLM_BASE_URL`.

**Caller changes**: `generate_response()`, `cast_vote()`, and `update_stance()` pass `round_number` and `task_type` through to `_throttled_generate`.

**Backward compatibility**: When `InferenceRouter` is constructed with `mode="cloud"`, `get_provider` always returns the cloud provider. Exemplar injection never triggers. Behavior is identical to the current single-provider design.

### 5.5 SimulationEngine Changes

**`_initialize_agents` change**: Create `InferenceRouter` and pass to agents.

```python
async def _initialize_agents(self, agent_configs, ..., simulation_config):
    mo = _wizard_model_override(simulation_config.parameters if simulation_config else None)
    cloud_provider = _get_llm_provider(model_override=mo)
    local_provider = get_local_llm_provider(model_override=mo)

    mode = (simulation_config.parameters or {}).get("inference_mode", settings.inference_mode)
    cloud_rounds = int((simulation_config.parameters or {}).get(
        "hybrid_cloud_rounds", settings.hybrid_cloud_rounds
    ))

    router = await InferenceRouter.create(
        cloud=cloud_provider,
        local=local_provider,
        mode=mode,
        cloud_rounds=cloud_rounds,
    )

    for config in agent_configs:
        agent = SimulationAgent(
            config=config,
            archetype=archetype,
            inference_router=router,
        )
        agents.append(agent)

    return agents, router  # Return router for exemplar storage
```

**Breaking change (callers)**: `_initialize_agents` previously returned only `agents`; it now returns **`(agents, router)`**. Every caller must unpack the tuple and pass `router` into the simulation loop for exemplar storage, Monte Carlo handoff, and (when applicable) persistence. Migration:

| Before | After |
| --- | --- |
| `agents = await self._initialize_agents(...)` | `agents, router = await self._initialize_agents(...)` |
| N/A | Use `router` in `run_simulation` for `store_exemplar`, `with_preloaded_exemplars`, etc. |

**`run_simulation` change**: After the priming round(s), store exemplars.

In the round loop, after round `cloud_rounds` completes:

```python
# After round completes and stances are updated:
if (
    router.mode == "hybrid"
    and round_num == router.cloud_rounds
):
    for agent in agents:
        agent_msgs = [
            m for m in round_state.messages
            if m.agent_id == agent.id
        ]
        router.store_exemplar(agent.id, agent_msgs)
    logger.info(
        "Hybrid: stored round-%d exemplars for %d agents",
        round_num, len(agents),
    )
```

**Monte Carlo change (hybrid, iterations > 1)**:

1. **Copy 1 (iteration 0)** runs like any other simulation: `InferenceRouter` is created inside `create_simulation`, round 1 uses the cloud path, and after the priming round finishes `run_simulation` stores exemplars on that router (same as non–Monte Carlo hybrid).

2. **After copy 1 completes**, the Monte Carlo layer must obtain that router and build a **follow-up router** for copies 2–N:
   - Extract the `InferenceRouter` instance used by copy 1 (e.g. via `SimulationEngine.get_agent_router(copy_1_sim_id)` after `run_simulation` returns).
   - Hold it in a **shared slot for the Monte Carlo batch**—in this codebase that is a **local variable** `follow_up_router` on `MonteCarloRunner.run` (not a field on `SimulationEngine`). An implementation could alternatively stash the same reference on the engine if that simplified testing or persistence.
   - Set `follow_up_router = router.with_preloaded_exemplars()` **once** after iteration 0 succeeds. That method returns a **new** `InferenceRouter` with `mode="hybrid"`, `cloud_rounds=0`, and the exemplar map carried over (shallow copy of the per-agent dicts so payloads stay aligned with copy 1). With `cloud_rounds=0`, routing sends **all** rounds to the local provider immediately; `mode="hybrid"` keeps exemplar injection and analytics/report cloud routing behavior correct.

3. **Copies 2–N** call `create_simulation(iter_config, inference_router=follow_up_router)` so each copy reuses that pre-primed router—no second cloud priming round.

**Where the lifecycle handoff lives (this repo)**:

- **`SimulationEngine._maybe_run_inline_monte_carlo`** (wizard “inline Monte Carlo” after the primary sim): prepares the capped iteration count, strips conflicting wizard flags, and **delegates** to `MonteCarloRunner(self).run(...)`. It does **not** extract the router itself; it is the **entry point** that starts the batch after the primary simulation has already finished.

- **`MonteCarloRunner.run`** in `backend/app/simulation/monte_carlo.py`: owns the **extraction**, **`follow_up_router` binding**, and **per-iteration wiring**. After iteration `i == 0` completes, it calls `get_agent_router(sim_id)` on copy 1, then `follow_up_router = router.with_preloaded_exemplars()`, and passes `inference_router=follow_up_router` into `create_simulation` for `i > 0`. Standalone Monte Carlo (non-inline) uses the same runner and the same handoff.

The router needs a method to support this:

```
def with_preloaded_exemplars(self) -> InferenceRouter:
```

Returns a new `InferenceRouter` with `mode="hybrid"` and `cloud_rounds=0` and exemplars derived from copy 1 as implemented in `InferenceRouter.with_preloaded_exemplars` (see `backend/app/llm/inference_router.py`).

### 5.6 Capabilities Endpoint

New endpoint in `backend/app/llm/router.py`:

```
GET /api/llm/capabilities
```

Response schema:

```json
{
  "hybrid_available": true,
  "local_provider": "ollama",
  "local_model": "qwen3:14b",
  "default_inference_mode": "hybrid"
}
```

```json
{
  "hybrid_available": false,
  "local_provider": null,
  "local_model": null,
  "default_inference_mode": "cloud"
}
```

**Detection logic** (executed on each request, cached for 60 seconds):

1. Is `settings.local_llm_provider` configured (non-empty)?
   - No: return `hybrid_available: false`.
2. Create local provider instance via `get_local_llm_provider()`.
3. Call `provider.test_connection()` with a **5-second** timeout (aligned with `OllamaProvider` / `LlamaCppProvider` `test_connection()`).
   - Success: return `hybrid_available: true` with provider/model details.
   - Failure: return `hybrid_available: false`.

The 60-second cache prevents hammering the local provider on every wizard page load. The implementation stores a module-level `(result, timestamp)` pair and guards cache reads/writes with an **`asyncio.Lock`** plus double-checked locking so concurrent capability requests do not race on refresh (async-safe under the FastAPI event loop).

### 5.7 Frontend Changes

**Wizard Step 4** (`frontend/src/app/simulations/new/page.tsx`):

On mount, fetch `GET /api/llm/capabilities`. Store result in component state.

If `hybrid_available === true`, render:

```
+----------------------------------------------------------+
|  [ ] Use local hardware for faster simulation            |
|                                                          |
|  Round 1 uses your cloud provider for quality            |
|  calibration. Subsequent rounds run locally.             |
+----------------------------------------------------------+
```

If `hybrid_available === false`, render nothing. The parameters section looks identical to today.

When the toggle is on, set `inference_mode: "hybrid"` in the `CreateSimulationRequest.parameters`. When off (or not shown), omit the field entirely -- backend defaults to `"cloud"`.

**API client** (`frontend/src/lib/api.ts`):

Add:

```typescript
interface InferenceCapabilities {
  hybridAvailable: boolean;
  localProvider: string | null;
  localModel: string | null;
  defaultInferenceMode: string;
}

async getInferenceCapabilities(): Promise<InferenceCapabilities>
```

Normalize snake_case response to camelCase as with other endpoints. On fetch failure, return `{ hybridAvailable: false, ... }` -- fail silent, default to cloud.

**Simulation detail page** (`frontend/src/app/simulations/[id]/page.tsx`):

Show a small badge or info line indicating which inference mode was used:

```
Inference: Hybrid (cloud-primed)
```

or simply:

```
Inference: Cloud
```

This is informational only, read from the simulation's stored parameters.

## 6. Data Flow

### 6.1 Standard Hybrid Simulation (6 agents, 10 rounds)

```
1. Frontend → POST /api/simulations
   { ..., parameters: { inference_mode: "hybrid" } }

2. Engine runs `await InferenceRouter.create(cloud, local, "hybrid", cloud_rounds=1)`

3. Round 1 (cloud):
   - 6x generate_response → cloud provider
   - 6x cast_vote → cloud provider
   - 6x update_stance → cloud provider
   - Router stores exemplars for all 6 agents

4. Rounds 2-10 (local, with exemplars):
   - 6x generate_response → local provider (exemplar injected)
   - 6x cast_vote → local provider (exemplar injected)
   - 6x update_stance → local provider (exemplar injected)

5. Post-sim:
   - analytics → cloud provider
   - report → cloud provider

6. Monte Carlo (if enabled, 25 copies):
   - Copy 1: same as steps 3-4 above (its own cloud round 1)
   - Copies 2-25: router.with_preloaded_exemplars()
     - All 10 rounds → local provider (copy-1 exemplars)
```

### 6.2 Cloud API Call Count Comparison

| Scenario | Cloud-only | Hybrid | Reduction |
| --- | --- | --- | --- |
| Single sim (6 agents, 10 rounds) | ~120 | ~20 (round 1 + reports) | 83% |
| Monte Carlo x25 | ~3,000 | ~40 (round 1 x2 + reports) | 99% |

### 6.3 Prompt Stack (Local Provider, Post-Priming)

```
[0] System: persona prompt (archetype + seed docs + research)
[1] User: STYLE CALIBRATION (exemplar from round 1)      ← NEW
[2] User: SIMULATION CONTEXT + round/phase/stance
[3] User: RECENT CONVERSATION (last 10 messages)
[4] User: INSTRUCTION (phase-specific)
[5] User: "Provide your response as your character would speak."
```

Message [1] is the only addition. It is omitted in cloud mode or when no exemplars exist.

## 7. Error Handling

| Scenario | Behavior |
| --- | --- |
| Local provider unreachable at simulation start | Router degrades to `mode="cloud"`, logs warning. Simulation proceeds on cloud. |
| Local provider fails mid-simulation (round 3+) | Agent's `_throttled_generate` retries (existing 3x retry logic). If all retries fail, agent produces error fallback message (existing behavior). |
| Local provider unreachable at capabilities check | Endpoint returns `hybrid_available: false`. Frontend hides toggle. |
| `inference_mode=hybrid` set in `.env` but no local provider configured | Router detects `local is None` at init, degrades to cloud. |
| `inference_mode=local` set in `.env` but no local provider | Router raises `ValueError` at init. Fail fast -- `local` mode is explicit developer intent. |
| Exemplar storage called but round 1 had agent errors | Exemplars for that agent are empty. Local rounds proceed without exemplar injection for that agent (graceful degradation, not failure). |
| Monte Carlo copy receives empty exemplar store | Runs without exemplars on local provider. Quality is lower but simulation completes. |

## 8. Performance Projections

Based on research benchmarks (see `claudedocs/research_hybrid_llm_architecture_20260404.md`) and the user's M5 Max 128GB hardware.

### 8.1 Single Simulation (6 agents, boardroom, 10 rounds)

| Phase | Cloud-only | Hybrid |
| --- | --- | --- |
| Round 1 | ~8s | ~8s (cloud) |
| Rounds 2-10 | ~67s | ~27s (local, no rate limits, higher parallelism) |
| Reports/analytics | ~10s | ~10s (cloud) |
| **Total** | **~85s** | **~45s (47% faster)** |

### 8.2 Monte Carlo x25

| Phase | Cloud-only | Hybrid |
| --- | --- | --- |
| Copy 1 (full hybrid) | ~85s | ~45s |
| Copies 2-25 (all local) | 24 x ~85s = ~34 min | 24 x ~35s = ~14 min |
| **Total** | **~36 min** | **~14.5 min (60% faster)** |

### 8.3 Cost

| Scenario | Cloud-only | Hybrid | Savings |
| --- | --- | --- | --- |
| Single sim | ~120 API calls | ~20 API calls | 83% |
| Monte Carlo x25 | ~3,000 API calls | ~40 API calls | 99% |

### 8.4 Quality

| Task | Local vs Cloud Quality | Impact |
| --- | --- | --- |
| Response generation (with exemplars) | ~90% | Acceptable -- exemplars anchor voice/style |
| Voting (with exemplars) | ~95% | Minimal -- structured output |
| Stance updates (with exemplars) | ~95% | Minimal -- short summarization |
| Strategic reasoning (complex phases) | ~70% | Mitigated by round-1 trajectory being cloud-set |
| **Aggregate simulation quality** | **~90-95%** | **Within goal of 5% degradation** |

## 9. Testing Strategy

### 9.1 Unit Tests

| Test | What it validates |
| --- | --- |
| `test_router_cloud_mode` | `get_provider` always returns cloud provider in cloud mode. |
| `test_router_hybrid_routing` | Returns cloud for round <= cloud_rounds, local for round > cloud_rounds. |
| `test_router_hybrid_always_cloud_for_reports` | task_type "analytics" and "report" always return cloud in hybrid mode. |
| `test_router_local_mode` | Always returns local provider. |
| `test_router_fallback_on_unreachable_local` | Degrades to cloud mode when local `test_connection` fails. |
| `test_router_local_mode_fails_without_provider` | Raises `ValueError` when mode is "local" but no local provider. |
| `test_exemplar_storage_and_retrieval` | Store messages, retrieve as `LLMMessage` list with correct structure. |
| `test_exemplar_truncation` | Exemplar content respects character limits (500/300/200). |
| `test_exemplar_empty_when_no_data` | Returns empty list when no exemplars stored for agent. |
| `test_with_preloaded_exemplars` | Returns new router in local mode with same exemplar store. |
| `test_agent_injects_exemplars` | In hybrid mode with local provider, exemplar message appears at position [1]. |
| `test_agent_no_exemplars_in_cloud_mode` | In cloud mode, no exemplar message in prompt. |
| `test_capabilities_cache` | Second call within 60s returns cached result without calling `test_connection`. |

### 9.2 Integration Tests

| Test | What it validates |
| --- | --- |
| `test_hybrid_simulation_end_to_end` | Full simulation with mock cloud + mock local. Verify round 1 uses cloud mock, rounds 2+ use local mock, exemplars are injected. |
| `test_cloud_only_backward_compat` | Simulation with default config produces identical call pattern to current code. |
| `test_monte_carlo_exemplar_sharing` | Monte Carlo copies 2+ receive exemplars from copy 1 and run all-local. |
| `test_capabilities_endpoint_local_available` | With mock local provider, endpoint returns `hybrid_available: true`. |
| `test_capabilities_endpoint_no_local` | Without local config, endpoint returns `hybrid_available: false`. |

### 9.3 Quality Validation (Manual / Future Automation)

Run identical simulations in cloud-only vs hybrid mode and compare:

- Vote outcome distributions across 10 runs (should be statistically similar).
- Agent voice consistency (manual review: does agent sound the same across rounds?).
- Strategic coherence (do agent positions evolve logically?).

## 10. Migration and Backward Compatibility

### 10.1 Zero-Breaking-Change Guarantee

- All new config vars have defaults that produce current behavior.
- `inference_mode` defaults to `"cloud"`.
- `SimulationAgent` constructor change is internal -- no public API change.
- Existing simulations in the database are unaffected (no schema change).
- The capabilities endpoint is additive.
- The frontend toggle is hidden by default.

### 10.2 Migration Path

1. Deploy backend with new config vars (all defaulted). No behavior change.
2. User installs Ollama (or another supported local OpenAI-compatible stack) and sets `LOCAL_LLM_*` in `.env`.
3. Capabilities endpoint starts returning `hybrid_available: true`.
4. Frontend toggle appears automatically.
5. User opts in per-simulation via the toggle.

No migration script. No database changes. No feature flags.

## 11. Future Enhancements (Out of Scope)

These are explicitly excluded from this spec but documented as natural extensions:

- **Semantic cache layer**: Cache LLM responses by prompt similarity. Independent of routing -- can be added as middleware in `provider.py` later.
- **Dynamic RouteLLM routing**: Replace static task-type routing with ML-based complexity classification per prompt. Requires training data from production simulations.
- **Confidence-based escalation**: Local model self-scores confidence; low-confidence responses automatically re-routed to cloud. Requires logprob support from local provider.
- **Multi-model local tier**: Different local models for different task types (small for votes, large for responses). Adds complexity without proportional benefit at this stage.
- **vllm-mlx migration**: Switching from Ollama to vllm-mlx for higher concurrent throughput. Independent infrastructure change -- the `InferenceRouter` works with any OpenAI-compatible local provider.
- **Per-simulation `hybrid_cloud_rounds` override**: Letting users choose how many cloud rounds to run (1, 2, 3). The config exists but is not exposed in the wizard UI initially.

## 12. File Change Summary (retrospective)

Inventory of components **as shipped** with this feature; use for navigation and ownership, not as a rollout status board.

| File | Delivery | Description |
| --- | --- | --- |
| `backend/app/llm/inference_router.py` | Shipped | `InferenceRouter` class with routing, exemplar storage, exemplar prompt building. |
| `backend/app/config.py` | Shipped | `inference_mode`, `local_llm_provider` (default `""`), `local_llm_base_url`, `local_llm_model_name`, `hybrid_cloud_rounds`. |
| `backend/app/llm/factory.py` | Shipped | `get_local_llm_provider()` returns `None` when provider is unconfigured. |
| `backend/app/llm/router.py` | Shipped | `GET /api/llm/capabilities` endpoint with 60s cached probe. |
| `backend/app/llm/ollama_provider.py` | Shipped (hardening) | `test_connection()` uses 5s request timeout (was default ~30s). |
| `backend/app/llm/llamacpp_provider.py` | Shipped (hardening) | `test_connection()` uses 5s request timeout (was 300s client default). |
| `backend/app/simulation/agent.py` | Shipped | Accepts `InferenceRouter`, passes `round_number`/`task_type`, injects exemplars. |
| `backend/app/simulation/engine.py` | Shipped | Router init with both providers, exemplar storage after priming round, Monte Carlo passthrough. |
| `backend/app/simulation/monte_carlo.py` | Shipped | Extracts router from copy 1, passes `with_preloaded_exemplars()` to copies 2+. |
| `.env.example` | Shipped | Commented `LOCAL_LLM_*` and `INFERENCE_MODE` vars. |
| `frontend/src/lib/api/llm.ts` | Shipped | `getInferenceCapabilities()` method and `InferenceCapabilities` type. |
| `frontend/src/lib/types/index.ts` | Shipped | `hybridLocalEnabled` and `inferenceMode` on `SimulationConfig`. |
| `frontend/src/app/simulations/new/page.tsx` | Shipped | Fetches capabilities, conditionally renders hybrid toggle in Step 4. |
| `frontend/src/app/simulations/[id]/page.tsx` | Shipped | Inference mode badge (Cloud / Hybrid / Local). |
| `backend/tests/test_inference_router.py` | Shipped | Unit tests for `InferenceRouter` (routing, exemplars, `create`, `with_preloaded_exemplars`). |
| `backend/tests/test_hybrid_simulation.py` | Shipped | Integration tests: engine + agent hybrid wiring, Monte Carlo follow-up router, end-to-end agent generate path. |
| `backend/tests/test_llm_capabilities.py` | Shipped | `GET /api/llm/capabilities` caching and `hybrid_available` (with / without local provider). |
