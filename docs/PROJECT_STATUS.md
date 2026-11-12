# Project status

Updated: 12 November 2026. This document describes the reliability branch; merge
and deployment are separate steps. Do not describe a closed issue or prototype
branch as shipped on main without checking its code.

## Implemented on this branch

- Monorepo frontend/backend and full-stack Vercel routing.
- Email/password and Google sign-in integrations; live production identity/provider
  credentials require an operator smoke test.
- Persistent owned Conversations with deletion and model/mode metadata for new responses.
- Incremental model-to-browser SSE; explicit terminal events and interrupted UI states.
- Explicit disconnect cancellation and a bounded generation deadline.
- Database-backed UTC token reservations, daily request admission, burst limits,
  duplicate request rejection, and idempotent settlement.
- Public Plan changes disabled; existing trusted entitlements remain usable.
- Canonical GPT-OSS model identities with documented legacy aliases; no canned fallback.
- Offline regression tests, pinned Python dependency resolutions, and PR verification workflows.

## Verification scope

Backend tests use fake providers and temporary SQLite or an isolated PostgreSQL
instance. Real TCP tests cover early chunks and disconnect cancellation. Frontend
stream tests cover fragmented input and early EOF. Browser contract tests use
mocked HTTP responses and never create production users. These do not establish
live provider availability, billing, hosted proxy cancellation, or real Supabase
sign-in. Record actual check results in the PR.

## Remaining product work

Agent Studio, autonomous tools, HITL approvals, MCP, and durable agent task
execution are tracked in #11–#17. Their prototype/implementation branches are
separate from current main. Choose a complete user workflow before expanding the
roadmap. Paid billing and webhook entitlement provisioning are not implemented.

## Release prerequisites

Run the explicit migration and smoke checks in [OPERATIONS.md](OPERATIONS.md).
Confirm hosted Actions results, require the named checks for merging, and verify
the hook in the installed Antigravity runtime. A valid hook script alone does
not prove that a particular agent version loads its configuration.
