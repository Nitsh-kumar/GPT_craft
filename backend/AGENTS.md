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
