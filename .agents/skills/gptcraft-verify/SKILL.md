---
name: gptcraft-verify
description: >-
  Run the full-stack and harness verification suites for the GPTCraft Personal
  Agent monorepo (backend pytest, frontend unit tests, frontend TypeScript
  check, frontend stream tests, Vite build, harness checks, and optional
  Playwright browser contract tests). Use this skill before completing any
  feature, bugfix, or refactor, or when the user asks to test or validate the repo.
---

# GPTCraft Full-Stack Verification Skill

Use this workflow to verify that `backend/`, `frontend/`, and `.agents/` harness files compile, type-check, and pass all automated contract, unit, and harness tests. Refer to `docs/OPERATIONS.md` for canonical CI checks and test environment rules.

## Quick Full-Stack Check (Windows)

Run the unified verification script from the repository root:

```powershell
pwsh -ExecutionPolicy Bypass -File scripts/verify.ps1
```

This runs `scripts/check-harness.ps1`, `scripts/test-session-hook.ps1`, backend `pytest -v`, and frontend `npm run test:unit`, `npm run lint`, `npm test`, and `npm run build`.

## Harness & Hook Checks

Run from the repository root to validate `.agents/` hooks, skills, and documentation consistency:

```powershell
pwsh -ExecutionPolicy Bypass -File scripts/test-session-hook.ps1
pwsh -ExecutionPolicy Bypass -File scripts/check-harness.ps1
```

## Individual Stack Checks

### 1. Backend Verification (`backend/`)
Ensure the virtual environment exists at `backend/.venv`, then run `pytest` (SQLite offline suite by default; set `GPTCRAFT_TEST_DATABASE_URL` to a dedicated database containing `test` in its name for PostgreSQL coverage):

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -v
```

On POSIX, run `.venv/bin/python -m pytest -q`.

### 2. Frontend Verification (`frontend/`)
Run unit tests, TypeScript check (`lint`), stream tests (`test`), and Vite production build (`build`) matching `frontend/package.json`:

```powershell
cd frontend
npm run test:unit
npm run lint
npm test
npm run build
```

### 3. Optional Browser Contract Suite (`frontend/`)
Run Playwright contract tests (starts its own Vite dev server and mocks auth/chat; does not verify live Supabase or model providers):

```powershell
cd frontend
npx playwright install chromium
npm run test:e2e
```

## Troubleshooting Failures
- **Schema / Contract Mismatch**: Compare `backend/app/schemas/` against `frontend/src/types/index.ts` and `frontend/src/services/`.
- **Missing Python Dependencies**: Install into `backend/.venv` using the hashed development lock:
  `cd backend; .\.venv\Scripts\python.exe -m pip install --require-hashes -r requirements-dev.lock`
  (or `.venv/bin/python -m pip install --require-hashes -r requirements-dev.lock` on POSIX; see `docs/OPERATIONS.md`).
- **Missing Node Modules**: Run `npm ci` inside `frontend/`.
- **Missing Playwright Browser**: Run `npx playwright install chromium` inside `frontend/`.
