# GPTCraft Coding Standards

These standards define the architectural, security, and quality judgment calls enforced during code reviews using `mattpocock-skills` (`code-review` for Standards + Spec verification, and `domain-modeling` with [`GLOSSARY.md`](GLOSSARY.md) and `docs/adr/` for domain alignment). Automated linting and type-checking are enforced by CI and [`scripts/verify.ps1`](scripts/verify.ps1); this document covers conventions beyond mechanical checks.

---

## 1. Architectural Boundaries & Layering

### 1.1 Backend Separation of Concerns
- **Routes (`backend/app/api/routes/`)**: Transport layer only (HTTP parsing, dependency injection via `get_db` / `get_current_user`, status codes). **Never execute raw SQL queries, complex ORM transactions, or LLM graph invocations directly inside route functions.**
- **Services (`backend/app/services/`)**: Business logic, policy checks (quota reservation, active account check, personalization), and LangGraph orchestration.
- **Data Access (`backend/app/db/`)**: Database session management, SQLAlchemy models ([`models.py`](backend/app/db/models.py)), explicit schema/RLS migration ([`migrate.py`](backend/app/db/migrate.py)), and atomic CRUD helpers.
- **AI Engine (`backend/app/ai/`)**: State graphs, checkpointer ([`checkpointer.py`](backend/app/ai/graph/checkpointer.py)), prompts, workspace tools, MCP client manager, and provider factory ([`llm.py`](backend/app/ai/llm.py)).

### 1.2 Frontend Component Hierarchy
- **Pages (`frontend/src/pages/`)**: Thin route containers composing layouts, hooks, and section components (< 250 lines).
- **Custom Hooks (`frontend/src/hooks/`)**: Encapsulate non-trivial state, network subscriptions, abort handling, and event listeners.
- **Components (`frontend/src/components/`)**: Reusable UI primitives and isolated widgets (`ApprovalCard`, `TelemetryDrawer`, `PersonalizationModal`, etc.) that explicitly handle `loading`, `error`, and `empty` states.

---

## 2. Cross-Stack Contract Conventions

### 2.1 Casing, Contracts, and TypeScript Sync
- Follow the authoritative contract summary in [`docs/OPERATIONS.md`](docs/OPERATIONS.md) rather than duplicating endpoint or payload tables here.
- **Internal Python**: Models, internal methods, and database columns use `snake_case`. Pydantic aliases (`auth.py`, `chat.py`, `memory.py`) must match the documented external contract.
- **TypeScript Sync**: Whenever changing [`backend/app/schemas/auth.py`](backend/app/schemas/auth.py), [`backend/app/schemas/chat.py`](backend/app/schemas/chat.py), or [`backend/app/schemas/memory.py`](backend/app/schemas/memory.py), simultaneously update [`frontend/src/types/index.ts`](frontend/src/types/index.ts), client services, and HTTP/SSE tests.

### 2.2 Tier & Quota Hierarchy
- User plans follow the canonical hierarchy: `free` -> `super` -> `hyper` (legacy `pro` maps to paid equivalent; public Plan mutation remains disabled pending verified billing).
- Feature and model gates must return explicit upgrade/entitlement errors (`403` / `422`) rather than generic `500` failures.

---

## 3. Multi-Tenant Security, Isolation & Sandbox Boundaries

### 3.1 Strict Tenant Isolation & Ownership
- **Ownership Checks**: Every read, mutation, approval, memory operation, checkpoint access, or stream must verify `user_id == current_user.id`.
- **PostgreSQL RLS**: All internal backend tables have Row-Level Security enabled via [`backend/app/db/migrate.py`](backend/app/db/migrate.py) with no browser Data API policies; never leak cross-tenant data or train models on tenant data.
- **Active Account Check**: `AuthService.get_user_by_token` must verify `user.is_active` and raise `403 Forbidden` for disabled accounts.

### 3.2 Host-Tool & Stdio-MCP Sandbox Gating
- Host workspace tools ([`backend/app/ai/tools/workspace.py`](backend/app/ai/tools/workspace.py)) and host `stdio` MCP servers ([`backend/app/ai/mcp/manager.py`](backend/app/ai/mcp/manager.py)) are **dev / single-operator gated only** until per-user isolated sandboxes exist. Never expose unisolated host execution or host `stdio` process spawning to untrusted multi-tenant production traffic.

