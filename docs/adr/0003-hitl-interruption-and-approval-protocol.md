# Human-In-The-Loop (HITL) Interruption & Approval Protocol

## Implementation Status / Amendment (2026-11-14)

Reconciliation against the shipped v1 implementation:

- **Checkpointer (`backend/app/ai/graph/checkpointer.py`)**: Replaced the planned `SqliteSaver` / `PostgresSaver` with the custom SQLAlchemy ORM `SQLAlchemyCheckpointSaver` backed by `agent_checkpoints`, `agent_checkpoint_blobs`, and `agent_checkpoint_writes` (supporting both SQLite and PostgreSQL, with PostgreSQL RLS enabled by `backend/app/db/migrate.py`). Pending approval metadata is persisted in `agent_approvals` (`AgentApproval`) and exposed for UI recovery via `GET /chat/{conversation_id}/approval`.
- **Actual `approval_required` & `done` Payloads (`backend/app/services/chat.py`, `backend/app/schemas/chat.py`)**:
  - `approval_required` emits `actionId`, `tool`, `toolName` (both keys emitted; `tool` matches `frontend/src/types/index.ts`), integer `tier` (e.g. `2`, not a `"Tier 2"` string `capabilityTier`), `parameters`, `rationale`, and `diff`.
  - When a turn interrupts for approval, `ChatService._run_graph_stream` settles token usage incurred so far and emits `event: done` with `status: "interrupted"`, `actionId`, `totalSteps`, `conversationId`, `tokensUsed`, `tokensRemaining`, `modelUsed`, and `modeUsed`. When a turn finishes without interruption, `event: done` emits `status: "completed"` along with `usage_estimated` (snake_case).
- **Generation Timeout (`backend/app/core/config.py`)**: Instead of a 10-minute streaming inactivity window, `generation_timeout_seconds` enforces a hard `60`-second default generation deadline (`ge=1, le=90`). Durable checkpoints (`agent_checkpoints` + `agent_approvals`) still preserve pending approval cards across browser refreshes and server restarts, restored via `GET /chat/{conversation_id}/approval`.
- **Resumption (`backend/app/api/routes/chat.py`)**: `POST /chat/approval` accepts `ApprovalDecisionRequest` (`actionId`, `decision`: `approve` | `modify` | `reject`, optional `modifiedParams`, optional `feedback`), verifies `user_id` ownership, rejects already-resolved approvals with `409`, reserves token quota against the checkpointed message bound, and streams resumed execution.

---

## Context
When an autonomous personal agent undertakes workspace mutations (Tier 2) or destructive operations (Tier 3), it must pause safely for user confirmation. Brittle agents often rely on client-side polling, loose websockets, or in-memory state that vanishes if a browser tab is closed or the server restarts.

## Decision
1. **Engine**: Use LangGraph's native `interrupt()` function inside tool execution nodes, paired with a database state checkpointer (`SqliteSaver` in development, `PostgresSaver` in production).
2. **Payload**: The `approval_required` SSE event envelope delivers:
   - `actionId`: Unique UUID string.
   - `toolName`: Targeted tool identifier.
   - `capabilityTier`: `Tier 2` or `Tier 3`.
   - `parameters`: Formatted arguments, file paths, diffs, or shell commands.
   - `rationale`: The agent's natural-language explanation of why the action is required.
3. **User Affordances**:
   - `Approve & Run`: Resumes execution as requested.
   - `Modify & Run`: Resumes execution with user-edited arguments or code diff.
   - `Reject with Feedback`: Injects a rejection `ToolMessage` with the user's feedback string so the agent can adapt its plan.
4. **Resumption API**:
   - `POST /chat/approval` endpoint handling `actionId`, `decision`, optional `modifiedParams`, and optional `feedback`.
5. **Durability & Inactivity**:
   - Pending approvals persist durably in the database checkpoint.
   - SSE streaming connections gracefully close after 10 minutes of inactivity; the frontend restores the pending approval card upon next load.
