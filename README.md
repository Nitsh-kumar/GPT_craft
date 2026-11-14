# GPTCraft — Personal Agent SaaS Platform

GPTCraft is transitioning into an **operator-hosted multi-tenant Personal Agent SaaS**, built with **FastAPI**, **LangGraph**, **SQLAlchemy**, and **Groq** on the backend, and **React 19**, **TypeScript**, **Vite 6**, and **Tailwind CSS v4** on the frontend.

Core SaaS pillars include authenticated user accounts, `free` / `super` / `hyper` plan entitlements with durable UTC token quotas, persistent cross-session memory, live Agent Studio telemetry, and Human-in-the-Loop (HITL) approval gates backed by durable database checkpoints.

> [!IMPORTANT]
> **Multi-Tenant Security Boundaries**: All user conversations, memories, approvals, and LangGraph checkpoints enforce `user_id` ownership and PostgreSQL Row-Level Security (RLS). Host workspace tools ([`backend/app/ai/tools/workspace.py`](backend/app/ai/tools/workspace.py)) and host `stdio` MCP servers ([`backend/app/ai/mcp/manager.py`](backend/app/ai/mcp/manager.py)) are **dev / single-operator gated only** until per-user isolated sandboxes are in place.

## Repository Architecture (Monorepo)

```text
GPT_craft/
├── .agents/                # Antigravity (AGY) CLI harness (skills, hooks, scripts)
├── AGENTS.md               # Root architectural & multi-tenant safety rules
├── CODING_STANDARDS.md     # Code-review conventions (mattpocock-skills)
├── DESIGN.md               # Modern Studio token & UI component guide
├── GLOSSARY.md             # Personal Agent SaaS domain vocabulary
├── api/                    # Optional Vercel serverless ASGI entrypoint (index.py)
├── backend/                # FastAPI + LangGraph + SQLAlchemy backend
│   ├── AGENTS.md           # Backend-specific agent rules
│   ├── app/                # Application source (api, ai, core, db, schemas, services)
│   ├── tests/              # Offline pytest contract and unit test suite
│   ├── .env.example        # Backend environment template
│   ├── mcp_servers.json    # Optional MCP server configuration
│   ├── requirements.in     # Canonical runtime dependency inputs
│   ├── requirements.lock   # Committed hashed runtime lockfile
│   ├── requirements-dev.in # Canonical dev/test dependency inputs
│   ├── requirements-dev.lock # Committed hashed dev/test lockfile
│   └── requirements.txt    # Wrapper referencing requirements.lock
├── frontend/               # React 19 + TypeScript + Vite 6 + Tailwind v4 SPA
│   ├── AGENTS.md           # Frontend-specific agent rules
│   ├── src/                # UI components, hooks, context, API client, types
│   ├── tests/              # Node unit/stream tests
│   ├── e2e/                # Playwright browser contract tests
│   ├── .env.example        # Frontend environment template
│   ├── package.json        # Node dependencies and scripts
│   └── vercel.json         # Optional Vercel frontend-only adapter config
├── docs/                   # Operations runbook, project status, ADRs, specs
├── scripts/                # Verification (verify.ps1), dev launcher, hook tests
├── requirements.txt        # Root wrapper referencing backend/requirements.lock
└── vercel.json             # Optional Vercel full-stack adapter config
```

## Quick Start (Local Development)

Requires **Python 3.12** and **Node 24**.

### 1. Backend Setup (`backend/`)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes -r requirements-dev.lock
Copy-Item .env.example .env
# Edit .env with DATABASE_URL, SECRET_KEY, GROQ_API_KEY, and auth settings
.\.venv\Scripts\python.exe -m app.db.migrate
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

On POSIX shells, use `.venv/bin/python -m pip install --require-hashes -r requirements-dev.lock`. For production/runtime-only installs without test tools, install from `backend/requirements.lock` using `--require-hashes -r requirements.lock`.

Interactive API docs are available at `http://localhost:8000/docs`.

### 2. Frontend Setup (`frontend/`)

```powershell
cd frontend
npm ci
Copy-Item .env.example .env
npm run dev
```

The UI will be served at `http://localhost:3000`.

## Antigravity (AGY) CLI Harness & Verification

This repository is configured with an **Antigravity (AGY) CLI** harness and uses **`mattpocock-skills`** (`code-review`, `codebase-design`, `diagnosing-bugs`, `domain-modeling`, `grilling`, `pr`, `prototype`, `research`, `tdd`, `wizard`, `writing-for-agents`) as primary workflow skills:

