# Personal Agent Execution Boundaries & Safety Tiers

## Implementation Status / Amendment (2026-11-14)

Reconciliation against shipped v1 code and the multi-tenant Personal Agent SaaS target:

- **Host Workspace & `stdio` MCP Are Dev / Single-Operator Gated**: Decision #2 ("Execute tools directly on the host workspace directory") and host `stdio` MCP subprocesses (`backend/app/ai/mcp/manager.py`) are **dev / single-operator gated only**. As GPTCraft transitions into an operator-hosted multi-tenant Personal Agent SaaS, multi-tenant production deployments must NOT expose host workspace tools or host `stdio` MCP servers to end users until per-user isolated sandboxes are implemented.
- **Built-In Tool Scope (`backend/app/ai/tools/workspace.py`)**: Shipped built-in tools cover **Tier 1** (`read_workspace_file`, `list_workspace_directory`, `search_workspace_symbols`, truncated to 4,000 characters) and **Tier 2** (`edit_workspace_file`, `run_terminal_command`) only. **No built-in Tier 3 tools and no built-in web research tool exist yet** (external tools may be federated via MCP, where `backend/app/ai/mcp/adapter.py` defaults tools to Tier 2 and honors configured tiers `1`, `2`, or `3`).
- **Timeouts (`backend/app/core/config.py`, `backend/app/ai/tools/workspace.py`)**: `run_terminal_command` enforces a 30-second default subprocess timeout (`DEFAULT_COMMAND_TIMEOUT_SECONDS = 30`), `stdin=subprocess.DEVNULL`, and interactive command detection; overall graph streaming enforces `generation_timeout_seconds` (default `60`, max `90`).
- **SSE Envelopes (`backend/app/services/chat.py`, `frontend/src/types/index.ts`)**: `POST /chat/stream` (`mode == "agent"`) and `POST /chat/approval` emit `thought`, `action_call`, `approval_required` (emitting both `tool` and `toolName`, integer `tier`, `parameters`, `rationale`, `diff`), `action_result`, `token`, `done` (`status`, `totalSteps`, `conversationId`, `tokensUsed`, `tokensRemaining`, `modelUsed`, `modeUsed`, plus `actionId` when interrupted and snake_case `usage_estimated` when completed), and `error` (`status`, `error`, `conversationId`).
- **Runtime User Memory (`backend/app/services/memory.py`)**: Runtime user personalization and episodic facts use SQL + regex heuristics (`UserPreferences`, `UserMemory`) at `/memory/preferences`, `/memory`, and `/memory/{memory_id}`; Mem0 is reserved for the `.agents/` developer harness only.

---

## Context
GPTCraft is evolving from a passive conversational workbench into an autonomous Personal Agent capable of executing workspace actions and technical research. Without well-defined execution boundaries, personal agents suffer from context window saturation (Open Interpreter), non-deterministic loops (AutoGPT), or destructive command execution.

## Decision
1. **Scope**: Focus Day 1 on Developer Workspace Automation (file inspection/editing, test and lint execution via terminal, git inspection) and live technical web research.
2. **Runtime**: Execute tools directly on the host workspace directory, bounded by path restrictions (no container prerequisite for local developer workflows).
3. **Safety Tiers**:
   - **Tier 1 (Read-Only / Search)**: Auto-executed without user interruption (reading files, directory listing, web research).
   - **Tier 2 (Workspace Mutations)**: 1-click confirmation required (editing files, running build/tests, creating branches).
   - **Tier 3 (External / Destructive)**: Explicit command inspection and diff review required (deleting files, running package installs, external network mutations).
4. **Command Constraints**: Strictly non-interactive execution (fails immediately if stdin prompt is requested), 30-second default timeout, and strict working-directory confinement to the project root.
5. **Streaming Protocol**: Structured SSE envelopes (`thought`, `action_call`, `approval_required`, `action_result`, `token`, `done`).
6. **UI Mode**: Add a dedicated `Agent Studio` mode in the React 19 frontend with real-time action telemetry and approval cards.
