# Project status

Updated: 14 November 2026

GPTCraft is transitioning from a conversational AI workbench into an **operator-hosted multi-tenant Personal Agent SaaS** (inspired by Hark Pro: isolated per-user execution, live action visibility, Human-in-the-Loop approval before sensitive actions, persistent cross-session memory, integrations, encrypted credential vault, and `free` / `super` / `hyper` SaaS tiers). Legacy `CraftMode` names (`standard`, `architect`, `code`, `brainstorm`, `agent`) and `/chat` endpoints remain v1 compatibility identifiers. Primary deployment targets **cloud-agnostic self-hosted ASGI + PostgreSQL (with RLS) + built Vite SPA**, with optional Vercel and Cloudflare PaaS adapters documented in [OPERATIONS.md](OPERATIONS.md#appendix-optional-paas-adapters).

---

## Shipped (v1)

### Core Platform & Reliability (PR #28)

- Monorepo backend (`backend/`, FastAPI + LangGraph + SQLAlchemy) and frontend (`frontend/`, React 19 + TypeScript + Vite 6 + Tailwind CSS v4), plus optional Vercel (`vercel.json`, `frontend/vercel.json`, `api/index.py`) and Cloudflare (`gpt-craft-backend`) deployment adapters.
- Email/password authentication and Google OAuth / Supabase JWT verification (`backend/app/core/security.py`, `backend/app/api/routes/auth.py`, `backend/app/api/routes/google_oauth.py`); live production provider credentials require an operator smoke test.
- Persistent owned Conversations with deletion and `GenerationDetails` (`model_used`, `mode_used`) persisted per assistant message.
- Incremental model-to-browser SSE streaming, explicit terminal events, and interrupted UI states (`backend/app/api/streaming.py`, `frontend/src/services/stream.ts`).
- Explicit disconnect cancellation (`CancellableStreamingResponse` + `AbortController`) and bounded generation timeout (`generation_timeout_seconds`, default `60`, max `90` in `backend/app/core/config.py`).
- Database-backed UTC token reservations, daily request admission, fixed-minute burst limits, `409` duplicate `request_id` rejection, and idempotent settlement (`DailyQuota`, `QuotaReservation` in `backend/app/db/crud_token.py`).
- Canonical `free`, `super`, and `hyper` plan hierarchy (`docs/adr/0001-canonical-plan-hierarchy.md`); public plan upgrades (`POST /auth/plan`) disabled (`403`) pending verified billing.
- Canonical Groq model IDs (`openai/gpt-oss-20b`, `openai/gpt-oss-120b`) with documented legacy aliases (`backend/app/ai/llm.py`); no canned fallback text in production flows.
- Offline test suite, SHA-256 hashed Python lockfiles (`backend/requirements.lock` and dev lockfile), explicit pre-deploy migration (`python -m app.db.migrate`), and GitHub Actions verification workflow (`.github/workflows/verify.yml`).
- SQL + regex heuristic user personalization and memory (`UserPreferences`, `UserMemory` in `backend/app/services/memory.py`) with `/memory/preferences`, `/memory`, and `/memory/{memory_id}` endpoints (`backend/app/api/routes/memory.py`) and React 19 `PersonalizationModal`. (Mem0 is used **only** for the `.agents/` developer harness, not runtime user memory.)

### Agent Studio Workbench & Durable Execution (Epic #11 / PR #29)

Implemented on `staging` against [`docs/specs/personal_agent_platform_spec.md`](specs/personal_agent_platform_spec.md), [`docs/adr/0002-personal-agent-execution-boundaries.md`](adr/0002-personal-agent-execution-boundaries.md), and [`docs/adr/0003-hitl-interruption-and-approval-protocol.md`](adr/0003-hitl-interruption-and-approval-protocol.md), as reconciled by their Implementation Status / Amendment notes:

- **Ticket 1 (#12)**: Agent Studio mode switcher (`mode == "agent"`) and typed SSE envelope transport (`thought`, `action_call`, `approval_required`, `action_result`, `token`, `done`, `error`).
- **Ticket 2 (#13)**: Cyclical LangGraph ReAct loop (`backend/app/ai/graph/agent.py`) and Tier 1 read-only workspace tools (`read_workspace_file`, `list_workspace_directory`, `search_workspace_symbols`, 4,000-character output truncation in `backend/app/ai/tools/workspace.py`).
- **Ticket 3 (#14)**: Human-In-The-Loop (HITL) interruption and Approval Cards — LangGraph `interrupt()`, Tier 2 `edit_workspace_file`, `POST /chat/approval` resumption (`approve`, `modify`, `reject`), `GET /chat/{conversation_id}/approval` recovery, and `AgentApproval` (`agent_approvals`) persistence.
- **Ticket 4 (#15)**: Tier 2 terminal execution guardrails (`run_terminal_command` in `backend/app/ai/tools/workspace.py`) with path jailing to workspace root, 30-second default timeout, and non-interactive `stdin` rejection.
- **Ticket 5 (#16)**: MCP client manager (`backend/app/ai/mcp/manager.py`, `backend/app/ai/mcp/adapter.py`) supporting `stdio` and `sse` transports, dynamic JSON Schema-to-`StructuredTool` translation (defaulting to Tier 2 HITL gating), and offline mock server tests (`backend/tests/test_mcp.py`).
- **Ticket 6 (#17)**: Action telemetry drawer (`TelemetryDrawer`), line-numbered diff and command inspection in `ApprovalCard`, frontend parser/reducer/telemetry unit tests, and Playwright browser contract tests (`frontend/e2e/app.spec.ts`).
- **Pre-`main` Database Hardening**:
  - Custom SQLAlchemy ORM `SQLAlchemyCheckpointSaver` (`agent_checkpoints`, `agent_checkpoint_blobs`, `agent_checkpoint_writes` in `backend/app/ai/graph/checkpointer.py`) replacing in-memory `MemorySaver()`.
  - PostgreSQL Row-Level Security (RLS) enabled across all 15 internal tables via `backend/app/db/migrate.py` (`rls_enable_statements`).

---

## Known v1 Boundaries & Multi-Tenant Gates

- **Host Workspace Tools & `stdio` MCP Are Dev / Single-Operator Gated Only**: `backend/app/ai/tools/workspace.py` operates directly against the host repository root, and `StdioMCPClient` in `backend/app/ai/mcp/manager.py` spawns host subprocesses. Do **not** enable host workspace tools or host `stdio` MCP servers for untrusted multi-tenant production users until per-user isolated sandboxes exist.
- **Built-In Tool Scope**: Only Tier 1 and Tier 2 workspace tools exist in `backend/app/ai/tools/workspace.py` today. No built-in Tier 3 tools and no built-in web research tool exist yet (external tools can be wired through MCP).
- **Runtime Memory Implementation**: User memory uses SQL storage + regex keyword/overlap heuristics (`backend/app/services/memory.py`), not vector/semantic Mem0 retrieval.
- **Public Plan Mutation Disabled**: `POST /auth/plan` returns `403` pending verified billing integration.

---

## Release Gates Before `main` Promotion

- Run the maintenance-window migration (`python -m app.db.migrate`) and operator smoke checks documented in [OPERATIONS.md](OPERATIONS.md).
- Confirm hosted GitHub Actions pass and configure branch protection requiring **Backend (sqlite)**, **Backend (postgres)**, **Frontend**, **Browser contracts**, and **Windows hook** (`#25`).
- Validate Antigravity (AGY) CLI harness and `SessionStart` hook behavior (`scripts/check-harness.ps1`, `scripts/test-session-hook.ps1`, `#24`).
- Keep optional PaaS auto-deployments held on `staging` (`"git": { "deploymentEnabled": false }` in `vercel.json` and `frontend/vercel.json`, and `main`-only triggers for Cloudflare Workers `gpt-craft-backend`).

---

## Target Roadmap (Hark-Pro Personal Agent SaaS)

The capabilities below define the target multi-tenant Personal Agent SaaS roadmap and are **not yet shipped**:

1. **Per-User Isolated Execution Sandboxes**: Replace host workspace execution (`backend/app/ai/tools/workspace.py`) and host `stdio` MCP subprocesses with ephemeral, per-user/per-session isolated containers or microVM sandboxes so multi-tenant users can safely execute code, files, and tools with strict tenant isolation.
2. **Tier 3 Safety Controls & Built-In Research Tools**: Add explicit Tier 3 (destructive/external action) tooling and built-in web research tools with per-action confirmation policies.
3. **Encrypted Credential Vault & Third-Party Integrations**: Add per-user encrypted secrets storage and scoped OAuth/API integrations (calendar, email, issue trackers, cloud storage, external remote MCP connectors) with strict `user_id` + RLS tenant isolation.
4. **Semantic Cross-Session User Memory**: Upgrade runtime `UserMemory` retrieval/extraction beyond SQL + regex heuristics while preserving strict per-user isolation and zero cross-user leakage or model training.
5. **Verified Billing & Plan Entitlements**: Integrate verified billing webhooks (e.g., Stripe) to safely re-enable `free` -> `super` / `hyper` upgrades and enforce tier entitlements.
6. **Live Provider & Staging Smoke Automation**: Add optional credentialed smoke tests for real auth, Groq inference, and remote MCP endpoints prior to release promotion.
