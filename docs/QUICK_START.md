# ScenarioLab Quick Start

Get the platform running in under 5 minutes.

## Prerequisites

| Tool | Version | Check |
|------|---------|-------|
| Node.js | Any recent LTS | `node -v` |
| Python | 3.11+ | `python3 --version` |
| uv | Latest | `uv --version` |
| Docker | Latest (optional) | `docker --version` |

## 1. Clone and Configure

```bash
git clone <repo-url> && cd ScenarioLab
cp .env.example .env
```

Edit `.env` with your LLM provider credentials:

```bash
# Minimum required settings
LLM_PROVIDER=openai          # or: anthropic, ollama, cli-claude, cli-chatgpt, cli-gemini
LLM_API_KEY=sk-your-key      # not needed for ollama/llamacpp/cli-* providers
LLM_MODEL_NAME=gpt-4         # model name for your chosen provider
```

## 2. Start the Platform

```bash
# Full stack (recommended) — installs deps, starts Neo4j + backend + frontend
./start.sh

# Without Neo4j (lighter, falls back to SQLite)
./start.sh --no-neo4j

# Skip dependency install (after first run)
./start.sh --skip-install
```

## 3. Open the App

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API docs | http://localhost:5001/docs |
| Neo4j Browser | http://localhost:7474 (if enabled) |

## 4. Run Your First Simulation

1. Open http://localhost:3000
2. Click **Simulations** in the sidebar
3. Click **New Simulation**
4. Follow the 5-step wizard:
   - **Step 1**: Pick a playbook (e.g., "M&A Culture Clash")
   - **Step 2**: Adjust agent counts per role
   - **Step 3**: Optionally attach seed documents
   - **Step 4**: Set rounds (default 10), environment type, and model
   - **Step 5**: Review and click **Launch**
5. Watch agents interact in real-time on the simulation detail page

## 5. CLI Alternative (Headless)

```bash
cd backend

# List available playbooks
uv run scenariolab-sim list-playbooks

# Run a simulation
uv run scenariolab-sim simulate --playbook mna-culture-clash --rounds 5

# With a seed document
uv run scenariolab-sim simulate --playbook pricing-war --seed ../data/market-report.pdf
```

## Stopping

Press `Ctrl+C` in the terminal running `start.sh`. It will prompt whether to stop the Neo4j container.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Port 3000/5001 already in use | `start.sh` auto-kills stale processes, or manually: <code>lsof -ti:3000 &#124; xargs kill</code> |
| Neo4j won't start | Run `docker ps` to check; try `./start.sh --no-neo4j` to skip it |
| LLM errors | Verify `LLM_API_KEY` in `.env`; test with `curl http://localhost:5001/api/llm/test -X POST` |
| Frontend shows mock data | Backend isn't running — check terminal output for errors |
| Python version too low | Install Python 3.11+ via `pyenv install 3.11` or Homebrew |

## Next Steps

- Read the full [User Guide](./USER_GUIDE.md) for feature walkthroughs
- See the [Manual Testing Guide](./MANUAL_TESTING.md) for end-to-end verification
- Explore the API at http://localhost:5001/docs
