# Project status

Reviewed: 13 October 2026

## Current scope

Backend with real provider invocation and persisted conversations; separate frontend branch.

## Next milestones

1. Align authenticated identity types, plan names, model selection, and quota contracts.
2. Make quota reservation/deduction atomic and enforce request limits.
3. Require safe signing configuration and fix disabled-user/OAuth token handling.
4. Declare and lock direct dependencies; replace implicit initialization with controlled migrations.
5. Add ownership, quota-concurrency, and provider-failure tests.
6. Verify backend plus frontend from clean checkouts.

## Acceptance checks

Two users cannot read each other's history. Concurrent requests cannot overspend quota. Provider failure has a defined accounting outcome. Advertise streaming only after transport streaming exists and is tested. Do not claim named model availability or latency without measurements.

## Release evidence

Before calling this project complete, record the commit, environment, commands, results, and known limitations. Screenshots and saved outputs alone do not establish that the current revision runs.

This pass changes documentation only. It does not certify runtime behavior, security, deployment availability, or ownership of third-party data and assets.
