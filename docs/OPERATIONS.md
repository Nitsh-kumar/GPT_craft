# Operations and verification

## Runtime and installation

Use Python 3.12 and Node 24. From `backend/`, create `.venv`, then install:

```text
python -m pip install --require-hashes -r requirements-dev.lock
```

Use the virtual-environment Python for all subsequent backend commands. Deployment
installs root `requirements.txt`, which points to the same runtime lock used by
`backend/requirements.txt`. Test tools are isolated in the development lock.
From `frontend/`, use `npm ci`.

To update dependencies, change `backend/requirements.in` (and the development
input if needed), regenerate both locks with `uv pip compile --python-version
3.12 --universal --generate-hashes` (development resolution constrained by the runtime lock),
then perform a clean hashed install and run verification. Never hand-edit hashes.

## Migration before deployment

This release adds `daily_quotas`, `quota_reservations`, and `generation_details`.
Application import no longer creates tables or seeds data. Stop chat traffic,
back up the database, and run with the **backend database owner** credentials:

```text
cd backend
python -m app.db.migrate
```

Run once before promoting the new application; rerunning preserves existing
allowances and reservations. The migration creates new tables, imports the
smallest non-negative remaining allowance from duplicate legacy daily rows, and
backfills request usage from retained user Messages. Deleted historical Messages
cannot be recovered; historical request counts are a lower bound. Legacy tables
remain available for rollback. The new quota and metadata tables have RLS enabled
on PostgreSQL, with no browser policies; the privileged backend owner accesses
them. They are not resources for direct frontend Data API access.

Keep traffic stopped across migration and promotion: mixing old and new
accounting code can reset or lose usage. On rollback, stop traffic again and
reconcile the legacy counters against new reservations before re-enabling the
old application. Do not blindly switch back to stale legacy counters.

## Accounting policy

- A UTC day has one durable allowance per User, regardless of Conversation deletion.
- Admission reserves a conservative UTF-8 prompt/history/system bound plus configured
  maximum completion tokens. Oversized conversations are rejected before dispatch.
- Accepted attempts consume one daily request slot and one fixed-minute burst slot,
  including provider failures and cancellations; rejected attempts do not.
- On success, observed provider usage settles once and unused reservation is returned.
  Missing usage retains the full reservation and sets `usage_estimated=true`.
- Failure before observable output releases token capacity. Partial output with unknown
  usage retains the reservation conservatively; it is never saved as a complete reply.
- An unexpected provider overrun records actual usage and unfunded excess, drains
  available token capacity to zero, and never silently clips reported usage.
- A duplicate UUID `request_id` returns 409 without another dispatch. Settlement is
  idempotent. A lost process leaves the reserved tokens charged; after 120 seconds
  subsequent admission marks the reservation expired. No refund is guessed for an
  unobserved provider completion. Review these records manually when reconciling costs.
- Defaults: 1024 maximum output tokens, 60-second generation deadline, 10 accepted
  requests per User per UTC minute. Settings are in `backend/.env.example`.

## Contracts

Existing auth/quota responses use camelCase. Conversational chat/history/conversation
fields and legacy SSE metadata retain snake_case (`type`: `start`, `chunk`,
`done`, or `error`, where `start` provides Conversation identity before output and
only `done` confirms successful completion). Agent Studio (`mode == "agent"`)
emits typed SSE `event:` envelopes (`thought`, `token`, `action_call`,
`approval_required`, `action_result`, `done`, `error`) using camelCase payloads
per [personal_agent_platform_spec.md](specs/personal_agent_platform_spec.md). EOF
without `done` is treated as interrupted.

The catalog exposes actual Groq model IDs: `openai/gpt-oss-20b` (free+) and
`openai/gpt-oss-120b` (hyper). Legacy llama3-8b-8192, gemma-7b-it, and
mixtral-8x7b-32768 requests resolve to GPT-OSS 20B; llama3-70b-8192 resolves to
GPT-OSS 120B. Responses always disclose the resolved ID. Unknown IDs are rejected.
Model listing was checked against https://console.groq.com/docs/models; account
permissions and live availability still require a credentialed smoke check.

## Checks

Windows: `powershell -ExecutionPolicy Bypass -File scripts/verify.ps1`.
POSIX: from backend run `.venv/bin/python -m pytest -q`; from frontend run
`npm run lint`, `npm run test:unit`, `npm test`, and `npm run build`. For PostgreSQL set
`GPTCRAFT_TEST_DATABASE_URL` to a dedicated database containing `test` in its name.
Tests recreate tables in that database. Never use a production connection.

Browser contract checks: from frontend run `npx playwright install chromium`,
then `npm run test:e2e`. The suite starts its own Vite server and mocks auth/chat;
it does not prove end-to-end Supabase or model-provider integration.

GitHub Actions exposes **Backend (sqlite)**, **Backend (postgres)**, **Frontend**,
**Browser contracts**, and **Windows hook**. Require these exact check names in
repository branch protection after a successful PR run. A committed workflow does
not itself enforce merges. This branch does not change repository protection.

The Windows hook check runs the configured command from root and nested directories
and validates its JSON. Finish runtime verification by starting a fresh Antigravity
session and confirming repository/branch context and a memory retrieval status.
Missing or timed-out memory must be explicit; only a count of facts naming GPTCraft is reported. Memory text is never automatically printed; retrieve selected project facts deliberately through the helper.

## Branching, staging, and deployment control

Development follows a three-tier integration flow (`feature -> staging -> main`) so
changes can be integrated and verified together before hitting production:

1. **Feature branches (`feat/...`, `fix/...`)** open PRs against **`staging`**,
   gated by the `Verify` GitHub Actions workflow.
2. **Held auto-deployments on push**: Vercel Git auto-deployments are disabled via
   `"git": { "deploymentEnabled": false }` in root `vercel.json` and
   `frontend/vercel.json`. Manage Cloudflare Workers (`gpt-craft-backend`) build
   triggers in the Cloudflare dashboard so only approved `main` promotions deploy.
3. **Staging soak & release PR (`staging -> main`)**: After running full-stack checks
   and operator smoke tests on `staging`, open a release PR from `staging` to `main`.
4. **Promotion**: Run the maintenance-window `python -m app.db.migrate` step first,
   promote `staging` -> `main`, trigger or re-enable production deployment, and run
   post-deploy smoke checks.

Before promotion: confirm schema migration, successful hosted checks, real sign-in,
a real chat, displayed model identity, quota settlement, and Stop behavior through
the deployed proxy. Upstream cancellation has been tested over local TCP; a hosted
proxy must forward disconnects for the same behavior.
