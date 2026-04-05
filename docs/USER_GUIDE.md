# ScenarioLab User Guide

ScenarioLab is an AI-powered war-gaming and simulation platform for strategy consultants. It lets you model competitive scenarios with AI agents representing stakeholders (competitors, regulators, customers) and generates analytical reports from the outcomes.

---

## Table of Contents

1. [Dashboard](#dashboard)
2. [Playbooks](#playbooks)
3. [Simulations](#simulations)
4. [Personas](#personas)
5. [Seed Documents](#seed-documents)
6. [Reports](#reports)
7. [Analytics](#analytics)
8. [Scenario Branching](#scenario-branching)
9. [Backtesting](#backtesting)
10. [Annotations](#annotations)
11. [Research](#research)
12. [Fine-Tuning](#fine-tuning)
13. [External API (v1)](#external-api-v1)
14. [API Keys](#api-keys)
15. [CLI Usage](#cli-usage)
16. [Configuration Reference](#configuration-reference)

---

## Dashboard

The home page (`/`) provides an overview of your recent simulations, active runs, and quick-access links. Use the sidebar to navigate between features.

---

## Playbooks

**Path**: `/playbooks`

Playbooks are reusable simulation templates that define the scenario, agent roles, and interaction rules.

### Built-in Playbooks

ScenarioLab ships with templates for common strategy scenarios:
- M&A culture clash
- Pricing war
- Regulatory response
- Market entry
- Negotiation

### Playbook Structure

Each playbook defines:
- **Name and description** -- the strategic scenario
- **Agent roster** -- roles and their default counts (e.g., 2 Competitors, 1 Regulator, 3 Customers)
- **Environment type** -- boardroom, war room, negotiation, or integration
- **Interaction rules** -- turn order, visibility, information asymmetry

### Vertical Libraries

Industry-specific scenario packs are available for quick starts:
- **Pharma** -- drug approval, patent cliff, regulatory compliance
- **Oil & Gas** -- ESG tightening, supply disruption, energy transition
- **Fintech** -- disruption scenarios, regulatory sandbox, market entry
- **Tech** -- AI talent flight, platform competition, antitrust
- **Financial Services** -- market stress, compliance overhaul, M&A integration
- **Political** -- policy rollout, geopolitical risk, election impact

Browse verticals via `GET /api/playbooks/verticals` and get scenarios for a specific vertical via `GET /api/playbooks/verticals/{vertical}`.

### Creating Custom Playbooks

Navigate to `/playbooks` and use the creation interface to define new templates. You can also auto-generate playbooks from a description using the AI copilot.

### Playbook Co-Pilot

Upload seed material and the AI suggests:
- Most relevant playbook template
- Agent roster and counts
- Key entities to model
- Recommended simulation parameters
- Missing information gaps

Use `POST /api/seeds/analyze` for initial analysis and `POST /api/seeds/analyze/refine` for iterative refinement.

---

## Simulations

### Creating a Simulation

**Path**: `/simulations/new`

The 5-step wizard guides you through simulation setup:

#### Step 1: Select Playbook

Choose a template from the library. The wizard lazy-loads the full agent roster when you select a playbook. You can also arrive here with a pre-selected playbook via `?playbook=<id>`.

#### Step 2: Configure Agents

Adjust the number of agents per role using the sliders. The total agent count updates live. Maximum is 48 agents per simulation (configurable via `SIMULATION_MAX_AGENTS`).

#### Step 3: Seed Documents

Optionally attach documents to enrich agent context:
- Select from previously uploaded documents
- Upload new files inline (PDF, DOCX, TXT, Markdown)
- Documents are injected into every agent's system prompt

#### Step 4: Set Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| Rounds | Number of interaction rounds | 10 |
| Environment Type | boardroom, war_room, negotiation, integration | Varies by playbook |
| Model | LLM model for agent reasoning | From `.env` config |
| Monte Carlo Iterations | Statistical sampling runs | 20 |
| Post-Run Report | Auto-generate report after completion | On |
| Post-Run Analytics | Auto-run analytics after completion | On |
| Extended Seed Context | Include full document text (vs. summaries) | Off |

A **cost estimate** is displayed based on your configuration.

#### Step 5: Review and Launch

Confirm all settings and click **Launch Simulation**. You'll be redirected to the simulation detail page.

### Regulatory Scenario Generator

**Path**: `/simulations/new/regulatory`

Auto-generate simulation scenarios from regulatory text:
1. Paste or upload regulatory text
2. The LLM summarizes the regulation and generates a scenario configuration
3. An agent roster appropriate for the regulation type is auto-suggested
4. Review and launch directly into the simulation wizard

### Running Simulations

**Path**: `/simulations/[id]`

Once launched, the simulation detail page shows:
- **Agent panels** -- each agent's actions and reasoning per round
- **Round progress** -- current round, total rounds, status
- **Controls** -- Start, Pause, Resume (no Stop button; use Delete to terminate)

### Gamification & Scoring

For interactive war games with client teams, enable the optional gamification layer:

- Configure scoring (`POST /api/simulations/{id}/gamification/configure`): Set scoring weights and team assignments
- View leaderboard (`GET /api/simulations/{id}/leaderboard`): Real-time scores across 2-6 competing teams
- Update after rounds (`POST /api/simulations/{id}/leaderboard/update`): Refresh scores after each round
- Metrics tracked: consensus points, speed, risk reduction score

### Simulation Controls

| Action | Trigger | Notes |
|--------|---------|-------|
| Start | Click Start button | Begins round execution |
| Pause | Click Pause button | Suspends after current round completes |
| Resume | Click Resume button | Continues from paused state |
| Delete | Click Delete button | Terminates and removes the simulation |

### Simulation Sub-Pages

Each simulation has specialized views accessible via tabs:

| Tab | Path | Purpose |
|-----|------|---------|
| Chat | `/simulations/[id]/chat` | Interactive chat with any agent; context-aware responses referencing simulation events; history persists per simulation |
| Sensitivity | `/simulations/[id]/sensitivity` | Tornado chart visualization showing which parameters have biggest impact on outcomes; ranks parameters by impact magnitude |
| Network | `/simulations/[id]/network` | Force-directed graph: nodes = agents, edges = communications; color-coded by sentiment (green = agreement, red = conflict); click nodes for transcripts |
| ZOPA | `/simulations/[id]/zopa` | Zone of Possible Agreement analysis for negotiation simulations; shows each party's range, overlap, and concession recommendations |
| Fairness | `/simulations/[id]/fairness` | Bias/fairness audit via perturbation analysis; detects statistically significant disparities with mitigation recommendations |
| Timeline | `/simulations/[id]/timeline` | Interactive timeline slider to scrub round-by-round; bookmark key turning points; export annotated timelines |
| Audit Trail | `/simulations/[id]/audit-trail` | Immutable event log with SHA-256 hash chain; verify integrity; export as JSON or CSV |
| Report | `/simulations/[id]/report` | Narrative report with executive summary, risk register, scenario matrix, and stakeholder heatmap |
| Market Intel | `/simulations/[id]/market-intel` | Live market data feed (Alpha Vantage, News API); configure sources; inject data into agent worldviews |
| Voice | `/simulations/[id]/voice` | Natural voice conversation with agents via Whisper transcription + TTS; supports workshop mode |
| Attribution | `/simulations/[id]/attribution` | Shapley value outcome attribution; quantifies which agents/coalitions drove specific outcomes with confidence intervals |
| Rehearsal | `/simulations/[id]/rehearsal` | Practice presentations against AI counterpart agents; get objections, pushback, and feedback |

### Dual-Create Simulations

The platform supports creating pairs of simulations atomically for A/B comparison:

- **Dual Create** (`POST /api/simulations/dual-create`): Creates two simulations as a rollback-safe pair. If the second creation fails, the first is automatically deleted.
- **Dual Run Preset** (`POST /api/simulations/dual-run-preset`): Preview two simulation payloads without persisting.
- **Dual Run Preset Create** (`POST /api/simulations/dual-run-preset-create`): Preview and create both in one call.

### Backtesting and Comparison

- **Backtesting** (`/simulations/backtest`): Run simulations against historical data to validate strategy models. Feed pre-event seed materials and compare simulated outcomes against known post-event results. Bundled historical cases available via `GET /api/simulations/backtest/cases`.
- **Comparison** (`/simulations/compare`): Side-by-side comparison of multiple simulation outcomes with shared metrics dashboard.

### Real-Time Updates (WebSocket)

Connect to `ws://localhost:5001/api/simulations/ws/{id}` for live simulation updates including round progress, agent actions, and status changes.

---

## Personas

**Path**: `/personas`

Personas define the behavioral archetypes for simulation agents. ScenarioLab ships with 13+ consulting-specific archetypes.

### Persona Library

Browse and manage pre-built persona archetypes. Each persona includes:
- **Role** -- functional position (CEO, CFO, CRO, Board Member, etc.)
- **Authority level** -- decision-making power (1-10 scale)
- **Risk tolerance** -- conservative, moderate, or aggressive
- **Information bias** -- qualitative, quantitative, or balanced
- **Decision speed** -- fast, moderate, or slow
- **Coalition tendencies** -- likelihood to form alliances
- **Incentive structure** -- financial, reputational, or operational motivations

### Persona Designer

**Path**: `/personas/designer`

Create custom personas using the visual designer:

1. Define role, traits, objectives, and behavioral parameters
2. Optionally ground the persona with web research (`POST /api/personas/designer`)
3. Validate coherence (`POST /api/personas/designer/validate`) to check for contradictory traits
4. Refresh research (`POST /api/personas/designer/{id}/refresh-research`) to re-fetch live web evidence and merge into the persona
5. Update or delete personas as needed

Research-backed personas use web search (Tavily) to ground agent behavior in real-world data about specific executives or stakeholder types.

### Interview-Based Extraction

Upload interview transcripts or notes, and the AI extracts persona archetypes automatically:

- `POST /api/personas/extract-interview` -- extract persona attributes from interview text
- `GET /api/personas/interview-protocol` -- get the standard interview question set (10-15 questions)

The system analyzes responses to calibrate parameters like risk tolerance, decision speed, and coalition tendencies.

### Counterpart Agents (Executive Coach Mode)

Create AI counterpart agents for rehearsing presentations:

1. Create a counterpart from a base archetype (`POST /api/personas/counterpart/create`)
2. Run rehearsal turns (`POST /api/personas/counterpart/{id}/rehearse`) -- the counterpart generates pushback calibrated to the stakeholder
3. Generate objections (`POST /api/personas/counterpart/{id}/objections`) -- produces 5+ relevant objections
4. Get feedback summary (`GET /api/personas/counterpart/{id}/feedback`) -- structured feedback from the rehearsal session

Access via the `/simulations/[id]/rehearsal` tab after simulation completion, or standalone via the API.

### Axioms

**Path**: `/personas/axioms`

Extract and validate behavioral axioms from historical decision patterns:

- **Extract** (`POST /api/personas/axioms/extract`) -- analyze board minutes, earnings calls, or prior war game outputs to extract behavioral rules (e.g., "This client's CFO voted for risk mitigation 85% of the time")
- **Validate** (`POST /api/personas/axioms/validate`) -- test extracted axioms against holdout data for accuracy

---

## Seed Documents

**Path**: `/upload`

Seed documents provide real-world context to simulation agents.

### Uploading Documents

1. Navigate to `/upload`
2. Drag and drop files or click to browse
3. Supported formats: PDF, DOCX, TXT, Markdown
4. Documents are processed and stored for reuse

### How Seeds Work

When attached to a simulation, seed document content is injected into agent system prompts. This grounds agent reasoning in real market data, company information, or regulatory text.

### Upload Reliability

The upload system supports safe abort when a browser disconnects mid-upload:
- Each upload receives an `X-Client-Upload-Id` header
- Acknowledge completion: `POST /api/seeds/upload/ack-client-id`
- Cancel on disconnect: `POST /api/seeds/upload/cancel-by-client-id`
- Batch delete: `POST /api/seeds/delete-batch`

### Multi-Language Support

The seed system supports documents in 8+ languages (English, German, French, Spanish, Japanese, Mandarin Chinese, Korean, Portuguese, Arabic). Features:
- Automatic language detection (`POST /api/seeds/detect-language`)
- Translation to English for processing (`POST /api/seeds/translate`)
- Full multilanguage pipeline (`POST /api/seeds/process-multilanguage`)

---

## Reports

**Path**: `/reports`

### Auto-Generated Reports

When "Post-Run Report" is enabled in simulation parameters, ScenarioLab automatically generates a narrative report after simulation completion.

### Report Sections

Reports include:
- **Executive Summary** -- key findings and recommendations
- **Risk Register** -- identified risks ranked by severity
- **Scenario Matrix** -- outcome comparison across scenarios
- **Stakeholder Heatmap** -- agent interaction intensity and alignment

### Review Checkpoints

Reports support human-review checkpoints at each pipeline stage:
- Create a checkpoint: `POST /api/reports/{id}/checkpoint`
- Update checkpoint status (approve/reject): `PATCH /api/reports/{id}/checkpoint/{checkpoint_id}`

### Export Formats

Reports can be exported as:
- **PDF** -- presentation-ready document
- **Markdown** -- for version control and editing
- **JSON** -- structured data for programmatic consumption
- **Miro** -- auto-generated Miro board with frames, app cards, and sticky notes (requires `MIRO_API_TOKEN`)
- **Interactive Deck** -- self-contained HTML presentation with embedded JS; supports branding via `logo_url`, `primary_color`, and `company_name` query params; works offline

---

## Analytics

**Path**: `/analytics`

### Post-Simulation Analytics

When "Post-Run Analytics" is enabled, the analytics agent automatically processes simulation data to detect:
- Emergent behavioral patterns (deviations from archetype baseline)
- Coalition formation and dissolution
- Decision convergence/divergence
- Strategic equilibria
- Sentiment trajectory (LLM-based when available, keyword fallback otherwise)

### Fairness & Attribution

- **Fairness Audit** (`POST /api/analytics/simulations/{id}/fairness-audit`): Run perturbation analysis (e.g., gender-flipped agent names) to detect unintended bias with statistical significance testing
- **Attribution** (`POST /api/analytics/simulations/{id}/attribution`): Shapley value computation showing which agents/coalitions drove specific outcomes

### Cost Estimation

- **Pre-simulation** (`POST /api/analytics/cost-estimate`): Calculate estimated token usage and cost based on agent count, rounds, and Monte Carlo iterations
- **Batch estimate** (`POST /api/analytics/cost-estimate/batch`): Cost estimate for batch runs

### Cross-Simulation Analytics

**Path**: `/analytics/cross-simulation`

Compare patterns across multiple simulations to identify meta-trends, strategy robustness, and scenario sensitivity.

- **Opt in** (`POST /api/analytics/cross-simulation/opt-in`): Opt a simulation into anonymized cross-sim learning (privacy-preserving)
- **View patterns** (`GET /api/analytics/cross-simulation/patterns`): Aggregate behavioral patterns across opted-in simulations
- **Privacy report** (`GET /api/analytics/cross-simulation/privacy-report/{id}`): Verify what data is shared for a simulation
- **Improve archetypes** (`POST /api/analytics/cross-simulation/improve-archetypes`): Get archetype calibration suggestions from aggregate data

### Export

- `GET /api/analytics/simulations/{id}/export/json` -- full analytics as JSON
- `GET /api/analytics/simulations/{id}/export/csv` -- tabular export

---

## Scenario Branching

Create "what-if" scenario branches for systematic exploration of strategic alternatives:

### Creating Branches

- **Create branch** (`POST /api/branches`): Branch from an existing simulation with modified config
- **Create root branch** (`POST /api/branches/root`): Start a new scenario tree

### Exploring the Tree

- **View tree** (`GET /api/branches/tree/{root_id}`): See the full scenario DAG
- **View lineage** (`GET /api/branches/{id}/lineage`): Trace a branch back to root
- **Compare branches** (`POST /api/branches/compare`): Side-by-side metrics comparison
- **Config diff** (`GET /api/branches/{a}/diff/{b}`): See what changed between branches

---

## Backtesting

**Path**: `/simulations/backtest`

Validate strategy models against historical outcomes:

1. Browse bundled historical cases (`GET /api/simulations/backtest/cases`) or provide your own
2. Configure simulation with pre-event seed materials only
3. Run backtest (`POST /api/simulations/backtest`)
4. Compare simulated outcomes against known post-event results

Accuracy is measured across three dimensions: stakeholder stance accuracy, timeline accuracy, and outcome direction accuracy.

---

## Annotations

Add inline commentary to simulation events during replay:

- **Create** (`POST /api/annotations`): Annotate any agent statement with agree/disagree/caveat tags
- **List** (`GET /api/simulations/{id}/annotations`): View all annotations, filterable by tag type
- **Export** (`GET /api/simulations/{id}/annotations/export`): Download as JSON
- **Delete** (`DELETE /api/annotations/{id}`): Remove an annotation

Annotations persist with the simulation and appear in exported reports (PDF, Miro, Interactive Deck). Multiple consultants can annotate the same simulation collaboratively.

---

## Research

The autoresearch module provides AI-powered background research for simulations.

### Research Types

| Type | Endpoint | Description |
|------|----------|-------------|
| Company | `/api/research/company` | Company profiles, financials, strategy |
| Industry | `/api/research/industry` | Market structure, trends, dynamics |
| Regulation | `/api/research/regulation` | Regulatory landscape, compliance |
| Executive | `/api/research/executive` | Leadership profiles, decision patterns |
| Historical Case | `/api/research/historical-case` | Precedent analysis |

### Research Sources

- **Tavily** -- web search (requires `TAVILY_API_KEY`)
- **SEC EDGAR** -- US securities filings (requires `SEC_USER_AGENT`)
- **EUR-Lex** -- EU regulatory documents
- **Alpha Vantage** -- market data (requires `ALPHA_VANTAGE_API_KEY`)
- **News API** -- current events (requires `NEWS_API_KEY`)

---

## Fine-Tuning

**Path**: `/fine-tuning`

Train domain-specific model variants using LoRA/QLoRA for more authentic agent behaviors.

### Workflow

1. **Prepare dataset** (`POST /api/llm/fine-tune/prepare-dataset`): Format training data (earnings calls, regulatory testimony, board minutes, etc.)
2. **Start job** (`POST /api/llm/fine-tune/start`): Launch a fine-tuning job with LoRA/QLoRA
3. **Monitor** (`GET /api/llm/fine-tune/status/{job_id}`): Track progress
4. **Activate** (`POST /api/llm/fine-tune/activate/{adapter_id}`): Switch to fine-tuned adapter for inference
5. **Benchmark** (`POST /api/llm/fine-tune/benchmark`): Run domain-specific benchmarks to validate improvement

### Management

- `GET /api/llm/fine-tune/jobs` -- list all fine-tuning jobs
- `GET /api/llm/fine-tune/adapters` -- list available LoRA adapters
- Adapters are typically <100MB for efficient storage

### Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `FINE_TUNE_DATA_DIR` | `./fine_tune_data` | Training data directory |
| `FINE_TUNE_OUTPUT_DIR` | `./fine_tune_output` | Output directory for adapters |

---

## External API (v1)

The external API at `/api/v1/` provides programmatic access for third-party integrations. All endpoints require `Authorization: Bearer <key>`.

### API Key Management (Admin)

Requires the admin key (`ADMIN_API_KEY` from `.env`):

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/api-keys` | Create API key with scopes |
| GET | `/api/v1/api-keys` | List all API keys |
| DELETE | `/api/v1/api-keys/{id}` | Revoke an API key |

### Simulation Operations

Requires API key with appropriate scopes:

| Method | Path | Scope |
|--------|------|-------|
| POST | `/api/v1/simulations` | `write:simulations` |
| GET | `/api/v1/simulations/{id}` | `read:simulations` |
| GET | `/api/v1/simulations/{id}/results` | `read:simulations` |
| POST | `/api/v1/simulations/{id}/start` | `write:simulations` |
| GET | `/api/v1/reports/{id}` | `read:reports` |

### Webhooks

Register webhooks for event notifications:

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/webhooks` | Register webhook URL |
| GET | `/api/v1/webhooks` | List registered webhooks |
| DELETE | `/api/v1/webhooks/{id}` | Remove webhook |

---

## API Keys

**Path**: `/api-keys`

Manage integration API keys for external access to ScenarioLab.

### Setup

1. Set `ADMIN_API_KEY` in `.env` to a long random secret
2. Navigate to `/api-keys`
3. Enter the admin key when prompted (stored per browser tab)
4. Create, list, and revoke API keys

---

## CLI Usage

ScenarioLab includes a headless CLI for scripted simulation runs.

### Commands

```bash
cd backend

# List available playbooks
uv run scenariolab-sim list-playbooks

# Run a simulation
uv run scenariolab-sim simulate \
  --playbook mna-culture-clash \
  --rounds 10 \
  --environment boardroom \
  --output markdown

# With seed document
uv run scenariolab-sim simulate \
  --playbook pricing-war \
  --seed ../data/market-report.pdf \
  --name "Q4 Pricing Analysis"

# Check simulation status
uv run scenariolab-sim status <simulation-id>

# Get results
uv run scenariolab-sim results <simulation-id> --output json
uv run scenariolab-sim results <simulation-id> --section executive_summary
```

### Output Sections

The `results` command supports `--section` filtering:
- `full` -- complete report
- `executive_summary` -- key findings only
- `risk_register` -- risk assessment
- `scenario_matrix` -- outcome comparison
- `stakeholder_heatmap` -- interaction analysis

### Remote Mode

Connect the CLI to a running ScenarioLab backend instead of running locally:

```bash
uv run scenariolab-sim simulate --playbook pricing-war --api-url http://scenariolab.example.com:5001
```

---

## Configuration Reference

All configuration is via environment variables in `.env`. See `.env.example` for the full list.

### Core Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LLM_PROVIDER` | Yes | `openai` | LLM provider key (see table below) |
| `LLM_API_KEY` | For cloud providers | | API key for cloud providers |
| `LLM_MODEL_NAME` | Yes | `gpt-4` | Model identifier sent to provider |
| `LLM_BASE_URL` | No | `https://api.openai.com/v1` | Override for Azure/proxies |
| `LLM_CONCURRENCY_DEFAULT` | No | `3` | Max concurrent LLM calls |
| `LLM_CONCURRENCY_OVERRIDES` | No | | JSON map for per-provider overrides, e.g. `{"cli-claude":2}` |
| `DEBUG` | No | `false` | Exposes exception messages in HTTP error responses; **never enable in production** |

### LLM Providers

| Provider | Key | Requirements |
|----------|-----|--------------|
| OpenAI | `openai` | `LLM_API_KEY` |
| Anthropic | `anthropic` | `LLM_API_KEY` |
| Google | `google` | `LLM_API_KEY` |
| Qwen | `qwen` | `LLM_API_KEY` |
| Ollama | `ollama` | Local Ollama running |
| llama.cpp | `llamacpp` | Local llama.cpp server |
| Claude CLI | `cli-claude` | Claude CLI installed |
| ChatGPT CLI | `cli-chatgpt` | OpenAI CLI installed |
| Gemini CLI | `cli-gemini` | Gemini CLI installed |
| Codex CLI | `cli-codex` | Codex CLI installed |

All CLI providers use a subprocess with bounded timeout (default 120s). Timeouts are configurable:

| Variable | Default | Description |
|----------|---------|-------------|
| `CLAUDE_CLI_TIMEOUT` | `120.0` | Claude CLI subprocess timeout (seconds) |
| `CLAUDE_CLI_VERSION_CHECK_TIMEOUT` | `10.0` | Claude CLI version check timeout |
| `GEMINI_CLI_TIMEOUT` | `120.0` | Gemini CLI subprocess timeout |
| `GEMINI_CLI_VERSION_CHECK_TIMEOUT` | `5.0` | Gemini CLI version check timeout |

### Hybrid Inference

Run some rounds locally and others in the cloud:

```bash
INFERENCE_MODE=hybrid          # cloud (default), hybrid, or local
LOCAL_LLM_PROVIDER=ollama      # ollama or llamacpp
LOCAL_LLM_BASE_URL=http://localhost:11434/v1
LOCAL_LLM_MODEL_NAME=qwen3:14b
HYBRID_CLOUD_ROUNDS=1          # every Nth round uses cloud
```

Probe hybrid availability: `GET /api/llm/capabilities` (cached).

### Simulation Limits

| Variable | Default | Description |
|----------|---------|-------------|
| `SIMULATION_MAX_AGENTS` | 48 | Max agents per simulation |
| `SIMULATION_LLM_PARALLELISM` | 4 | Concurrent LLM calls during simulation |
| `SIMULATION_ROUND_TIMEOUT_SECONDS` | 0 (off) | Per-round wall-clock timeout; set >0 to auto-terminate stuck rounds |
| `INLINE_MONTE_CARLO_MAX_ITERATIONS` | 25 | Max Monte Carlo iterations when triggered from wizard |

### Database

The defaults in the table below are for **local development** (for example, Neo4j on `localhost` or via Docker). Do not rely on these values in production.

| Variable | Default | Description |
|----------|---------|-------------|
| `NEO4J_URI` | `bolt://localhost:7687` | Neo4j connection |
| `NEO4J_USER` | `neo4j` | Neo4j username |
| `NEO4J_PASSWORD` | `password` | Neo4j password |

In production, use strong, unique credentials and load them from a secure source (for example, a secret manager), not copied from local defaults.

Neo4j is optional. The backend degrades gracefully to SQLite if Neo4j is unavailable.

### Graphiti (temporal simulation memory)

When `GRAPHITI_ENABLED=true`, the backend runs **[Graphiti](https://github.com/getzep/graphiti)** against Neo4j (same Bolt URI; database name from `NEO4J_GRAPHITI_DATABASE`, default `neo4j`). Each completed simulation **round** is ingested as an episode with `group_id` equal to the simulation id. Deleting a simulation removes that partition from Graphiti.

Graphiti’s default LLM and embedder expect an **OpenAI** API key: set `GRAPHITI_OPENAI_API_KEY`, or use `LLM_PROVIDER=openai` with `LLM_API_KEY`, or `OPENAI_API_KEY`.

| Variable | Default | Description |
|----------|---------|-------------|
| `GRAPHITI_ENABLED` | `false` | Enable temporal memory |
| `NEO4J_GRAPHITI_DATABASE` | `neo4j` | Separate database recommended for production |
| `GRAPHITI_OPENAI_API_KEY` | | Falls back to `LLM_API_KEY` when provider is openai |
| `GRAPHITI_MAX_COROUTINES` | | Max concurrent Graphiti operations |
| `GRAPHITI_INJECT_AGENT_CONTEXT` | `false` | Prepend retrieved facts to agent prompts (extra cost per turn) |

Endpoints:
- Status: `GET /api/graph/temporal-memory-status`
- Search (scoped to one simulation): `POST /api/graph/temporal/search` with JSON `{ "simulation_id", "query", "limit" }`

### Integrations

| Variable | Default | Description |
|----------|---------|-------------|
| `MIRO_API_TOKEN` | | Miro REST API token for board export |
| `MIRO_BOARD_ID` | | Target Miro board ID |
| `MCP_SERVER_ENABLED` | `false` | Enable built-in MCP server |
| `TAVILY_API_KEY` | | Web search for autoresearch |
| `SEC_USER_AGENT` | `ScenarioLab/1.0 ...` | Required for SEC EDGAR API |
| `ALPHA_VANTAGE_API_KEY` | | Market intelligence data |
| `NEWS_API_KEY` | | News feed for market intelligence |
| `ADMIN_API_KEY` | | Protects `/api/v1/api-keys` admin routes |

### Voice & Transcription

| Variable | Default | Description |
|----------|---------|-------------|
| `WHISPER_MODEL` | `whisper-1` | Whisper model for transcription |
| `TTS_VOICE` | `alloy` | TTS voice selection |
| `TTS_MODEL` | `tts-1` | TTS model |