- **Hierarchical Rules**: [`AGENTS.md`](AGENTS.md), [`backend/AGENTS.md`](backend/AGENTS.md), and [`frontend/AGENTS.md`](frontend/AGENTS.md).
- **Local Skills (`.agents/skills/`)**:
  - `gptcraft-verify`: Runs full-stack `pytest`, frontend unit/stream tests, `tsc --noEmit`, and `vite build`.
  - `gptcraft-dev`: Bootstraps local environments and guides cross-stack feature work.
  - `mem0-memory`: Manual developer harness memory operations via [`.agents/scripts/mem0_helper.ps1`](.agents/scripts/mem0_helper.ps1) (strictly developer-only; runtime app memory uses SQL in [`backend/app/services/memory.py`](backend/app/services/memory.py)).
  - `keploy`: API test case and mock generation.
  - `mitmproxy`: HTTP/SSE traffic inspection and debugging.
  - `trivy`: Dependency, container, and IaC security scanning.
- **Session Lifecycle Hook**: [`.agents/hooks.json`](.agents/hooks.json) invokes [`.agents/scripts/session_start.ps1`](.agents/scripts/session_start.ps1) for fast, offline-safe repository context at session start.

Run the full-stack verification suite anytime with:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/verify.ps1
```

## Self-Hosted Production Deployment (Primary)

GPTCraft's primary architecture is **cloud-agnostic self-hosted**:

1. **Database & Migration**: Provision PostgreSQL, back up existing data, stop chat traffic, and run [`backend/app/db/migrate.py`](backend/app/db/migrate.py) (`cd backend && python -m app.db.migrate`) as the backend database owner before promoting application code. Migration creates tables and enables PostgreSQL RLS across all internal tables.
2. **Backend ASGI Server**: Install hashed runtime dependencies (`python -m pip install --require-hashes -r backend/requirements.lock`), configure secrets (`DATABASE_URL`, `SECRET_KEY`, `GROQ_API_KEY`, `FRONTEND_URL`, and optional Google/Supabase auth variables), and serve `app.main:app` with Uvicorn/ASGI.
3. **Frontend SPA Build & Reverse Proxy**: Build `frontend/` (`npm ci && npm run lint && npm run build`) and serve `frontend/dist` behind a reverse proxy. Forward `/auth/*`, `/chat`, `/chat/*`, `/memory`, `/memory/*`, `/health`, `/docs`, and `/openapi.json` to FastAPI (preserving streaming disconnect propagation for SSE cancellation) and route SPA `GET` paths to `index.html`.

### Optional PaaS Adapters

- **Vercel ([`vercel.json`](vercel.json), [`frontend/vercel.json`](frontend/vercel.json), [`api/index.py`](api/index.py))**: Import the repository root with the **Other** framework preset (leaving framework unset so root `vercel.json` builds Vite into `public/` and routes API traffic to `api/index.py`). Git auto-deployments are held (`"git": { "deploymentEnabled": false }`). Configure `DATABASE_URL`, `SECRET_KEY`, `GROQ_API_KEY`, `FRONTEND_URL`, and optional `SUPABASE_URL` / public `SUPABASE_ANON_KEY` (never a Supabase service-role key in `VITE_*` variables). Leave `VITE_API_BASE_URL` unset for same-origin calls.
- **Cloudflare (`gpt-craft-backend`)**: Optional worker/backend adapter; scope build triggers in the Cloudflare dashboard to `main` promotions as documented in [`docs/OPERATIONS.md`](docs/OPERATIONS.md).

## Reliability and Release Status

Use Python 3.12 and Node 24. Public paid Plan changes remain disabled pending verified billing (`free`, `super`, `hyper` tiers). Models resolve to actual Groq provider IDs (`openai/gpt-oss-20b`, `openai/gpt-oss-120b`); provider errors are never masked with canned success text.

- [`docs/OPERATIONS.md`](docs/OPERATIONS.md): Authoritative runtime install, maintenance-window migration, accounting policy, HTTP/SSE contract summary, CI checks, and release smoke checks.
- [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md): Shipped versus planned capabilities and release gates.
- [`CODING_STANDARDS.md`](CODING_STANDARDS.md), [`GLOSSARY.md`](GLOSSARY.md), [`DESIGN.md`](DESIGN.md), and `docs/adr/`: Engineering review conventions, domain vocabulary, UI design tokens, and architectural decisions.
