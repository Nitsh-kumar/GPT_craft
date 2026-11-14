# Human-In-The-Loop (HITL) Interruption & Approval Protocol

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
