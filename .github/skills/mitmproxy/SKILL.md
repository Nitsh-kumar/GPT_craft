---
name: mitmproxy
description: >-
  Inspect, intercept, modify, and replay HTTP/1, HTTP/2, HTTP/3, and WebSocket traffic
  using mitmproxy. Use when testing API security, analyzing client-server communications,
  debugging REST/GraphQL/WebSocket endpoints, crafting automated traffic manipulation
  scripts with Python addons (mitmdump), auditing for OWASP API vulnerabilities,
  or exporting traffic in HAR/flow formats.
metadata:
  github-repo: https://github.com/mitmproxy/mitmproxy
  version: 1.0.0
---

# mitmproxy Interactive HTTPS Intercepting Proxy

mitmproxy is an open-source, interactive, SSL/TLS-capable intercepting HTTP proxy for penetration testing, security auditing, and developer debugging. It supports HTTP/1, HTTP/2, HTTP/3, and WebSockets across three complementary interfaces.

---

## Tool Overview & Interfaces

1. **`mitmproxy`**: Interactive TUI (terminal user interface) with vim-like navigation for live inspection and filtering.
2. **`mitmweb`**: Browser-based web GUI (default: `http://127.0.0.1:8081`) for graphical packet analysis and flow inspection.
3. **`mitmdump`**: Headless CLI tool ideal for CI/CD, batch processing, automated capture, and custom Python script addons.

---

## Installation & Certificate Setup

### 1. Installation

```bash
# Via Python pip / pipx:
pip install mitmproxy

# Via Windows Package Manager (winget):
winget install mitmproxy.mitmproxy

# Via Homebrew (macOS):
brew install mitmproxy
```

### 2. TLS / SSL Certificate Installation

When mitmproxy starts for the first time, it generates CA certificates in `~/.mitmproxy/`:
- `mitmproxy-ca-cert.pem`: Root certificate in PEM format.
- `mitmproxy-ca-cert.cer`: Windows/Android-compatible certificate.
- `mitmproxy-ca.p12`: PKCS12 format for iOS.

**To trust certificates on test clients**:
1. Route client traffic through mitmproxy (default: `http://127.0.0.1:8080`).
2. Visit `http://mitm.it` in the client browser to download and install the CA certificate into your OS trust store.
3. For CLI/Python tools:
   ```bash
   export REQUESTS_CA_BUNDLE=~/.mitmproxy/mitmproxy-ca-cert.pem
   export NODE_EXTRA_CA_CERTS=~/.mitmproxy/mitmproxy-ca-cert.pem
   export CURL_CA_BUNDLE=~/.mitmproxy/mitmproxy-ca-cert.pem
   ```

---

## Core Workflows

### Workflow 1: Reverse Proxy for Local API Debugging

Run mitmweb in front of a local backend server (e.g. FastAPI on port 8000) to inspect all frontend-backend exchanges:

```bash
# Listen on port 8088 and reverse proxy to 127.0.0.1:8000; web UI on 8081
mitmweb --mode reverse:http://127.0.0.1:8000 --listen-port 8088 --web-port 8081
```

Configure your frontend API client to target `http://localhost:8088`. All requests and responses will be visible in the web UI.

### Workflow 2: Automated Headless Capture & HAR Export

Capture API flows silently during automated test suites:

```bash
# Capture traffic to flow file
mitmdump -w traffic.flow --listen-port 8080

# Convert captured flows to HAR format for audits or sharing
mitmdump -r traffic.flow --set hardump=audit-traffic.har
```

### Workflow 3: Custom Python Scripting & Addons

mitmproxy features a Python event-driven addon architecture for request/response tampering, security fuzzing, and telemetry.

Save as `security_addon.py`:
```python
from mitmproxy import http

class SecurityTester:
    def request(self, flow: http.HTTPFlow) -> None:
        # 1. Inspect or modify headers
        if "api" in flow.request.pretty_url:
            print(f"[>] Outgoing API Call: {flow.request.method} {flow.request.path}")
            # Example: Fuzz authorization header
            # flow.request.headers["X-Test-Trace"] = "fuzz-agent-01"

    def response(self, flow: http.HTTPFlow) -> None:
        # 2. Check for security headers or leaked data
        if flow.response:
            status = flow.response.status_code
            if status >= 400:
                print(f"[!] API Error {status} on {flow.request.path}")
            
            # Audit missing security headers
            if "Strict-Transport-Security" not in flow.response.headers:
                flow.response.headers["X-Audit-Warning"] = "Missing HSTS header"

addons = [SecurityTester()]
```

Run with:
```bash
mitmdump -s security_addon.py -p 8080
```

---

## OWASP API Security Testing Cheatsheet

Use mitmproxy filters and addons to test for common vulnerabilities:

| Vulnerability | Testing Strategy | mitmproxy Technique |
| :--- | :--- | :--- |
| **BOLA / IDOR** | Manipulate resource IDs in endpoints (`/users/10` -> `/users/11`) | Modify request path via TUI (`e` to edit) or script `flow.request.path` |
| **Broken Auth** | Tamper with or strip JWT / Bearer tokens | Use `--modify-headers '/~u api/Authorization/Bearer fake-token'` |
| **Mass Assignment** | Inject privileged parameters into POST/PUT JSON bodies | Intercept request body and append `{"tier": "hyper", "isAdmin": true}` |
| **Data Leakage** | Detect PII, secrets, or internal stack traces in responses | Use view filter `~bs "password" | ~bs "traceback"` |

---

## Filtering Expressions Cheatsheet

In `mitmproxy` or `mitmweb`, use filter syntax:
- `~m POST & ~u /api/v1/`: Only POST requests to `/api/v1/`
- `~c 500`: Server error responses
- `~h "Authorization"`: Requests containing the Authorization header
- `~d example.com`: Restrict to domain `example.com`

---

## Troubleshooting

- **Client rejects SSL/TLS**: Confirm `mitmproxy-ca-cert.pem` is installed in the client's trusted root authority store.
- **Port already in use**: Specify alternative ports via `--listen-port <port>` and `--web-port <port>`.
- **HTTP/3 / QUIC traffic**: Enable experimental HTTP/3 support using `--set http3=true`.
