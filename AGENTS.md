# GPTCraft — Monorepo Architecture & Agent Rules

You are working inside the **GPTCraft** monorepo: a production-bound AI conversation platform inspired by ChatGPT and Claude, built with FastAPI + LangGraph + SQLAlchemy on the backend and React 19 + TypeScript + Vite + Tailwind CSS v4 on the frontend.

## Repository Layout

```text
GPT_craft/
├── .agents/                # Antigravity (AGY) CLI harness: skills, hooks, scripts
├── backend/                # Python FastAPI + LangGraph + SQLAlchemy API
│   ├── AGENTS.md           # Backend-specific architecture and rules
│   ├── app/                # FastAPI application source (`app.*`)
│   ├── tests/              # Pytest unit and integration tests
│   └── requirements.txt    # Python dependencies
├── frontend/               # React 19 + TypeScript + Vite SPA
│   ├── AGENTS.md           # Frontend-specific architecture and rules
│   ├── src/                # React components, hooks, context, services, types
│   └── package.json        # Node dependencies and scripts
├── docs/                   # Project status, architectural decision records, roadmaps
└── scripts/                # Cross-stack verification and dev helper scripts
```

## Core Architectural Principles

1. **Working Directory Discipline**:
   - Backend commands (`pytest`, `uvicorn`, `alembic`) must be executed from `backend/` (or with `PYTHONPATH=backend`) because imports use `from app....`.
   - Frontend commands (`npm run dev`, `npm run lint`, `npm run build`) must be executed from `frontend/`.

2. **Cross-Stack Contract Alignment**:
   - Whenever you modify a Pydantic schema in `backend/app/schemas/` or a route in `backend/app/api/routes/`, you **must** verify and update the corresponding TypeScript interfaces in `frontend/src/types/index.ts` and API clients in `frontend/src/services/`.
   - User plans follow the tier hierarchy: `free`, `super`, `hyper` (with legacy `pro` mapped to paid tier).
   - Auth responses (`/auth/login` and `/auth/register`) return camelCase `accessToken`, `tokenType`, and `user`.

3. **Security & Secrets**:
   - Never expose LLM provider keys (`GROQ_API_KEY`, etc.) or signing secrets (`SECRET_KEY`) in frontend `VITE_*` variables or client bundles. All LLM inference and quota accounting must go through the backend API.
   - Never commit `.env` or `.db` files. Update `backend/.env.example` and `frontend/.env.example` whenever new environment variables are introduced.

4. **Verification Before Completion**:
   - Before declaring any task complete, run the verification suite via `powershell -ExecutionPolicy Bypass -File scripts/verify.ps1` (or activate the `gptcraft-verify` skill) to ensure both backend `pytest` and frontend `tsc --noEmit` + `vite build` pass with zero errors.

5. **Mem0 Persistent Memory & Harness Integration**:
   - The agent harness is integrated with **Mem0** (platform backend scoped to `nit2314`).
   - On `SessionStart`, active memories are automatically retrieved and injected into the agent's context.
   - Use the `mem0-memory` skill or `.agents/scripts/mem0_helper.ps1` to query (`search`), add (`add`), or inspect (`list`) long-term memories.
   - Always persist significant architectural decisions, user preferences, custom runbooks, and resolved defects to Mem0 so that they survive across conversations.
