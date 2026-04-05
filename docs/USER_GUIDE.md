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
8. [Research](#research)
9. [API Keys](#api-keys)
10. [CLI Usage](#cli-usage)
11. [Configuration Reference](#configuration-reference)

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

### Creating Custom Playbooks

Navigate to `/playbooks` and use the creation interface to define new templates. You can also auto-generate playbooks from a description using the AI copilot.

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

### Running Simulations

**Path**: `/simulations/[id]`

Once launched, the simulation detail page shows:
- **Agent panels** -- each agent's actions and reasoning per round
- **Round progress** -- current round, total rounds, status
- **Controls** -- Start, Pause, Resume (no Stop button; use Delete to terminate)

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
| Chat | `/simulations/[id]/chat` | Interactive chat with simulation agents |
| Sensitivity | `/simulations/[id]/sensitivity` | Sensitivity analysis of key variables |
| Network | `/simulations/[id]/network` | Relationship network visualization |
| ZOPA | `/simulations/[id]/zopa` | Zone of Possible Agreement analysis |
| Fairness | `/simulations/[id]/fairness` | Fairness and bias assessment |
| Timeline | `/simulations/[id]/timeline` | Chronological event timeline |
| Audit Trail | `/simulations/[id]/audit-trail` | Detailed event log with hash verification |
| Report | `/simulations/[id]/report` | Generated narrative report |
| Market Intel | `/simulations/[id]/market-intel` | Market intelligence overlay |
| Voice | `/simulations/[id]/voice` | Voice input/output for agent interaction |
| Attribution | `/simulations/[id]/attribution` | Source attribution tracking |
| Rehearsal | `/simulations/[id]/rehearsal` | Rehearsal/practice mode |

### Backtesting and Comparison

- **Backtesting** (`/simulations/backtest`): Run simulations against historical data to validate strategy models
- **Comparison** (`/simulations/compare`): Side-by-side comparison of multiple simulation outcomes

---

## Personas

**Path**: `/personas`

Personas define the behavioral archetypes for simulation agents.

### Persona Library

Browse and manage pre-built persona archetypes. Each persona includes:
- Role definition (competitor, regulator, customer, etc.)
- Behavioral traits and biases
- Decision-making patterns
- Communication style

### Persona Designer

**Path**: `/personas/designer`

Create custom personas using the visual designer. Define traits, objectives, and behavioral parameters.

### Interview-Based Extraction

Upload interview transcripts or notes, and the AI extracts persona archetypes automatically, identifying behavioral patterns, motivations, and decision criteria.

### Axioms

**Path**: `/personas/axioms`

Define foundational rules and constraints that govern agent behavior across simulations.

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

### Multi-Language Support

The seed system supports documents in multiple languages. Content is processed and made available to agents regardless of the source language.

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

### Export Formats

Reports can be exported as:
- PDF
- PowerPoint (PPTX)
- Markdown
- JSON

---

## Analytics

**Path**: `/analytics`

### Post-Simulation Analytics

When "Post-Run Analytics" is enabled, the analytics agent automatically processes simulation data to detect:
- Emergent behavioral patterns
- Coalition formation
- Decision convergence/divergence
- Strategic equilibria

### Cross-Simulation Analytics

**Path**: `/analytics/cross-simulation`

Compare patterns across multiple simulations to identify meta-trends, strategy robustness, and scenario sensitivity.

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

| Variable | Required | Description |
|----------|----------|-------------|
| `LLM_PROVIDER` | Yes | LLM provider key |
| `LLM_API_KEY` | For cloud providers | API key |
| `LLM_MODEL_NAME` | Yes | Model name |
| `LLM_BASE_URL` | No | Override for Azure/proxies |

### LLM Providers

| Provider | Key | Requirements |
|----------|-----|--------------|
| OpenAI | `openai` | `LLM_API_KEY` |
| Anthropic | `anthropic` | `LLM_API_KEY` |
| Ollama | `ollama` | Local Ollama running |
| llama.cpp | `llamacpp` | Local llama.cpp server |
| Claude CLI | `cli-claude` | Claude CLI installed |
| ChatGPT CLI | `cli-chatgpt` | OpenAI CLI installed |
| Gemini CLI | `cli-gemini` | Gemini CLI installed |

### Hybrid Inference

Run some rounds locally and others in the cloud:

```bash
INFERENCE_MODE=hybrid
LOCAL_LLM_PROVIDER=ollama
LOCAL_LLM_BASE_URL=http://localhost:11434/v1
LOCAL_LLM_MODEL_NAME=qwen3:14b
HYBRID_CLOUD_ROUNDS=1    # every Nth round uses cloud
```

### Simulation Limits

| Variable | Default | Description |
|----------|---------|-------------|
| `SIMULATION_MAX_AGENTS` | 48 | Max agents per simulation |
| `SIMULATION_LLM_PARALLELISM` | 4 | Concurrent LLM calls |
| `SIMULATION_ROUND_TIMEOUT_SECONDS` | 0 (off) | Per-round wall-clock timeout |

### Database

The defaults in the table below are for **local development** (for example, Neo4j on `localhost` or via Docker). Do not rely on these values in production.

| Variable | Default | Description |
|----------|---------|-------------|
| `NEO4J_URI` | `bolt://localhost:7687` | Neo4j connection |
| `NEO4J_USER` | `neo4j` | Neo4j username |
| `NEO4J_PASSWORD` | `password` | Neo4j password |

In production, use strong, unique credentials and load them from a secure source (for example, a secret manager), not copied from local defaults.

Neo4j is optional. The backend degrades gracefully to SQLite if Neo4j is unavailable.
