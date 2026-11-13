---
name: keploy
description: >-
  Automate API test case and dependency mock generation using Keploy. Use when
  recording network interactions and database calls from live application traffic,
  replaying tests deterministically without live third-party dependencies,
  verifying API regression behavior, expanding test coverage across FastAPI, Go,
  Node.js, or Java backends, or configuring Keploy in CI/CD pipelines.
metadata:
  github-repo: https://github.com/keploy/keploy
  version: 1.0.0
---

# Keploy API Testing & Mock Generation

Keploy is an open-source, AI-powered API testing and data-mocking platform. It records real API calls along with outgoing dependencies (PostgreSQL, MongoDB, Redis, Elasticsearch, HTTP integrations, gRPC) and converts them into deterministic, zero-code test cases and mock files.

---

## When to Use

- **Generate Integration Tests**: Automatically capture real user or synthetic test traffic and turn it into permanent regression tests.
- **Dependency Mocking**: Safely test backend services without running live external databases, third-party payment gateways, or OAuth servers.
- **Regression & Contract Drift**: Verify that refactoring or updating dependencies has not introduced breaking changes or contract mismatches.
- **CI/CD Quality Gates**: Run recorded integration test suites deterministically in GitHub Actions or Docker without provisioning complex infrastructure.

## When Not to Use

- **Pure Unit Tests**: Use language-native unit testing (`pytest`, `jest`, `go test`) for pure in-memory functions and algorithmic logic.
- **Frontend UI Testing**: Use Playwright or Cypress for DOM assertions and visual regression.

---

## Installation & Setup

### 1. Linux & Windows (WSL2)
Keploy relies on eBPF to capture network traffic transparently without SDK modifications:
```bash
curl --silent -O -L https://keploy.io/install.sh && bash install.sh
```

### 2. Docker Container (Cross-Platform)
When running across Docker Compose or containerized setups:
```bash
docker run --privileged -p 16789:16789 \
  -v /sys/kernel/debug:/sys/kernel/debug:rw \
  -v /sys/fs/bpf:/sys/fs/bpf:rw \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v ${PWD}:${PWD} -w ${PWD} \
  ghcr.io/keploy/keploy:latest
```

---

## Core Workflows

### Workflow 1: Recording API Tests & Dependency Mocks

1. **Start the application with Keploy Record mode**:
   ```bash
   # For a Python FastAPI application:
   keploy record -c "uvicorn app.main:app --port 8000"
   
   # For a Node.js/TypeScript application:
   keploy record -c "npm start"
   
   # For a Go application:
   keploy record -c "./my-go-binary"
   ```

2. **Trigger API Traffic**:
   Send HTTP requests to your application via `curl`, Postman, automated tests, or frontend interactions:
   ```bash
   curl -X POST http://localhost:8000/api/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email": "user@example.com", "password": "securepassword"}'
   ```

3. **Stop Recording**:
   Press `Ctrl+C`. Keploy creates recorded assets in the repository:
   ```text
   keploy/
   ├── keploy.yml
   └── test-set-0/
       ├── tests/
       │   ├── test-1.yaml
       │   └── test-2.yaml
       └── mocks.yaml
   ```

### Workflow 2: Replaying Tests Deterministically

Replay the recorded tests against your application. Keploy intercepts outgoing dependency calls and serves recorded mocks without contacting real external services:

```bash
keploy test -c "uvicorn app.main:app --port 8000" --delay 10
```

- `--delay <seconds>`: Gives the application sufficient startup time before Keploy executes replay traffic.
- `--testsets <names>`: Replay specific test suites (e.g. `--testsets "test-set-0,test-set-auth"`).

### Workflow 3: Configuring Noise & Dynamic Fields

Dynamic attributes like UUIDs, timestamps, and JWTs cause false positives in strict equality comparisons. Configure `keploy.yml` to ignore noise:

```yaml
version: api.keploy.io/v1beta1
record:
  path: ""
  filters:
    - path: "/health"
    - path: "/metrics"
test:
  delay: 10
  ignoreOrdering: true
  globalNoise:
    body:
      - "token"
      - "accessToken"
      - "created_at"
      - "updated_at"
      - "session_id"
    header:
      - "Date"
      - "Set-Cookie"
```

---

## CI/CD Automation (GitHub Actions)

Embed Keploy regression tests in CI to guarantee zero unintended regressions before merging:

```yaml
name: Keploy Integration Tests

on:
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install Keploy
        run: curl --silent -O -L https://keploy.io/install.sh && sudo bash install.sh

      - name: Run Keploy Tests
        run: |
          sudo -E env PATH=$PATH keploy test -c "python -m uvicorn app.main:app --port 8000" --delay 10
```

---

## Troubleshooting & Best Practices

- **Permission Denied / eBPF Error**: Keploy uses Linux eBPF probes. On Linux/WSL2, prepend `sudo` or execute in a privileged container (`--privileged`).
- **Port Conflicts**: Ensure your test port (e.g., 8000) and Keploy internal proxy port (16789) are free.
- **Missing Mocks**: If a database query or external API call fails during replay, ensure it was executed during the record phase and that DNS/TLS traffic was routed through Keploy.
- **Repository Hygiene**: Do not commit runtime logs (`*_logs.txt`) or temporary artifacts. Always inspect `keploy/` YAML diffs in PR reviews.
