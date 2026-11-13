# Backend instructions

Use a virtual environment. First install with
`.venv/bin/python -m pip install --require-hashes -r requirements-dev.lock`
(or `.venv/Scripts/python.exe` on Windows). `requirements.in` is the runtime
source; `requirements.lock` and `requirements-dev.lock` are committed resolutions.

- Routes own HTTP transport and dependencies. Services own admission/generation policy. DB modules own transactions. The AI graph owns provider execution.
- Every conversation read/write verifies the current User's ownership; inactive Users receive 403.
- Call the shared reservation/settlement interface for both JSON and SSE. No transaction may span inference. Accepted requests retain their request slot on failure; token rules are in `docs/OPERATIONS.md`.
- New schemas or changes to response/events require matching TypeScript types, clients, and behavioral HTTP tests.
- Use UTC for quota dates and rate-limit windows.
- Test at HTTP/SSE, provider-factory, and quota reservation interfaces. Inject offline provider fakes; never use live credentials in automated tests.
- Run `python -m pytest -q`. PostgreSQL concurrency coverage requires a dedicated `GPTCRAFT_TEST_DATABASE_URL`; local tests default to a temporary SQLite database.
- Schema creation/import is explicit (`python -m app.db.migrate`), not an import/startup side effect. Follow the maintenance-window runbook before deployment.

## Agent Studio & Tool Execution Safety
- Refer to architectural guidelines in `docs/adr/0002-personal-agent-execution-boundaries.md` and `docs/adr/0003-hitl-interruption-and-approval-protocol.md`.
- **3-Tier Capability Model**:
  - *Tier 1 (Read-Only)*: Auto-executed without user interruption (`read_workspace_file`, `list_workspace_directory`, `search_workspace_symbols`). Truncate tool output to 4,000 characters to prevent context window saturation.
  - *Tier 2 (Workspace Mutation)*: Must suspend via LangGraph native `interrupt()` backed by DB state checkpointing and emit an `approval_required` SSE envelope. Resumed via `POST /chat/approval`.
  - *Tier 3 (Destructive / External)*: Requires explicit command and diff review before confirmation.
- **Execution Guardrails**: All workspace tools in `app/ai/tools/` must confine paths strictly inside the active workspace root (reject path traversal), enforce a 30-second execution timeout, and fail immediately on interactive `stdin` prompts.
- **Typed SSE Envelopes**: In `agent` craft mode, `POST /chat/stream` emits structured SSE envelopes (`thought`, `action_call`, `approval_required`, `action_result`, `token`, `done`).
