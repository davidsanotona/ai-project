# VC ESG Deal Sourcing Agent

A multi-agent system that researches companies and generates investment memos
with ESG/climate scoring. Built to demonstrate the Multi-Agent Protocol (MCP) pattern
using parallel agent execution, shared state, and conditional routing.

---

## Project Structure

```
vc-esg-agent/
├── .github/
│   └── workflows/
│       ├── ci.yml               # Lint, test, docker build — runs on every PR
│       └── cd.yml               # Build, push, deploy — runs on merge to main
├── agents/
│   ├── company_intel.py         # Phase 1: founding team, funding, business model
│   ├── esg_climate.py           # Phase 2a (parallel): ESG scores, greenwashing, SDG mapping
│   ├── market_analysis.py       # Phase 2b (parallel): TAM, competitors, moat
│   ├── risk_assessment.py       # Phase 3: red flags, regulatory exposure, controversy
│   └── memo_writer.py           # Phase 4: generates final VC investment memo
├── models/
│   └── state.py                 # Shared DealState dataclass — all agents read/write this
├── tools/
│   ├── tool_schemas.py          # MCP-compatible tool definitions for every agent and API
│   ├── search_tools.py          # Tavily search wrapper with mock fallback
│   └── finance_tools.py         # yfinance wrapper for public company financials
├── tests/
│   └── test_pipeline.py         # Unit tests — run in CI without real API keys
├── output/                      # Generated memos and deal state JSON (gitignored)
├── Dockerfile                   # Multi-stage build: builder + slim runtime
├── docker-compose.yml           # Local dev and single-host deployment
├── .env.example                 # API key template — copy to .env and fill in
├── requirements.txt
└── main.py                      # CLI entry point
```

---

## Setup

### Option A: Local Python

```bash
pip install -r requirements.txt

export ANTHROPIC_API_KEY=your_key_here
export TAVILY_API_KEY=your_key_here   # optional — falls back to mock data if not set

python main.py --company "Northvolt" --thesis "Battery storage and clean energy"
```

### Option B: Docker (recommended)

```bash
# 1. Copy and fill in your API keys
cp .env.example .env

# 2. Build the image
docker build -t vc-esg-agent .

# 3. Run a single analysis
docker run --env-file .env -v $(pwd)/output:/app/output \
  vc-esg-agent --company "Northvolt" --thesis "Battery storage"

# Or with docker compose
docker compose run vc-agent --company "Northvolt" --thesis "Battery storage"
```

Memos are written to `./output/` on your host machine via the volume mount.

---

## Usage

```bash
python main.py --company "Northvolt" --thesis "Battery storage and clean energy"
python main.py --company "Tesla" --thesis "EV infrastructure"
python main.py -c "Form Energy" -t "Long duration energy storage"
```

Output is saved to `./output/` as:
- `memo_{company}_{timestamp}.md` — the investment memo
- `state_{company}_{timestamp}.json` — full deal state for audit trail

---

## CI/CD Pipeline

The project uses GitHub Actions with two separate workflows.
CI is for confidence, CD is for speed — they are intentionally decoupled.

### CI — runs on every pull request and push to main

```
lint (flake8)
    └── test (pytest — mock data, no API keys needed)
            └── docker build (verifies image compiles)
```

No PR can be merged unless all three jobs pass.

### CD — runs only on merge to main

```
build Docker image
    └── push to Docker Hub (tagged with git SHA + latest)
            └── deploy to target environment
```

Three deploy targets are supported — uncomment the relevant block in `cd.yml`:

- **Railway** — fastest setup for early-stage, connects directly to the repo
- **Fly.io** — more control than Railway, requires a `fly.toml` in the repo root
- **VPS via SSH** — most control, SSH into server, pull image, restart container

### GitHub Secrets required

| Secret | Used by | Description |
|---|---|---|
| `DOCKER_USERNAME` | CD | Docker Hub username |
| `DOCKER_PASSWORD` | CD | Docker Hub password or access token |
| `RAILWAY_TOKEN` | CD (Option A) | Railway project token |
| `FLY_API_TOKEN` | CD (Option B) | Fly.io API token |
| `VPS_HOST` | CD (Option C) | Server IP or hostname |
| `VPS_USER` | CD (Option C) | SSH username |
| `VPS_SSH_KEY` | CD (Option C) | Private SSH key |

Add secrets at: GitHub repo > Settings > Secrets and variables > Actions

### Running tests locally

```bash
pip install pytest
pytest tests/ -v
```

Tests use mock data only — no API keys required.

---

## Architecture

### Execution flow

```
User Input (company name + investment thesis)
                    |
          [Orchestrator]
                    |
         Phase 1 — sequential
                    |
         [Company Intel Agent]        <- resolves identity, funding, business model
                    |
         Phase 2 — parallel (ThreadPoolExecutor)
          /                  \
[ESG & Climate Agent]   [Market Agent]
  scores, SDGs,           TAM, competitors,
  greenwashing flags       moat
          \                  /
         Phase 3 — sequential (conditional)
                    |
         [Risk Assessment Agent]      <- aggregates red flags from all prior agents
                    |
         Phase 4 — sequential
                    |
         [Memo Writer Agent]          <- produces final investment memo
                    |
         INVEST / WATCH / PASS + markdown memo
```

### Key design decisions

**Shared state over message passing**
All agents read and write a single `DealState` dataclass. This avoids serialization
overhead in a single-process setup. In a distributed MCP deployment, each agent
would return a partial result and the orchestrator merges them — functionally the same pattern.

**Parallel execution in Phase 2**
ESG and Market agents are independent of each other. Running them concurrently with
`ThreadPoolExecutor` halves the wall-clock time for Phase 2. Safe because they write
to non-overlapping state fields (`state.esg` vs `state.market`), so no locking is needed.

**Deterministic recommendation, not LLM-decided**
The INVEST/WATCH/PASS recommendation is computed with explicit rules in
`memo_writer._derive_recommendation()` before Claude writes the narrative memo.
This makes the most critical output auditable and prevents hallucination on the
decision itself. Claude's role is articulation, not decision-making.

**Conditional routing**
If ESG score < 30, the Risk Agent is skipped and the pipeline auto-assigns HIGH risk
and PASS. This reflects a real fund constraint and demonstrates orchestrator-level
business logic that lives outside individual agents.

**Graceful degradation**
Every agent call is wrapped in `_run_agent_safe()`. A search API timeout or malformed
Claude response does not crash the pipeline — the error is logged in `state.errors`,
state is returned unchanged, and downstream agents handle missing fields with null checks.

---

## MCP Protocol connection

In a production Multi-Agent Protocol deployment:
- Each agent module would be its own MCP server
- The orchestrator would call them using `tool_use` messages over HTTP
- Tool definitions in `tools/tool_schemas.py` are already written in MCP-compatible format
- The `docker-compose.yml` has commented stubs showing how each agent becomes its own service

The current implementation uses direct Python function calls to keep the project
self-contained, but the structure maps 1:1 to a real MCP deployment.

---

## Extending the system

- **Feedback loop**: user rates the memo, Memo Writer regenerates with the critique
- **Portfolio overlay**: compare new deal ESG exposure against existing portfolio
- **Sector benchmarking**: score company ESG relative to sector peers, not on an absolute scale
- **Distributed deployment**: each `agents/` module becomes its own MCP server in `docker-compose.yml`
- **Async execution**: replace `ThreadPoolExecutor` with `asyncio` for higher throughput across many concurrent analyses
