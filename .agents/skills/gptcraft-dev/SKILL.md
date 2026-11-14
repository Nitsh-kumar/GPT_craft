---
name: gptcraft-dev
description: >-
  Start, configure, or debug the local development environment for the GPTCraft
  monorepo (FastAPI backend on port 8000 and React/Vite frontend on port 3000).
  Use this skill when the user asks to run the app, bootstrap the local
  environment, or add full-stack features across FastAPI, LangGraph, and React.
---

# GPTCraft Development & Full-Stack Workflow Skill

## 1. Environment Bootstrap

If `.env` files or dependencies are not yet initialized:

```powershell
# Backend setup
cd backend
if (!(Test-Path .venv)) { python -m venv .venv }
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (!(Test-Path .env)) { Copy-Item .env.example .env }

# Frontend setup
cd ../frontend
if (!(Test-Path node_modules)) { npm install }
if (!(Test-Path .env)) { Copy-Item .env.example .env }
```


## 2. Starting Development Servers

- **Backend API (`http://localhost:8000`, Swagger UI at `/docs`)**:
  ```powershell
  cd backend
  .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
  ```
- **Frontend UI (`http://localhost:3000`)**:
  ```powershell
  cd frontend
  npm run dev
  ```
- Or launch both via helper script:
  ```powershell
  powershell -ExecutionPolicy Bypass -File scripts/dev.ps1
  ```

## 3. Adding a Full-Stack Feature or AI Tool

1. **AI / LangGraph Layer (`backend/app/ai/`)**:
   - Add new tools in `backend/app/ai/tools/` and bind them in `backend/app/ai/graph/agent.py`.
   - Extend `AgentState` in `backend/app/ai/graph/state.py` if additional state keys are required.
2. **Database & Service Layer (`backend/app/db/`, `backend/app/services/`)**:
   - Update models in `backend/app/db/models.py` and CRUD logic in `backend/app/db/`.
   - Update `ChatService` or `AuthService` in `backend/app/services/`.
3. **API & Schema Contract (`backend/app/schemas/`, `backend/app/api/routes/`)**:
   - Update Pydantic models and FastAPI routes.
   - Add or update tests in `backend/tests/`.
4. **Frontend Sync (`frontend/src/`)**:
   - Mirror schema updates in `frontend/src/types/index.ts`.
   - Update API calls in `frontend/src/services/chatService.ts` or `authService.ts`.
   - Route streaming responses through `src/utils/sseParser.ts` (`parseSseBuffer`) to handle both typed Agent Studio envelopes and conversational frames.
   - Update hooks (`useChat.ts`, `useQuota.ts`) and UI components (`src/components/`).
5. **Verify**:
   - Run frontend unit tests (`cd frontend; npm run test:unit`) and TypeScript checks (`npm run lint`).
   - Run full-stack verification: `powershell -ExecutionPolicy Bypass -File scripts/verify.ps1`.