### 3.3 Secrets & Token Exposure
- LLM provider API keys (`GROQ_API_KEY`), JWT signing secrets (`SECRET_KEY`), and database/service-role credentials must **never** appear in frontend bundles, `VITE_*` variables, or client error payloads.
- All token reservation, settlement, and burst rate limiting execute server-side via [`backend/app/db/crud_token.py`](backend/app/db/crud_token.py).

---

## 4. UI Design System & Theme Compatibility

### 4.1 Semantic CSS Tokens
- Use the "Modern Studio / Precision Atelier" semantic tokens defined in [`frontend/src/index.css`](frontend/src/index.css) and documented in [`DESIGN.md`](DESIGN.md).
- **Never hardcode hex or raw Tailwind grays** for structural surfaces or primary text. Use semantic tokens (`--canvas`, `--surface`, `--raised`, `--sunken`, `--ink`, `--ink-2`, `--ink-3`, `--line`, `--line-strong`, `--accent`, `--warn`, `--danger`, `--ok`, and legacy `--ember` aliases) with accessible contrast in both light and dark modes.

---

## 5. Streaming, HITL & Tool Safety Hygiene

### 5.1 SSE Resilience & Schema Reference
- Real-time streaming endpoints use Server-Sent Events (`text/event-stream`) via [`CancellableStreamingResponse`](backend/app/api/streaming.py) and client `AbortController`. Generators must terminate cleanly without orphan background tasks on disconnect or stop requests.
- Canonical Agent Studio (`thought`, `action_call`, `approval_required`, `action_result`, `token`, `done`, `error`) and legacy v1 (`start`, `chunk`, `done`, `error`) SSE payload shapes are defined in [`docs/OPERATIONS.md`](docs/OPERATIONS.md), [`backend/app/schemas/chat.py`](backend/app/schemas/chat.py), [`backend/app/services/chat.py`](backend/app/services/chat.py), and [`frontend/src/types/index.ts`](frontend/src/types/index.ts).

### 5.2 Tool Guardrails & HITL Checkpointing
- **Output Truncation**: Truncate tool outputs to 4,000 characters (`MAX_TOOL_OUTPUT_CHARS`) before re-injecting into LLM context.
- **Path Confinement**: Confine all workspace file/command paths inside the workspace root (`resolve_workspace_path`) and reject traversal (`..`, external absolute paths).
- **Execution Timeout**: Enforce the 30-second tool command timeout (`DEFAULT_COMMAND_TIMEOUT_SECONDS`) and bounded generation deadline (`generation_timeout_seconds` in [`backend/app/core/config.py`](backend/app/core/config.py), default `60`, max `90`).
- **Non-Interactive Guardrail**: Reject interactive commands (`check_interactive_command`) and run subprocesses with `stdin=subprocess.DEVNULL`.
- **HITL Checkpointing**: Tier 2 (and future Tier 3) operations must suspend via LangGraph `interrupt()`, persist via `SQLAlchemyCheckpointSaver` ([`backend/app/ai/graph/checkpointer.py`](backend/app/ai/graph/checkpointer.py)) and `AgentApproval`, and resume solely through `POST /chat/approval`.

---

## 6. Testing & Deterministic Verification

### 6.1 Offline Testing & Fixtures
- Automated tests (`backend/tests/`) must **never** call live external LLM APIs; inject offline fakes via the provider factory ([`backend/app/ai/llm.py`](backend/app/ai/llm.py)) and use isolated temporary database fixtures leaving no `.db` artifacts behind.

### 6.2 Full-Stack Verification
- Run [`scripts/verify.ps1`](scripts/verify.ps1) on Windows (or backend `pytest` + frontend `lint`, `test:unit`, `test`, `build` on POSIX) before completing work.

---

## 7. Code Review Checklist

- [ ] **Architecture & Isolation**: Layering respected; every user-scoped query checks `user_id` ownership and relies on RLS-protected tables; host tools/`stdio` MCP remain dev/single-operator gated.
- [ ] **Contract & Type Sync**: Pydantic schemas, TypeScript types (`frontend/src/types/index.ts`), API clients, and HTTP/SSE tests updated together.
- [ ] **Agent Safety & HITL**: Tool guardrails (4,000-char truncation, path confinement, 30s timeout, non-interactive stdin) and `interrupt()` / `SQLAlchemyCheckpointSaver` resumption preserved.
- [ ] **Determinism**: Tests run offline with zero live credentials and pass `scripts/verify.ps1`.
- [ ] **Harness Sync**: Any PR changing routes, schemas, SSE payloads, tools, migrations, dependencies, or scripts updates the matching pointer doc (`docs/PROJECT_STATUS.md`, `docs/OPERATIONS.md`, or ADR status) in the same PR.
