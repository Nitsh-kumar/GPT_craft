# Backend instructions

Use a Python 3.12 virtual environment in `backend/`. Install dev and test tools with hashes:
`.venv/bin/python -m pip install --require-hashes -r requirements-dev.lock`
(or `.\.venv\Scripts\python.exe -m pip install --require-hashes -r requirements-dev.lock` on Windows).
`requirements.in` is the canonical runtime source; `requirements.lock` (referenced by `requirements.txt`) and `requirements-dev.lock` are committed hashed resolutions. Runtime-only installs use `python -m pip install --require-hashes -r requirements.lock`.

## Architecture & Contracts

- Routes (`app/api/routes/`) own HTTP transport and dependencies. Services (`app/services/`) own admission, policy, and orchestration. DB modules (`app/db/`) own transactions. The AI engine (`app/ai/`) owns LangGraph graphs, tools, MCP adapters, and provider factory (`app/ai/llm.py`).
- Call the shared reservation/settlement interface (`TokenUsageCRUD` / `ChatService`) for both JSON and SSE. No transaction may span inference; use UTC for quota dates and rate-limit windows.
- Authoritative HTTP/SSE contracts and accounting rules live in [`docs/OPERATIONS.md`](../docs/OPERATIONS.md) and the Pydantic schemas ([`app/schemas/auth.py`](app/schemas/auth.py), [`app/schemas/chat.py`](app/schemas/chat.py), [`app/schemas/memory.py`](app/schemas/memory.py)). Any schema or event change requires matching updates in [`frontend/src/types/index.ts`](../frontend/src/types/index.ts), clients, and HTTP/SSE tests.

## Multi-Tenant Safety & Memory Boundaries

- **Tenant Isolation**: Every read/write across conversations, messages, approvals, memories (`UserPreferences`, `UserMemory`), and LangGraph checkpoints must verify `user_id` ownership; inactive users receive `403`. PostgreSQL Row-Level Security (RLS) is enabled in [`app/db/migrate.py`](app/db/migrate.py) across all internal tables with no browser Data API policies; never leak cross-tenant data or train models on tenant data.
- **Runtime Memory vs. Harness Memory**: Application memory ([`app/services/memory.py`](app/services/memory.py) and [`app/api/routes/memory.py`](app/api/routes/memory.py) at `/memory/preferences`, `/memory`, `/memory/{memory_id}`) uses SQL + deterministic regex heuristics. Mem0 belongs strictly to the `.agents/` developer harness.

## Agent Studio, Sandbox Gating & HITL Checkpointing

- **Sandbox Gating**: Host workspace tools ([`app/ai/tools/workspace.py`](app/ai/tools/workspace.py)) and host `stdio` MCP servers ([`app/ai/mcp/manager.py`](app/ai/mcp/manager.py)) are **dev / single-operator gated only** until per-user isolated sandboxes exist.
- **Implemented Tools & Guardrails**: `app/ai/tools/workspace.py` implements Tier 1 read-only tools (`read_workspace_file`, `list_workspace_directory`, `search_workspace_symbols`, output truncated to 4,000 characters) and Tier 2 HITL tools (`edit_workspace_file`, `run_terminal_command`, workspace-root confined, 30-second execution timeout, interactive `stdin` rejected). Built-in Tier 3 tools and built-in web research tools do not exist yet.
- **HITL & Durable Checkpoints**: Tier 2 mutations suspend via LangGraph `interrupt()`, persist via custom ORM `SQLAlchemyCheckpointSaver` ([`app/ai/graph/checkpointer.py`](app/ai/graph/checkpointer.py) tables `agent_checkpoints`, `agent_checkpoint_blobs`, `agent_checkpoint_writes`) and `AgentApproval`, and resume only via `POST /chat/approval`. `generation_timeout_seconds` ([`app/core/config.py`](app/core/config.py)) defaults to `60` (`le=90`).
- Reference [`docs/adr/0002-personal-agent-execution-boundaries.md`](../docs/adr/0002-personal-agent-execution-boundaries.md) and [`docs/adr/0003-hitl-interruption-and-approval-protocol.md`](../docs/adr/0003-hitl-interruption-and-approval-protocol.md).

## Testing & Migrations

- Inject offline provider fakes via [`app/ai/llm.py`](app/ai/llm.py); never use live credentials in automated tests.
- Run `python -m pytest -q` (defaults to a temporary SQLite database; set `GPTCRAFT_TEST_DATABASE_URL` for PostgreSQL concurrency coverage).
- Schema creation/import is explicit (`python -m app.db.migrate`), never an import/startup side effect. Follow the maintenance-window runbook in [`docs/OPERATIONS.md`](../docs/OPERATIONS.md) before deployment.
