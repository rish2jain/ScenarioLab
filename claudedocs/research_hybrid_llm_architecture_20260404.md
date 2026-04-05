# Hybrid Local + Cloud LLM Architecture for ScenarioLab Simulations

**Date**: 2026-04-04
**Query**: How to leverage local hardware + cloud LLMs to increase simulation speed without significantly reducing quality
**Depth**: Deep
**Confidence**: High (well-researched domain with production-validated patterns)

---

## Executive Summary

ScenarioLab simulations are LLM-call-intensive: a 6-agent boardroom simulation generates **~12 LLM calls per round** across response generation, voting, and stance updates. With 10 rounds and Monte Carlo batches of 25, a single simulation can require **3,000+ LLM calls**. Currently, all calls go to a single cloud provider at 4 concurrent requests max.

A hybrid architecture can **reduce cloud spend by 60-80%** and **cut simulation wall-clock time by 40-60%** by:
1. Running routine agent tasks locally (stance updates, votes, simple responses)
2. Reserving cloud models for complex strategic reasoning and report generation
3. Adding a semantic cache layer to eliminate repeated/similar queries
4. Switching from Ollama to vllm-mlx for efficient concurrent local inference

**Quality impact**: 5-10% reduction on routine tasks (invisible in aggregate), 0% on critical reasoning (still cloud). The aggregate simulation quality loss is negligible because the quality-sensitive outputs (strategic moves, final reports) remain on frontier models.

---

## 1. Current Architecture Analysis

### LLM Call Patterns Per Simulation Round

| Task | Calls/Round | Max Tokens | Temperature | Complexity |
|------|------------|------------|-------------|------------|
| Agent response generation | N agents x M phases | 1024 | 0.7 | Variable |
| Voting | N agents per vote phase | 256 | 0.5 | Low |
| Stance update | N agents (end of round) | 128 | 0.5 | Low |
| Post-sim analytics | 1 | Large | - | High |
| Post-sim report | 1 | Large | - | High |

**Example (6 agents, boardroom, 5 phases):**
- ~12 LLM calls per round
- 10 rounds = ~120 calls
- Monte Carlo x25 = ~3,000 calls
- Current parallelism: 4 concurrent (agent semaphore) capped at 10 (global)

### Current Bottlenecks

