# Project Status

Updated: 12 November 2026

## Completed Milestones

1. **Unified Monorepo & Initial Harness**:
   - Merged backend and frontend into a unified `backend/` + `frontend/` monorepo structure while preserving Git history.
   - Cleaned root dumps, dependencies, and contract mismatches across FastAPI and React 19.
   - Implemented root and directory-scoped `AGENTS.md` rules, AGY skills (`gptcraft-verify`, `gptcraft-dev`), and unified verification script (`scripts/verify.ps1`).

2. **Real-Time SSE Token Streaming**:
   - Replaced simulated client-side word delay in `chatService.ts` with true server-driven Server-Sent Events (`text/event-stream`).
   - Integrated FastAPI `StreamingResponse` with LangGraph async streaming, supporting graceful client abortion (`AbortController`).

3. **Native Personalization & Long-Term Memory**:
   - Implemented native in-database `UserPreferences` and `UserMemory` SQLAlchemy models with support for both SQLite and PostgreSQL.
   - Built hybrid auto-extraction memory pipeline with explicit memory management endpoints (`/users/me/preferences`, `/users/me/memories`).
   - Integrated Mem0 long-term memory retrieval into agent context at session startup.
   - Added React 19 Memory Management Modal in the frontend sidebar for user inspection, editing, and deletion of stored preferences and memories.

4. **Epic #11 Ticket 1 (#12): Agent Studio Mode Switcher & Typed SSE Protocol Envelope Foundation**:
   - Added `agent` mode to craft switcher alongside `standard`, `architect`, `code`, and `brainstorm`.
   - Defined typed SSE event envelopes (`thought`, `action_call`, `approval_required`, `action_result`, `token`, `done`, `error`) for agent execution.
   - Implemented resilient client-side streaming parser (`frontend/src/utils/sseParser.ts`) with chunk buffering, CRLF handling, and legacy conversational fallback.
   - Added unit test suite (`frontend/src/utils/sseParser.test.ts`) integrated into `npm run test:unit` and `scripts/verify.ps1`.

5. **Epic #11 Ticket 2 (#13): Cyclical LangGraph ReAct Loop & Tier 1 Workspace Tools**:
   - Built safe, read-only Tier 1 workspace tools (`read_workspace_file`, `list_workspace_directory`, `search_workspace_symbols`) with root path jail enforcement and guaranteed `<= 4,000` character truncation.
   - Configured cyclical LangGraph ReAct loop (`chatbot -> tools -> chatbot -> END`) using `ToolNode` and `tools_condition`.
   - Emitted typed `action_call` and `action_result` SSE event envelopes with tier tags and parameters during agent tool invocation.
   - Added frontend action telemetry components in `MessageBubble.tsx` and updated state management in `useChat.ts`.
   - Expanded backend and frontend test suites verifying tool execution, path security, truncation, and SSE event streaming.

6. **Epic #11 Ticket 3 (#14): Human-In-The-Loop (HITL) Interruption & Approval Cards**:
   - Implemented Tier 2 tool `edit_workspace_file` with workspace root path jailing, unified diff calculation (`difflib.unified_diff`), and LangGraph `interrupt()`.
   - Added durable `AgentApproval` database model and CRUD methods (`create_or_update_approval`, `get_pending_approval`, `resolve_approval`).
   - Integrated in-memory graph checkpointing with `MemorySaver()` bound to `configurable.thread_id`.
   - Built SSE stream interruption handling emitting `approval_required` and `done` with status `"interrupted"`.
   - Created `POST /chat/approval` and `GET /chat/{conversation_id}/approval` resumption endpoints.
   - Built interactive Paper & Ink `ApprovalCard.tsx` in frontend with unified diff viewer, Approve, Modify, and Reject with Feedback flows.
   - Restored pending approval requests on page reload in `useChat.ts`.
   - Expanded backend test suite with 4 comprehensive HITL test scenarios and frontend unit tests for approval envelope parsing.

---

## Active Epic #11: Stateful Autonomous Personal Agent Platform

Tracking implementation against `docs/specs/personal_agent_platform_spec.md`, `docs/adr/0002-personal-agent-execution-boundaries.md`, and `docs/adr/0003-hitl-interruption-and-approval-protocol.md`.

- [x] **Ticket 1 (#12)**: Agent Studio Mode Switcher & Typed SSE Protocol Envelope Foundation
- [x] **Ticket 2 (#13)**: Cyclical LangGraph ReAct Loop & Tier 1 Workspace Tools (`read_workspace_file`, `list_workspace_directory`, `search_workspace_symbols`, 4,000-char truncation)
- [x] **Ticket 3 (#14)**: Human-In-The-Loop (HITL) Interruption & Approval Cards (LangGraph `interrupt()`, DB checkpointing, `POST /chat/approval` resumption, interactive confirmation cards)
- [ ] **Ticket 4 (#15)**: Command Execution Guardrails & Process Timeouts (path jailing, 30-second execution timeouts, non-interactive stdin rejection)
- [ ] **Ticket 5 (#16)**: Model Context Protocol (MCP) Client Manager (stdio and sse client manager, dynamic tool translation to LangChain structured tools)
- [ ] **Ticket 6 (#17)**: Action Telemetry Drawer, Diff Inspector & E2E Studio Polish (collapsible telemetry drawer, syntax-highlighted diffs, e2e test suite)

---

## Upcoming Production Milestones

1. **Database Migrations Baseline**: Formalize Alembic migrations across deployment environments.
2. **Atomic Quota Reservation & Rate Limiting**: Apply SlowAPI limiter decorators to `/chat` and use atomic SQL updates for token deduction.
