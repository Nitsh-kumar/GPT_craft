# Project status

Updated: 13 November 2026

## Implemented Reliability & Core Platform (Merged from PR #28)

- Monorepo frontend/backend and full-stack Vercel routing (Vercel Git auto-deploy currently held via `git.deploymentEnabled: false` on `staging`).
- Email/password and Google sign-in integrations; live production identity/provider credentials require an operator smoke test.
- Persistent owned Conversations with deletion and model/mode metadata (`GenerationDetails`) for new responses.
- Incremental model-to-browser SSE; explicit terminal events and interrupted UI states.
- Explicit disconnect cancellation and a bounded generation deadline.
- Database-backed UTC token reservations, daily request admission, burst limits, duplicate request rejection, and idempotent settlement (`DailyQuota`, `QuotaReservation`).
- Public Plan changes disabled pending verified billing; existing trusted entitlements remain usable.
- Canonical GPT-OSS model identities with documented legacy aliases; no canned fallback in production flows.
- Offline regression tests, pinned Python dependency resolutions (`requirements.in`/`.lock`), explicit DB migration (`python -m app.db.migrate`), and PR verification workflows.
- Native in-database `UserPreferences` and `UserMemory` models with `/users/me/preferences` and `/users/me/memories` APIs and React 19 Personalization Modal.

## Shipped on Staging: Epic #11 — Stateful Autonomous Personal Agent Platform (PR #29)

Implemented on `staging` against `docs/specs/personal_agent_platform_spec.md`, `docs/adr/0002-personal-agent-execution-boundaries.md`, and `docs/adr/0003-hitl-interruption-and-approval-protocol.md`:

- [x] **Ticket 1 (#12)**: Agent Studio Mode Switcher & Typed SSE Protocol Envelope Foundation
- [x] **Ticket 2 (#13)**: Cyclical LangGraph ReAct Loop & Tier 1 Workspace Tools (`read_workspace_file`, `list_workspace_directory`, `search_workspace_symbols`, 4,000-char truncation)
- [x] **Ticket 3 (#14)**: Human-In-The-Loop (HITL) Interruption & Approval Cards (LangGraph `interrupt()`, DB checkpointing, `POST /chat/approval` resumption, interactive confirmation cards)
- [x] **Ticket 4 (#15)**: Command Execution Guardrails & Process Timeouts (`run_terminal_command`, path jailing, 30-second execution timeouts, non-interactive stdin rejection)
- [x] **Ticket 5 (#16)**: Model Context Protocol (MCP) Client Manager (stdio and sse client manager, dynamic tool translation to LangChain structured tools, wired into `agent.py` with offline mock server tests)
- [x] **Ticket 6 (#17)**: Action Telemetry Drawer, Diff Inspector & E2E Studio Polish (collapsible `TelemetryDrawer`, line-numbered syntax-highlighted diffs & terminal viewer in `ApprovalCard`, `telemetry.test.ts` + isolated Playwright `app.spec.ts` spec)

## Release prerequisites & Next Phase Plan

1. **Pre-`main` release hardening (from `staging` audit)**:
   - Run the explicit migration and smoke checks in [OPERATIONS.md](OPERATIONS.md).
   - Extend PostgreSQL RLS setup in `backend/app/db/migrate.py` to also enable RLS on `user_preferences`, `user_memories`, and `agent_approvals` (currently enabled on `daily_quotas`, `quota_reservations`, `generation_details`).
   - Confirm hosted Actions results, configure branch protection requiring **Backend (sqlite)**, **Backend (postgres)**, **Frontend**, **Browser contracts**, and **Windows hook** (`#25`), and verify the Antigravity session-start hook (`#24`).
   - Scope Cloudflare Workers (`gpt-craft-backend`) build triggers to `main` only in the Cloudflare dashboard, and re-enable/trigger Vercel deployment when promoting `staging` -> `main`.
2. **Next Phase Engineering Roadmap (Post-Epic #11)**:
   - **Durable Graph Checkpointing**: Replace in-memory `MemorySaver()` in `backend/app/ai/graph/agent.py` with PostgreSQL-backed LangGraph checkpointing so HITL approvals (`POST /chat/approval`) survive multi-worker restarts and serverless cold starts.
   - **Isolated Workspace Sandboxing**: Move `run_terminal_command` and file tools from host workspace confinement to per-session ephemeral containers/sandboxes before exposing Agent Studio to multi-tenant production users.
   - **Verified Billing & Plan Entitlements**: Implement Stripe/webhook billing verification before re-enabling paid plan upgrades (`super` / `hyper`); paid billing remains out of scope until verified.
   - **Live Provider & Staging Smoke Automation**: Add an optional credentialed smoke test script for Supabase Auth + live Groq/MCP servers before promoting `staging` to `main`.
