# GPTCraft agent instructions

GPTCraft is a conversation application moving toward a personal agent. Keep the
FastAPI/LangGraph/SQLAlchemy backend and React/TypeScript/Vite frontend in this monorepo.

- Read `backend/AGENTS.md` or `frontend/AGENTS.md` before changing that stack.
- Run backend commands from `backend/`; frontend commands from `frontend/`.
- Keep provider keys and signing secrets on the backend. Commit environment examples, never credentials or local databases.
- Match existing public contracts: auth/quota JSON is camelCase; conversation/chat JSON and SSE metadata use snake_case. Update TypeScript clients and HTTP tests with schema changes.
- Plans are `free`, `super`, `hyper`; public Plan mutation is disabled pending verified billing.
- Use the documented provider factory for test fakes; production errors must remain errors.
- Before finishing, run `scripts/verify.ps1` on Windows, or backend pytest plus frontend lint, test, and build commands on POSIX. Record skipped integration checks explicitly.
- Before deploying this branch, follow the maintenance-window migration in `docs/OPERATIONS.md`.
- The session-start hook reports the status/count of a bounded Mem0 project lookup; memory text is loaded deliberately through the helper. Treat absent/failed retrieval as missing context. Use `.agents/scripts/mem0_helper.ps1` for deliberate project memory operations; committed ADRs remain the source of architectural decisions.

Read `docs/PROJECT_STATUS.md` for shipped versus planned work; `CODING_STANDARDS.md`
for review conventions; `DESIGN.md` for the current visual system. When changing
accounting, migration, cancellation, dependencies, or deployment, read
`docs/OPERATIONS.md`. Issues/specs use GitHub (`docs/agents/issue-tracker.md`),
triage labels use `docs/agents/triage-labels.md`, and terminology/decisions live in
`GLOSSARY.md` and `docs/adr/`.
