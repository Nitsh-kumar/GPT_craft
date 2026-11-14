---
name: gptcraft-dev
description: >-
  Start, configure, or debug the local development environment for the GPTCraft
  Personal Agent monorepo (FastAPI backend on port 8000 and React/Vite frontend
  on port 3000). Use this skill when the user asks to run the app, bootstrap the
  local environment, or add full-stack features across FastAPI, LangGraph, and React.
---

# GPTCraft Development & Full-Stack Workflow Skill

Refer to `docs/OPERATIONS.md` as the canonical reference for runtime versions (Python 3.12, Node 24), dependency management, database migrations, accounting rules, API/SSE contracts, and verification commands.

## 1. Environment Bootstrap

If `.env` files or dependencies are not yet initialized:

```powershell
# Backend setup (Windows PowerShell / pwsh)
cd backend
if (!(Test-Path .venv)) { python -m venv .venv }
.\.venv\Scripts\python.exe -m pip install --require-hashes -r requirements-dev.lock
if (!(Test-Path .env)) { Copy-Item .env.example .env }
.\.venv\Scripts\python.exe -m app.db.migrate

# Frontend setup
cd ../frontend
if (!(Test-Path node_modules)) { npm ci }
if (!(Test-Path .env)) { Copy-Item .env.example .env }
```

On POSIX (`pwsh` / shell), use `.venv/bin/python` instead of `.\.venv\Scripts\python.exe`. Always install backend development dependencies with `--require-hashes -r requirements-dev.lock`, and use `npm ci` in `frontend/`. Never commit `.env` files, provider keys, or local `.db` artifacts.

## 2. Starting Development Servers

Always run explicit schema migration before starting the backend (application import does not create tables or seed plans):

- **Backend API (`http://localhost:8000`, Swagger UI at `/docs`)**:
  ```powershell
  cd backend
  .\.venv\Scripts\python.exe -m app.db.migrate
  .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
  ```
- **Frontend UI (`http://localhost:3000`)**:
  ```powershell
  cd frontend
  npm run dev
  ```
- Or launch both on Windows via helper script (after initial migration):
  ```powershell
  pwsh -ExecutionPolicy Bypass -File scripts/dev.ps1
  ```

## 3. Adding a Full-Stack Feature or AI Tool

1. **AI / LangGraph Layer (`backend/app/ai/`)**:
   - Add new workspace tools in `backend/app/ai/tools/` and bind them in `backend/app/ai/graph/agent.py`.
   - Extend `AgentState` in `backend/app/ai/graph/state.py` if additional state keys are required.
2. **Database & Service Layer (`backend/app/db/`, `backend/app/services/`)**:
   - Update models in `backend/app/db/models.py`, explicit migrations in `backend/app/db/migrate.py`, and CRUD helpers in `backend/app/db/`.
   - Update `ChatService`, `AuthService`, or `MemoryService` in `backend/app/services/`. (Runtime user memory and preferences live in SQLAlchemy `UserPreferences` and `UserMemory` via `backend/app/services/memory.py`, never Mem0.)
3. **API & Schema Contract (`backend/app/schemas/`, `backend/app/api/routes/`)**:
   - Update Pydantic models and FastAPI routes, preserving existing casing contracts (camelCase for auth, quota, memory preferences/memories, and Agent Studio SSE envelopes; snake_case for legacy conversation/chat/SSE metadata per `docs/OPERATIONS.md`).
   - Add or update offline tests in `backend/tests/` using the documented provider factory fakes.
4. **Frontend Sync (`frontend/src/`)**:
   - Mirror schema updates in `frontend/src/types/index.ts`.
   - Update API clients in `frontend/src/services/chatService.ts`, `authService.ts`, or `memoryService.ts`.
   - Route streaming responses through `frontend/src/utils/sseParser.ts` (`parseSseBuffer`) to handle both typed Agent Studio envelopes and conversational frames.
   - Update hooks (`frontend/src/hooks/useChat.ts`, `useQuota.ts`) and UI components (`frontend/src/components/`).
5. **Verify**:
   - Run frontend unit tests (`npm run test:unit`), stream contract tests (`npm test`), TypeScript type checks (`npm run lint`), and production build (`npm run build`) inside `frontend/`.
   - Run backend offline tests (`.\.venv\Scripts\python.exe -m pytest -q` or `.venv/bin/python -m pytest -q`) inside `backend/`.
   - Run full-stack verification on Windows: `pwsh -ExecutionPolicy Bypass -File scripts/verify.ps1`.
