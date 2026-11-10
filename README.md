# GPTCraft — AI Chat & Agent Platform

GPTCraft is a full-stack AI conversation platform built with **FastAPI**, **LangGraph**, **SQLAlchemy**, and **Groq** on the backend, and **React 19**, **TypeScript**, **Vite 6**, and **Tailwind CSS v4** on the frontend.

## Repository Architecture (Monorepo)

```text
GPT_craft/
├── .agents/                # Antigravity (AGY) CLI harness (skills, hooks, scripts)
├── AGENTS.md               # Root architectural rules for AGY CLI
├── backend/                # FastAPI + LangGraph + SQLAlchemy backend
│   ├── AGENTS.md           # Backend-specific agent rules
│   ├── app/                # Application source (api, ai, core, db, schemas, services)
│   ├── tests/              # Automated pytest contract and unit test suite
│   ├── .env.example        # Backend environment template
│   └── requirements.txt    # Python dependencies
├── frontend/               # React 19 + TypeScript + Vite 6 + Tailwind v4 SPA
│   ├── AGENTS.md           # Frontend-specific agent rules
│   ├── src/                # UI components, hooks, context, API client, types
│   ├── .env.example        # Frontend environment template
│   └── package.json        # Node dependencies and scripts
├── docs/                   # Project status and engineering milestones
└── scripts/                # Cross-stack verification (`verify.ps1`) and dev launcher (`dev.ps1`)
```

## Quick Start

### 1. Backend Setup (`backend/`)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env with your GROQ_API_KEY and SECRET_KEY
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```


Interactive API docs are available at `http://localhost:8000/docs`.

### 2. Frontend Setup (`frontend/`)

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

The UI will be served at `http://localhost:3000`.

## Antigravity (AGY) CLI Harness & Verification

This repository is configured with a native AGY CLI harness:
- **Hierarchical Rules**: [`AGENTS.md`](AGENTS.md), [`backend/AGENTS.md`](backend/AGENTS.md), and [`frontend/AGENTS.md`](frontend/AGENTS.md).
- **On-Demand Skills**:
  - `gptcraft-verify`: Runs full-stack `pytest`, `tsc --noEmit`, and `vite build`.
  - `gptcraft-dev`: Bootstraps virtual environments, runs local servers, and guides cross-stack feature development.
- **Session Lifecycle Hook**: [`.agents/hooks.json`](.agents/hooks.json) injects monorepo context at session start.

Run the full-stack verification suite anytime with:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/verify.ps1
```
