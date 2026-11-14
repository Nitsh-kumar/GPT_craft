---
name: gptcraft-verify
description: >-
  Run the full-stack verification suite for the GPTCraft monorepo (backend pytest
  tests, frontend unit tests, frontend TypeScript type-checking, and frontend production Vite build).
  Use this skill before completing any feature, bugfix, or refactor, or when the
  user asks to test, validate, or check the health of the project.
---

# GPTCraft Full-Stack Verification Skill

Use this workflow to verify that both `backend/` and `frontend/` compile, type-check, and pass all automated contract and unit tests.

## Quick Full-Stack Check

Run the unified verification script from the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/verify.ps1
```

## Individual Stack Checks

### 1. Backend Verification (`backend/`)
Ensure the virtual environment exists at `backend/.venv`, then run `pytest`:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -v
```

### 2. Frontend Verification (`frontend/`)
Run the unit test suite, TypeScript compiler check (`lint`), and Vite production build:

```powershell
cd frontend
npm run test:unit
npm run lint
npm run build
```

## Troubleshooting Failures
- **Schema / Contract Mismatch**: Compare `backend/app/schemas/` against `frontend/src/types/index.ts` and `frontend/src/services/`.
- **Missing Python Dependencies**: Install into `backend/.venv` via `backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt`.

- **Missing Node Modules**: Run `npm install` inside `frontend/`.