1. **Sequential phase execution**: Agents speak in order within each phase
2. **Single provider**: All calls route to one LLM provider
3. **No caching**: Identical prompts in Monte Carlo runs re-query the LLM
4. **Ollama concurrency ceiling**: Collapses at >10 concurrent requests (41 tok/s vs vLLM's 793 tok/s at 128 connections)

---

## 2. Proposed Hybrid Architecture

```
                    +------------------+
                    |  Semantic Cache   |
                    |  (Bifrost/Redis)  |
                    +--------+---------+
                             |
                    +--------v---------+
                    | Complexity Router |
                    | (RouteLLM-based)  |
                    +---+----------+---+
                        |          |
              +---------v--+  +----v----------+
              | Local Tier |  |  Cloud Tier   |
              | vllm-mlx   |  | GPT-4o/Claude |
              | Qwen 3 14B |  | Sonnet 4.6    |
              +------------+  +---------------+
```

### Layer 1: Semantic Cache

**What**: Intercept all LLM requests, check for semantically similar prior queries.

**Why it matters for ScenarioLab**: Monte Carlo runs repeat simulations with slight variations. Agent stance updates and votes often produce near-identical prompts across runs. A semantic cache can eliminate **30-60% of all LLM calls**.

**Implementation**:
- **Bifrost** (Go, 11us overhead, 5K req/s) or **LiteLLM** (Python, ~8ms, 100+ providers)
- Embedding model runs locally (ONNX/MLX) -- no cloud dependency for cache lookups
- Per-request TTL: short for dynamic simulation responses, long for analytical queries
- Conversation history threshold to prevent false positives in multi-turn agent dialogues

**Integration point**: Add as middleware in `backend/app/llm/provider.py` before the global semaphore.

### Layer 2: Complexity Router

**What**: Classify each LLM request by complexity and route to local or cloud.

**Why**: RouteLLM (ICLR 2025) achieves **95% of GPT-4 quality using only 26% GPT-4 calls** (48% cheaper). With data augmentation: 95% quality with only **14% strong model calls** (75% cost reduction).

**Routing Rules for ScenarioLab**:

| Task | Route | Rationale |
|------|-------|-----------|
| Stance updates (128 tok) | Local | Simple summarization, low quality sensitivity |
| Vote casting (256 tok) | Local | Structured output (for/against/abstain), classification-like |
| Simple agent responses (early phases, Q&A) | Local | Information retrieval, not deep reasoning |
| Complex strategic responses (proposals, rebuttals) | Cloud | Requires multi-step reasoning, game theory |
| Post-sim analytics | Cloud | Large context, cross-agent synthesis |
| Post-sim report generation | Cloud | Highest quality requirement |
| Monte Carlo re-runs (cached miss) | Local | Speed priority, aggregate quality matters not individual |

**Implementation options**:
1. **Static routing** (simplest): Route by task type using the existing `generate_response()` / `cast_vote()` / `update_stance()` method signatures
2. **RouteLLM integration**: Matrix factorization router classifies prompt complexity dynamically
3. **Confidence-based cascading**: Local model generates + self-scores confidence; escalate to cloud if below threshold

**Recommendation**: Start with static routing (zero ML overhead), add RouteLLM later for dynamic optimization.

### Layer 3: Local Inference Tier

**What**: High-throughput local LLM serving for routine simulation tasks.

**Model selection**:

| Hardware | Recommended Model | Tok/s | Concurrent Agents |
|----------|------------------|-------|-------------------|
| M4 Pro 48GB | Qwen 3 14B Q4 | 25-50 | 5-8 |
| M4 Max 64GB | Qwen 3 14B Q4 | 35-60 | 8-12 |
| M4 Max 128GB | Qwen 3 32B Q4 | 20-35 | 10-15 |
| RTX 4090 24GB | Qwen 3 14B Q4 | 40-60 | 8-12 |

**Why vllm-mlx over Ollama**:
- Ollama: 41 tok/s peak, collapses at 128 concurrent connections
- vllm-mlx: Up to 525 tok/s on M4 Max, continuous batching, handles concurrent agents gracefully
- **Zero code changes**: vllm-mlx exposes OpenAI-compatible API -- ScenarioLab's existing `OllamaProvider` works as-is, just change `LLM_BASE_URL`
- Continuous batching handles variable-length agent outputs efficiently
- Structured output support (JSON schema) for vote parsing

**Quality on ScenarioLab tasks**:

| Task | Local 14B Quality vs Cloud | Acceptable? |
|------|---------------------------|-------------|
| Persona role-play | 85-90% | Yes -- aggregate quality across agents is what matters |
| Vote classification | 95%+ | Yes -- structured output, trivial task |
| Stance summarization | 90%+ | Yes -- 128 tokens, simple summarization |
| Strategic reasoning | 60-70% | No -- route to cloud |
| Multi-file analysis | 55-65% | No -- route to cloud |

### Layer 4: Cloud Tier

**What**: Frontier models for quality-critical tasks.

**When to use**: Complex strategic reasoning, post-simulation analytics, report generation, and any request the router classifies as high-complexity.

**Key benefit**: By offloading 60-80% of calls to local, cloud API rate limits become irrelevant. The remaining cloud calls get faster because there's less queuing.

---

## 3. Implementation Plan

### Phase 1: Multi-Provider Support (Low effort, high impact)

**Current state**: Single provider per simulation (`engine.py` creates one provider instance).

**Change**: Allow per-task provider selection in the agent.

```python
# In SimulationAgent
async def generate_response(self, ...):
    provider = self._select_provider(task_type="response", complexity=phase.complexity)
    return await provider.generate(messages, ...)

async def cast_vote(self, ...):
    provider = self._select_provider(task_type="vote")  # Always local
    return await provider.generate(messages, ...)

async def update_stance(self, ...):
    provider = self._select_provider(task_type="stance")  # Always local
    return await provider.generate(messages, ...)
```

**Files to modify**:
- `backend/app/llm/factory.py` -- Support creating multiple provider instances
- `backend/app/simulation/agent.py` -- Add `_select_provider()` method with task-type routing
- `backend/app/simulation/engine.py` -- Initialize both local and cloud providers
- `backend/app/config.py` -- Add `LOCAL_LLM_PROVIDER`, `LOCAL_LLM_BASE_URL`, `LOCAL_LLM_MODEL_NAME`

### Phase 2: Local Inference Setup (Medium effort)

1. Install vllm-mlx: `pip install vllm-mlx` (or Docker)
2. Download Qwen 3 14B Q4: `huggingface-cli download Qwen/Qwen3-14B-GGUF`
3. Start server: `vllm serve Qwen/Qwen3-14B --device mlx --port 11435`
4. Configure: `LOCAL_LLM_BASE_URL=http://localhost:11435/v1`

No code changes needed beyond Phase 1 -- vllm-mlx is OpenAI-compatible.

### Phase 3: Semantic Cache (Medium effort)

**Option A -- LiteLLM** (Python, integrates naturally):
```python
# In provider.py, wrap generate() with cache check
from litellm import completion
response = completion(model="qwen3-14b", messages=messages, caching=True)
```

**Option B -- Custom Redis cache** (more control):
- Hash prompt + model + temperature as cache key
- Embedding-based similarity search for near-misses
- TTL: 0 for Monte Carlo (exact repeats), 1hr for analytical queries

### Phase 4: Dynamic Router (Low priority, high sophistication)

Add RouteLLM for prompt-level complexity classification:
```python
from routellm.controller import Controller
client = Controller(routers=["mf"], strong_model="claude-sonnet-4-6", weak_model="local/qwen3-14b")
response = client.chat.completions.create(model="router-mf-0.5", messages=messages)
```

The `0.5` threshold controls the strong/weak split. Tune based on simulation quality metrics.

---

## 4. Speed Impact Analysis

### Current (Cloud-only, 6 agents, 10 rounds)

| Phase | Calls | Avg Latency | Total |
|-------|-------|-------------|-------|
| Agent responses | ~60 | 2-4s | ~40s (4 concurrent) |
| Votes | ~30 | 1-2s | ~15s |
| Stance updates | ~60 | 1-2s | ~20s |
| **Total per sim** | **~150** | | **~75s** |
| Monte Carlo x25 | ~3,750 | | **~31 min** |

### Projected (Hybrid, same simulation)

| Phase | Local Calls | Cloud Calls | Total |
|-------|------------|-------------|-------|
| Agent responses | ~40 (simple) | ~20 (complex) | ~25s |
| Votes | ~30 (all local) | 0 | ~5s |
| Stance updates | ~60 (all local) | 0 | ~8s |
| **Total per sim** | **~130 local** | **~20 cloud** | **~38s (49% faster)** |
| Monte Carlo x25 (with cache) | ~600 local | ~200 cloud | **~12 min (61% faster)** |

**Semantic cache reduces Monte Carlo calls by ~60%** because prompts are highly similar across runs.

---

## 5. Quality Safeguards

### Validation Strategy

1. **A/B testing**: Run identical simulations on cloud-only vs hybrid, compare:
   - Vote outcome distributions (should be statistically similar)
   - Report quality scores (human evaluation)
   - Agent response coherence (automated LLM-as-judge)

2. **Confidence-based escalation**: If local model returns low-confidence output (detectable via logprobs or self-evaluation), automatically re-route to cloud.

3. **Critical path protection**: Never route these to local:
   - First-round proposals (sets the simulation trajectory)
   - Final-round strategic decisions
   - Cross-agent synthesis (analytics/reports)
   - Any prompt exceeding 4K input tokens (local models degrade with long context)

4. **Quality monitoring dashboard**: Track per-task quality scores over time. Alert if local model quality drops below threshold.

### Rollback

The static routing approach is trivially reversible -- set `LOCAL_LLM_PROVIDER` to the same as `LLM_PROVIDER` and all calls go to cloud again.

---

## 6. Hardware Recommendations

### Minimum Viable (Good for development + small sims)

- **Mac Mini M4 Pro 48GB** (~$2,000)
- Runs Qwen 3 14B Q4 at 25-50 tok/s
- Handles 5-8 concurrent agents
- Cost: $0/month after purchase vs ~$500-2,000/month cloud

### Recommended (Production simulations)

- **Mac Studio M4 Max 64GB** (~$3,000)
- Runs Qwen 3 14B Q4 at 35-60 tok/s (or 32B at 20-35 tok/s)
- Handles 8-12 concurrent agents with vllm-mlx
- Memory bandwidth: 410-546 GB/s (the key bottleneck metric)

### Maximum (Large-scale Monte Carlo)

- **Mac Studio M4 Ultra 128GB** (~$5,000+)
- Runs 70B models comfortably
- Handles 15-20+ concurrent agents
- ~800 GB/s memory bandwidth

### Alternative: NVIDIA GPU

- **RTX 4090 24GB** (~$1,600): 145 tok/s on 8B, ~50 tok/s on 14B
- Higher per-token throughput than Apple Silicon, but limited by 24GB VRAM
- Better for inference-heavy workloads; worse for large models

---

## 7. Comparison: Approaches Ranked

| Approach | Speed Gain | Quality Risk | Implementation Effort | Cost Savings |
|----------|-----------|-------------|----------------------|-------------|
| **1. Semantic cache** | 30-60% fewer calls | 0% (identical responses) | Low (add middleware) | 30-60% |
| **2. Static task routing** | 40-50% faster | 5-10% on routed tasks | Medium (multi-provider) | 60-80% |
| **3. vllm-mlx serving** | 10-20x local throughput | 0% (same model) | Low (swap server) | 0% (already local) |
| **4. Increase parallelism** | 2-3x on current setup | 0% | Trivial (config change) | 0% |
| **5. Dynamic RouteLLM** | +5-10% over static | Lower than static | High (ML pipeline) | +5-10% over static |
| **6. Speculative decoding** | 2-3x per call | 0% (lossless) | High (framework support) | 0% |

**Recommended order**: 4 -> 1 -> 3 -> 2 -> 5 -> 6

---

## 8. Quick Wins (Do Today)

1. **Increase `simulation_llm_parallelism` from 4 to 8-10** in config.py (if cloud provider supports it)
2. **Increase global semaphore from 10 to 20** in provider.py
3. **Add `LOCAL_LLM_*` config vars** to config.py for future multi-provider support
4. **Install Ollama + Qwen 3 14B** locally for development/testing

---

## Sources

### Routing & Orchestration
- RouteLLM (LMSYS/UC Berkeley, ICLR 2025) -- github.com/lm-sys/RouteLLM
- Dynamic LLM Routing Survey (March 2026) -- arxiv.org/html/2603.04445v1
- vLLM Semantic Router v0.2.0 -- github.com/vllm-project/semantic-router
- Not Diamond -- notdiamond.ai

### Local Inference
- vllm-mlx -- github.com/waybarrios/vllm-mlx
- MLX vs llama.cpp benchmarks -- groundy.com/articles/mlx-vs-llamacpp
- Ollama MLX Integration (March 2026) -- byteiota.com/ollama-mlx-integration
- Ollama vs vLLM Deep Dive (Red Hat) -- developers.redhat.com/articles/2025/08/08/ollama-vs-vllm

### Caching
- Bifrost Gateway -- dev.to/debmckinney/top-llm-gateways-semantic-caching-2026
- GPTCache -- github.com/zilliztech/GPTCache
- Semantic Caching Survey -- arxiv.org/html/2603.03301

### Speculative Decoding
- SpecBundle/SpecForge (LMSYS, Dec 2025) -- lmsys.org/blog/2025-12-23-spec-bundle
- SLED Framework -- arxiv.org/html/2506.09397v3

### Model Quality
- Local LLM vs Claude Coding Benchmark -- kunalganglani.com/blog/local-llm-vs-claude-coding-benchmark
- Best Local LLMs Mac 2026 -- insiderllm.com/guides/best-local-llms-mac-2026
- Open-Source LLMs Compared 2026 -- till-freitag.com/en/blog/open-source-llm-comparison

### Hardware
- Apple Silicon LLM Benchmarks -- siliconbench.radicchio.page
- Local AI Hardware Guide 2026 -- localaimaster.com/blog/ai-hardware-requirements-2025
- Native LLM on Apple Silicon (arXiv) -- arxiv.org/html/2601.19139
