# Operations and verification

This document is the single source of truth for GPTCraft runtime setup, cloud-agnostic self-hosted deployment, pre-deploy database migrations, quota accounting, public HTTP/SSE contracts, verification commands, and optional PaaS adapters.

## Runtime and installation

Use Python 3.12 (see [`.python-version`](../.python-version)) and Node 24.

### Development setup

From `backend/`, create `.venv`, install pinned development and runtime dependencies with hash verification, and initialize the schema:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes -r requirements-dev.lock
.\.venv\Scripts\python.exe -m app.db.migrate
```

On POSIX shells, use `.venv/bin/python -m pip install --require-hashes -r requirements-dev.lock` and `.venv/bin/python -m app.db.migrate`. Use the virtual-environment Python for all subsequent backend commands.

From `frontend/`, install Node dependencies cleanly from the lockfile:

```powershell
cd frontend
npm ci
```

### Production runtime setup

Runtime dependencies are pinned with SHA-256 hashes in [`backend/requirements.lock`](../backend/requirements.lock) (excluding test-only packages such as `pytest`). Install production environments directly from the hashed runtime lockfile:

```bash
# From repo root:
python -m pip install --require-hashes -r backend/requirements.lock
# Or from backend/:
python -m pip install --require-hashes -r requirements.lock
```

Root [`requirements.txt`](../requirements.txt) (`-r backend/requirements.lock`) and [`backend/requirements.txt`](../backend/requirements.txt) (`-r requirements.lock`) serve solely as buildpack pointers for optional PaaS adapters.

### Dependency updates

To update Python dependencies, edit [`backend/requirements.in`](../backend/requirements.in) (and [`backend/requirements-dev.in`](../backend/requirements-dev.in) if test tooling changes). Regenerate both hashed lockfiles with `uv pip compile --python-version 3.12 --universal --generate-hashes` (matching the exact compile commands recorded in the header comments of [`backend/requirements.lock`](../backend/requirements.lock) and the dev lockfile, constraining dev resolution against `backend/requirements.lock`), perform a clean `python -m pip install --require-hashes -r requirements-dev.lock` install, and run full-stack verification. Never hand-edit hashes.

## Primary deployment: Cloud-agnostic self-hosted

GPTCraft is designed for cloud-agnostic self-hosted deployment as an operator-hosted multi-tenant Personal Agent SaaS: a FastAPI/Uvicorn ASGI backend, PostgreSQL 16+ with Row-Level Security (RLS), and a built Vite static SPA.

### Topology and reverse proxy

1. **Backend ASGI service**: Run `uvicorn app.main:app` from `backend/` using the production runtime environment. Keep provider keys and signing secrets strictly on the backend.
2. **Database (PostgreSQL + RLS)**: Connect using privileged **backend database owner** credentials. Application code enforces `user_id` ownership across all user data, memories, checkpoints, and pending approvals; PostgreSQL RLS is enabled on all internal tables with no public browser Data API policies.
3. **Frontend SPA**: Build static assets from `frontend/`:
   ```bash
   cd frontend
   npm ci
   npm run lint
   npm run build
   ```
   Serve `frontend/dist/` from your reverse proxy (Nginx, Caddy, Envoy, or CDN). Route `/auth/*`, `/chat`, `/chat/*`, `/memory`, `/memory/*`, `/health`, `/docs`, and `/openapi.json` to the FastAPI ASGI service, and fall back unmatched `GET`/`HEAD` requests to `index.html`.
4. **Streaming & disconnect forwarding**: Disable proxy response buffering for `text/event-stream` (`X-Accel-Buffering: no` is set on SSE responses in [`backend/app/api/routes/chat.py`](../backend/app/api/routes/chat.py)) and ensure the reverse proxy forwards client disconnects to Uvicorn so [`CancellableStreamingResponse`](../backend/app/api/streaming.py) triggers upstream cancellation and quota settlement.

### Environment configuration

- **Backend ([`backend/.env.example`](../backend/.env.example), [`backend/app/core/config.py`](../backend/app/core/config.py))**:
  - `DATABASE_URL`: PostgreSQL connection URL (`postgres://` and `postgresql://` normalize to `postgresql+psycopg2://` in [`backend/app/db/session.py`](../backend/app/db/session.py)).
  - `SECRET_KEY`: Strong random signing key. Startup validation (`validate_runtime_secret_key`) rejects placeholder secrets whenever `DEBUG=False`.
  - `GROQ_API_KEY`: Provider API key (server-side only).
  - `FRONTEND_URL`: Allowed frontend origin for CORS and OAuth redirects.
  - `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_JWT_SECRET`: Optional Supabase Auth JWKS/JWT verification settings (`backend/app/core/security.py`).
  - `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`: Optional Google OAuth settings (`backend/app/api/routes/google_oauth.py`).
  - Accounting and timeout defaults: `MAX_OUTPUT_TOKENS=1024` (`1..4096`), `GENERATION_TIMEOUT_SECONDS=60` (`1..90`), `CHAT_BURST_LIMIT=10` (`1..100`).
- **Frontend ([`frontend/.env.example`](../frontend/.env.example))**:
  - Leave `VITE_API_BASE_URL` unset for same-origin reverse-proxy deployments, or set it to the backend origin when hosted separately.
  - Only public `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` may be exposed in Vite builds; never expose service-role keys or `GROQ_API_KEY`.

### Multi-tenant safety gates

- **Host workspace tools are dev / single-operator gated**: Built-in tools in [`backend/app/ai/tools/workspace.py`](../backend/app/ai/tools/workspace.py) operate directly on the host filesystem/workspace root (`GPTCRAFT_WORKSPACE_ROOT`). Do **not** expose `agent` mode host workspace execution to untrusted multi-tenant SaaS users until per-user isolated workspace sandboxes are implemented.
- **Host `stdio` MCP servers are dev / single-operator gated**: [`MCPManager`](../backend/app/ai/mcp/manager.py) spawns local subprocesses for `stdio` entries in [`backend/mcp_servers.json`](../backend/mcp_servers.json). Keep host `stdio` servers disabled in multi-tenant production unless isolated per user; `MCPManager` also automatically refuses to spawn the development mock server (`app.ai.mcp.mock_server`) when `GPTCRAFT_ENV`, `APP_ENV`, `ENVIRONMENT`, or `ENV` is `prod` or `production`.

## Migration before deployment

Application import and startup no longer create tables or seed data. Current schema tables include `plans`, `users`, `oauth_accounts`, `user_daily_limit`, `conversations`, `messages`, `daily_quotas`, `quota_reservations`, `generation_details`, `user_preferences`, `user_memories`, `agent_approvals`, `agent_checkpoints`, `agent_checkpoint_blobs`, and `agent_checkpoint_writes`.

Stop chat traffic, back up the database, and run [`backend/app/db/migrate.py`](../backend/app/db/migrate.py) with **backend database owner** credentials before promoting a release:

```text
cd backend
python -m app.db.migrate
```

- **Idempotency & backfill**: Rerunning preserves existing allowances, reservations, approvals, and checkpoints. On PostgreSQL, `migrate.py` runs `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` via SQLAlchemy `DDL` (`rls_enable_statements`) across all 15 internal tables (`RLS_PROTECTED_MODELS`) with zero public browser policies. It imports the smallest non-negative remaining allowance from duplicate legacy `user_daily_limit` rows, backfills `daily_quotas.requests_used` from retained `user` messages (deleted historical messages cannot be recovered, so historical request counts are a lower bound), adds `agent_approvals.model_used` if missing, and seeds the canonical `free`, `super`, and `hyper` plans (`seed_default_plan`).
- **Maintenance window & rollback**: Keep traffic stopped across migration and promotion; mixing old and new accounting code can reset or lose usage. Legacy `user_daily_limit` remains intact for rollback, but on rollback you must stop traffic again and reconcile legacy counters against `daily_quotas` / `quota_reservations` before re-enabling the prior version.

## Accounting policy

Implementation lives in [`backend/app/services/chat.py`](../backend/app/services/chat.py) and [`backend/app/db/crud_token.py`](../backend/app/db/crud_token.py):

- **Canonical plans**: `free` (5,000 tokens / 50 requests per UTC day), `super` (50,000 tokens / 500 requests), and `hyper` (500,000 tokens / 5,000 requests), with legacy `pro` mapped to `super` quotas in [`backend/app/ai/llm.py`](../backend/app/ai/llm.py). Public plan mutation via `POST /auth/plan` is disabled (`403 Forbidden`) in [`backend/app/services/auth.py`](../backend/app/services/auth.py) pending verified billing.
- **UTC daily allowance & admission**: Each UTC day has one durable `DailyQuota` row per User, independent of Conversation deletion. Admission (`prompt_bound` + `TokenUsageCRUD.reserve`) reserves a conservative UTF-8 byte bound over system prompt, user personalization instructions, retrieved memories, conversation history, tool calls, and `max_output_tokens`. Oversized conversations fail with `402` before provider dispatch.
- **Request and burst slots**: Accepted attempts consume one daily request slot and one fixed-minute UTC burst slot (default `chat_burst_limit = 10` per minute), including provider failures and cancellations. Rejected admissions (`402` token exhaustion, `429` daily/burst limit with `Retry-After`, `409` duplicate `request_id`) do not consume slots.
- **Settlement & expiration**:
  - On success, observed `total_tokens` settles once and unused reserved tokens are returned. Missing provider usage retains the full reservation and sets `usage_estimated=true`.
  - Failure before any observable assistant output releases token capacity (`tokens_used=0`); failure or cancellation after partial output retains the reservation conservatively (`tokens_used=None`) and never persists partial prose as a complete reply.
  - An unexpected provider overrun records actual usage and `unfunded_tokens`, drains `tokens_remaining` to zero, and never clips reported usage.
  - Duplicate UUID `request_id` returns `409`. Pending reservations expire 120 seconds after creation (`expires_at = epoch + 120`); subsequent admission marks expired pending reservations `"expired"` without refunding unobserved completions. Reconcile expired records manually when auditing provider spend.
- **HITL approval resumption**: `ChatService.prepare_approval` reserves tokens against the checkpointed message bound (plus feedback/modified parameters) and preserves the original `model_used` from `AgentApproval`. On `interrupt()`, the turn settles usage incurred up to the pause and emits `done` with `status: "interrupted"`.
- **Defaults**: `max_output_tokens = 1024`, `generation_timeout_seconds = 60` (`ge=1, le=90`), `chat_burst_limit = 10`. Settings live in [`backend/.env.example`](../backend/.env.example) and [`backend/app/core/config.py`](../backend/app/core/config.py).

## Contracts

Keep backend Pydantic schemas, route payloads, and TypeScript client types synchronized across [`backend/app/schemas/auth.py`](../backend/app/schemas/auth.py), [`backend/app/schemas/chat.py`](../backend/app/schemas/chat.py), [`backend/app/schemas/memory.py`](../backend/app/schemas/memory.py), and [`frontend/src/types/index.ts`](../frontend/src/types/index.ts). Legacy `CraftMode` values (`standard`, `architect`, `code`, `brainstorm`, `agent`) and `/chat` endpoints are **v1 compatibility identifiers** retained alongside the Personal Agent platform evolution.

### HTTP and SSE contract table

| Surface | Endpoints & Source | Casing | Authoritative Fields & Notes |
| --- | --- | --- | --- |
| **Auth** | `POST /auth/register`, `POST /auth/login`, `GET /auth/me`, `POST /auth/plan` ([`auth.py`](../backend/app/api/routes/auth.py), [`auth.py` schemas](../backend/app/schemas/auth.py)) | camelCase (`LoginResponse`) / standard fields (`UserResponse`) | `LoginResponse`: `accessToken`, `tokenType`, `user` (`id`, `name`, `email`, `plan`). Google OAuth routes live at `/auth/google/login` and `/auth/google/callback` ([`google_oauth.py`](../backend/app/api/routes/google_oauth.py)). `POST /auth/plan` returns `403`. |
| **Quota & Models** | `GET /chat/quota`, `GET /chat/models` ([`chat.py` routes](../backend/app/api/routes/chat.py), [`chat.py` schemas](../backend/app/schemas/chat.py)) | camelCase | `QuotaResponse`: `requestsRemaining`, `tokensRemaining`, `totalRequests`, `totalTokens`. `ModelInfoResponse`: `id`, `name`, `description`, `requiredPlan`. Matches `Quota` and `Model` in [`frontend/src/types/index.ts`](../frontend/src/types/index.ts). |
| **Memory & Preferences** | `GET/PUT /memory/preferences`, `GET/POST/DELETE /memory`, `DELETE /memory/{memory_id}` ([`memory.py` routes](../backend/app/api/routes/memory.py), [`memory.py` schemas](../backend/app/schemas/memory.py)) | camelCase (`CamelModel`) | `UserPreferencesResponse`: `userId`, `customInstructionsProfile`, `customInstructionsStyle`, `memoryEnabled`, `updatedAt`. `UserMemoryResponse`: `id`, `userId`, `category` (`general`, `tech_stack`, `project`, `preference`), `content`, `isActive`, `sourceConversationId`, `createdAt`, `updatedAt`. `MemoryListResponse`: `memories`, `total`, `memoryEnabled`. Matches [`frontend/src/types/index.ts`](../frontend/src/types/index.ts) and [`memoryService.ts`](../frontend/src/services/memoryService.ts). |
| **Legacy Chat & History (JSON)** | `POST /chat`, `GET /chat/conversations`, `GET /chat/{conversation_id}/history`, `DELETE /chat/{conversation_id}` ([`chat.py` routes](../backend/app/api/routes/chat.py), [`chat.py` schemas](../backend/app/schemas/chat.py)) | snake_case | `ChatRequest`: `message`, `conversation_id`, `model`, `mode`, `request_id`. `ChatResponse`: `response`, `tokens_used`, `tokens_remaining`, `conversation_id`, `usage_estimated`, `model_used`, `mode_used`. `ConversationResponse`: `id`, `title`, `created_at`, `updated_at`. `MessageResponse`: `id`, `role`, `content`, `created_at`, `model_used`, `mode_used`. Matches `ConversationResponse` and `HistoryMessage` in [`frontend/src/types/index.ts`](../frontend/src/types/index.ts). |
| **Conversational SSE (`mode != "agent"`)** | `POST /chat/stream` ([`chat.py` service](../backend/app/services/chat.py), [`stream.ts`](../frontend/src/services/stream.ts)) | snake_case | Default `data:` JSON frames with `type`: `start` (`conversation_id`, `request_id`, `model_used`, `mode_used`), `chunk` (`content`), `done` (`conversation_id`, `tokens_used`, `tokens_remaining`, `model_used`, `mode_used`, `usage_estimated`), `error` (`status`, `error`, `conversation_id`). `start` provides Conversation identity before tokens; EOF without `done` is treated as interrupted. |
| **Agent Studio SSE (`mode == "agent"`)** | `POST /chat/stream`, `POST /chat/approval` ([`chat.py` service](../backend/app/services/chat.py), [`sseParser.ts`](../frontend/src/utils/sseParser.ts), [`frontend/src/types/index.ts`](../frontend/src/types/index.ts)) | camelCase (except `usage_estimated`) | Typed `event:` frames: `thought` (`thought`), `action_call` (`actionId`, `tool`, `args`, `tier`), `approval_required` (`actionId`, `tool`, `toolName`, `tier`, `parameters`, `rationale`, `diff`), `action_result` (`actionId`, `tool`, `output`), `token` (`token`), `error` (`status`, `error`, `conversationId`), and `done`. On `done`, `status` is `"interrupted"` (`actionId`, `totalSteps`, `conversationId`, `tokensUsed`, `tokensRemaining`, `modelUsed`, `modeUsed`) or `"completed"` (`totalSteps`, `conversationId`, `tokensUsed`, `tokensRemaining`, `modelUsed`, `modeUsed`, snake_case `usage_estimated`). EOF without `done` is treated as interrupted. |
| **HITL Approval REST** | `POST /chat/approval`, `GET /chat/{conversation_id}/approval` ([`chat.py` routes](../backend/app/api/routes/chat.py), [`chat.py` schemas](../backend/app/schemas/chat.py)) | camelCase | `ApprovalDecisionRequest`: `actionId`, `decision` (`approve`, `modify`, `reject`), `modifiedParams`, `feedback`. `ApprovalPendingResponse`: `actionId`, `conversationId`, `tool`, `toolName`, `tier`, `parameters`, `rationale`, `diff`, `status`. |

### Model catalog and legacy aliases

[`backend/app/ai/llm.py`](../backend/app/ai/llm.py) exposes actual Groq model IDs:
- `openai/gpt-oss-20b` (`free` and above)
- `openai/gpt-oss-120b` (`hyper`)

Legacy aliases `llama3-8b-8192`, `gemma-7b-it`, and `mixtral-8x7b-32768` resolve to `openai/gpt-oss-20b`; `llama3-70b-8192` resolves to `openai/gpt-oss-120b`. Responses always disclose the resolved model ID, and unknown IDs are rejected with HTTP `422`. Account permissions and live provider availability still require a credentialed smoke check.

## Verification and CI checks

### Full-stack verification

- **Windows**:
  ```powershell
  powershell -ExecutionPolicy Bypass -File scripts/verify.ps1
  ```
  Runs harness drift checks (`scripts/check-harness.ps1`), session-hook checks (`scripts/test-session-hook.ps1`), backend `pytest`, and frontend `npm run test:unit`, `npm run lint`, `npm test`, and `npm run build` ([`scripts/verify.ps1`](../scripts/verify.ps1)).
- **POSIX**:
  From `backend/`, run `.venv/bin/python -m pytest -q`. From `frontend/`, run `npm run lint`, `npm run test:unit`, `npm test`, and `npm run build`.
- **PostgreSQL test coverage**:
  Set `GPTCRAFT_TEST_DATABASE_URL` to a dedicated test PostgreSQL database containing `test` in its name. Tests recreate tables in that database; never point it at a production database.

### Harness and session-hook checks

Run both Antigravity (AGY) CLI harness checks from the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/check-harness.ps1
powershell -ExecutionPolicy Bypass -File scripts/test-session-hook.ps1
```

[`scripts/test-session-hook.ps1`](../scripts/test-session-hook.ps1) validates the `.agents/hooks.json` `SessionStart` command from both the repo root and nested `backend/` directory, confirms repository/branch JSON output, and verifies that bounded Mem0 diagnostics distinguish structured/CLI failures without auto-printing raw memory facts (use `.agents/scripts/mem0_helper.ps1` for deliberate project memory lookups).

### Browser contract checks

From `frontend/`, install Chromium and run Playwright E2E tests:

```powershell
cd frontend
npx playwright install chromium
npm run test:e2e
```

On Linux CI, pass `--with-deps chromium`. The Playwright suite starts its own Vite dev server and mocks auth/chat endpoints (`frontend/e2e/app.spec.ts`); it verifies UI/contract behavior and does not prove live Supabase or Groq integration.

### GitHub Actions checks

[`.github/workflows/verify.yml`](../.github/workflows/verify.yml) exposes five required check names:
- **Backend (sqlite)**
- **Backend (postgres)**
- **Frontend**
- **Browser contracts**
- **Windows hook**

Require these exact check names in repository branch protection after a successful PR run.

## Branching, staging, and promotion

Development follows a three-tier integration flow (`feature -> staging -> main`):

1. **Feature branches (`feat/...`, `fix/...`)**: Open PRs against `staging`, gated by the `Verify` GitHub Actions workflow.
2. **Staging soak**: Run full-stack checks (`scripts/verify.ps1`, `scripts/check-harness.ps1`, `scripts/test-session-hook.ps1`) and operator smoke checks on `staging`.
3. **Release PR (`staging -> main`)**: Open a release PR after staging soak passes.
4. **Maintenance-window promotion**: Stop traffic, back up the database, run `python -m app.db.migrate`, promote `staging` to `main`, deploy the new backend/frontend artifacts, and run post-deploy smoke checks.

Before promotion or immediately after deploy, confirm: schema migration succeeded, all hosted CI checks passed, `GET /health` returns healthy JSON, `GET /chat/models` returns the model catalog, unauthenticated `POST /chat` returns `401` rather than SPA HTML, real sign-in and real chat work, displayed model identity matches the resolved Groq ID, quota settlement updates accurately, and Stop/disconnect cancellation halts upstream generation through the deployed proxy.

## Appendix: Optional PaaS adapters

Self-hosted ASGI + PostgreSQL + static SPA is the primary deployment target. The repository also retains optional PaaS adapter configs; when using serverless or edge adapters, note that local host workspace tools and local `stdio` MCP subprocesses cannot safely persist or isolate across multi-tenant serverless invocations.

### Vercel

- **Root full-stack config ([`vercel.json`](../vercel.json), [`api/index.py`](../api/index.py))**: Builds `frontend/` into `public/` (`npm ci && npm run lint && npm run build -- --outDir ../public`), serves static SPA assets, and routes `/auth/(.*)`, `/chat`, `/chat/(.*)`, `/memory`, `/memory/(.*)`, `/health`, `/docs`, and `/openapi.json` to the Python ASGI entrypoint `api/index.py` (`maxDuration: 300`, `includeFiles: "backend/**"`). Root [`requirements.txt`](../requirements.txt) points Vercel's Python builder to `backend/requirements.lock`. Import with the **Other** framework preset (not the FastAPI preset) so SPA routing and API routes stay intact.
- **Static frontend config ([`frontend/vercel.json`](../frontend/vercel.json))**: Optional Vite SPA-only deployment configuration with SPA catch-all rewrites.
- **Held auto-deployments**: Both `vercel.json` and `frontend/vercel.json` set `"git": { "deploymentEnabled": false }` so pushes do not bypass the `staging -> main` promotion gate.

### Cloudflare Workers

- **`gpt-craft-backend`**: Optional Cloudflare Workers backend adapter. Manage build triggers in the Cloudflare dashboard so only approved `main` promotions deploy.
