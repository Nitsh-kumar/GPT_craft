# GPTCraft agent instructions

GPTCraft is transitioning into an **operator-hosted multi-tenant Personal Agent SaaS** (isolated per-user execution, live action visibility, HITL approval before sensitive actions, persistent cross-session memory, integrations, and encrypted credential vault on freemium + paid tiers). Keep the FastAPI/LangGraph/SQLAlchemy backend and React/TypeScript/Vite frontend in this monorepo.

## Domain & Architecture Boundaries

- **SaaS Core**: Plans are `free`, `super`, `hyper` with durable quota accounting and authentication; public Plan mutation remains disabled pending verified billing.
- **v1 Compatibility Identifiers**: Legacy conversational `CraftMode` (`standard`, `architect`, `code`, `brainstorm`, `agent`) and `/chat` routes are v1 compatibility identifiers, not the target Personal Agent domain identity.
- **Deployment Model**: Primary deployment is **cloud-agnostic self-hosted** (FastAPI/Uvicorn ASGI + PostgreSQL with RLS + built Vite SPA). Vercel ([`vercel.json`](vercel.json), [`frontend/vercel.json`](frontend/vercel.json), [`api/index.py`](api/index.py)) and Cloudflare (`gpt-craft-backend`) configurations are optional PaaS adapters.
- **Multi-Tenant Safety Rules**:
  1. **Tenant isolation**: Enforce strict `user_id` ownership checks and PostgreSQL Row-Level Security (RLS) across all user data, memories, approvals, checkpoints, and integrations—never leak cross-tenant data or train models on tenant data.
  2. **Sandbox gating**: Host workspace tools ([`backend/app/ai/tools/workspace.py`](backend/app/ai/tools/workspace.py)) and host `stdio` MCP servers ([`backend/app/ai/mcp/manager.py`](backend/app/ai/mcp/manager.py)) are **dev / single-operator gated only** until per-user isolated sandboxes exist.

## Engineering Rules & Pointers

- Read [`backend/AGENTS.md`](backend/AGENTS.md) or [`frontend/AGENTS.md`](frontend/AGENTS.md) before changing that stack. Run backend commands from `backend/`; frontend commands from `frontend/`.
- Keep provider keys and signing secrets on the backend. Commit `.env.example` templates only, never credentials or local databases.
- Use [`docs/OPERATIONS.md`](docs/OPERATIONS.md) as the single source of truth for runtime setup, hashed dependency installs, migrations, accounting policy, verification checks, deployment control, and HTTP/SSE contracts (backed by [`backend/app/schemas/auth.py`](backend/app/schemas/auth.py), [`backend/app/schemas/chat.py`](backend/app/schemas/chat.py), [`backend/app/schemas/memory.py`](backend/app/schemas/memory.py), and [`frontend/src/types/index.ts`](frontend/src/types/index.ts)).
- Use the documented provider factory ([`backend/app/ai/llm.py`](backend/app/ai/llm.py)) for offline test fakes; production errors must remain errors.
- Standardize on **Antigravity (AGY) CLI** (`.agents/`, `pwsh`-friendly while remaining compatible with Windows CI) and **`mattpocock-skills`** (`code-review`, `codebase-design`, `diagnosing-bugs`, `domain-modeling`, `grilling`, `pr`, `prototype`, `research`, `tdd`, `wizard`, `writing-for-agents`) alongside repo skills in `.agents/skills/`.
- `SessionStart` ([`.agents/hooks.json`](.agents/hooks.json), [`.agents/scripts/session_start.ps1`](.agents/scripts/session_start.ps1)) runs fast and fails safe offline. Mem0 ([`.agents/scripts/mem0_helper.ps1`](.agents/scripts/mem0_helper.ps1)) is strictly manual developer harness memory—never application runtime memory ([`backend/app/services/memory.py`](backend/app/services/memory.py)) and never architecture ground truth. Committed ADRs in `docs/adr/` remain the source of architectural decisions.
- Before finishing, run [`scripts/verify.ps1`](scripts/verify.ps1) on Windows, or backend pytest plus frontend lint, unit/stream tests, and build commands on POSIX (see [`docs/OPERATIONS.md`](docs/OPERATIONS.md)). Record skipped integration checks explicitly.
- Before deploying, follow the maintenance-window migration in [`docs/OPERATIONS.md`](docs/OPERATIONS.md).

Read [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md) for shipped versus planned work; [`CODING_STANDARDS.md`](CODING_STANDARDS.md) for code-review conventions; [`DESIGN.md`](DESIGN.md) for the visual system; [`GLOSSARY.md`](GLOSSARY.md) and `docs/adr/` for domain vocabulary and decisions; [`docs/agents/issue-tracker.md`](docs/agents/issue-tracker.md) and [`docs/agents/triage-labels.md`](docs/agents/triage-labels.md) for GitHub issue and triage conventions.

## Work Rules
- Work on one feature at a time
- Only start the next feature after the current one passes end-to-end verification
- Don't "also refactor" feature B while implementing feature A
- **Harness Sync**: Any PR changing routes, schemas, SSE payloads, tools, migrations, dependencies, or scripts must update the matching pointer doc (`docs/PROJECT_STATUS.md`, `docs/OPERATIONS.md`, or ADR status) in the same PR.
