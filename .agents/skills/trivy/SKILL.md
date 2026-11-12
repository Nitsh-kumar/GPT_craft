---
name: trivy
description: >-
  Comprehensive security scanner for vulnerabilities (CVEs), secrets, misconfigurations,
  licenses, and SBOM generation using Aqua Security Trivy. Use when scanning container
  images, local filesystems, git repositories, and Infrastructure-as-Code (IaC) files
  (Dockerfiles, Kubernetes, Terraform), generating CycloneDX or SPDX SBOMs, or configuring
  security quality gates in CI/CD workflows.
metadata:
  github-repo: https://github.com/aquasecurity/trivy
  version: 1.0.0
---

# Trivy Security Scanner

Trivy by Aqua Security is a comprehensive, fast, and multi-target security scanner. It discovers vulnerabilities (CVEs) in OS packages and language dependencies (Python, Node.js, Go, Java, Rust), detects hardcoded secrets, audits Infrastructure-as-Code (IaC) misconfigurations, and generates Software Bills of Materials (SBOMs).

---

## When to Use

- **Dependency Security (SCA)**: Scan project lockfiles (`requirements.txt`, `package-lock.json`, `uv.lock`, `pnpm-lock.yaml`) for known CVEs.
- **Container Hygiene**: Audit Docker base images and layers before publishing or deploying.
- **IaC & Config Auditing**: Scan Dockerfiles, Kubernetes manifests, Terraform, and GitHub Actions workflows for security misconfigurations.
- **Secret Scanning**: Prevent accidental leakage of API keys, private certificates, and credentials.
- **SBOM Generation**: Produce CycloneDX or SPDX compliance manifests for software supply chain compliance.

---

## Installation

```bash
# Windows (via winget):
winget install AquaSecurity.Trivy

# macOS (via Homebrew):
brew install trivy

# Linux (Debian / Ubuntu):
sudo apt-get install wget apt-transport-https gnupg lsb-release
wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | sudo apt-key add -
echo deb https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main | sudo tee -a /etc/apt/sources.list.d/trivy.list
sudo apt-get update && sudo apt-get install trivy

# Docker (zero install):
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v ${PWD}:/src aquasec/trivy:latest fs /src
```

---

## Core Workflows

### Workflow 1: Repository & Dependency Vulnerability Scan

Scan current workspace filesystem for CVEs, secrets, and misconfigurations:

```bash
# Full security audit of local filesystem
trivy fs --scanners vuln,secret,misconfig .

# Filter for High and Critical vulnerabilities only
trivy fs --severity HIGH,CRITICAL .

# Fail CI pipeline if High or Critical vulnerabilities are found
trivy fs --exit-code 1 --severity HIGH,CRITICAL .
```

### Workflow 2: Container Image Security Scan

Scan container images locally or from remote registries:

```bash
# Scan local Docker image
trivy image --severity HIGH,CRITICAL my-app:latest

# Ignore unpatched vulnerabilities (focus on actionable fixes)
trivy image --ignore-unfixed my-app:latest
```

### Workflow 3: Secret Detection & IaC Auditing

Audit Dockerfiles and configuration files for common security lapses (running as root, exposed secrets, unpinned versions):

```bash
# Audit IaC and Dockerfiles
trivy config .

# Scan exclusively for hardcoded secrets / API keys
trivy fs --scanners secret .
```

### Workflow 4: Software Bill of Materials (SBOM) Generation

Generate SBOM reports for compliance and vulnerability tracking:

```bash
# CycloneDX JSON format
trivy fs --format cyclonedx --output sbom-cyclonedx.json .

# SPDX JSON format
trivy fs --format spdx-json --output sbom-spdx.json .
```

---

## Configuration (`trivy.yaml` and `.trivyignore`)

### 1. Project Configuration (`trivy.yaml`)

```yaml
vulnerability:
  type:
    - os
    - library
  severity:
    - CRITICAL
    - HIGH
ignore-unfixed: false
skip-dirs:
  - "node_modules"
  - ".venv"
  - "dist"
  - "tests"
output:
  format: table
  severity-sort: true
```

### 2. Risk Acceptance (`.trivyignore`)

To suppress documented false positives or accepted risks, create `.trivyignore`:

```text
# Accepted risk: Development only dependency
CVE-2024-XXXXX

# Patch planned in sprint 24
CVE-2023-YYYYY
```

---

## CI/CD Pipeline Integration (GitHub Actions)

Add Trivy as an automated security quality gate:

```yaml
name: Security Scan

on:
  push:
    branches: [ main ]
  pull_request:

jobs:
  trivy-scan:
    name: Trivy Security Scan
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-results.sarif'
          severity: 'CRITICAL,HIGH'

      - name: Upload SARIF to GitHub Security tab
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: 'trivy-results.sarif'
```

---

## Troubleshooting & Tips

- **Vulnerability DB Download Rate Limits**: Trivy downloads its vulnerability database from GitHub Container Registry (`ghcr.io/aquasecurity/trivy-db`). If facing rate limits, cache the DB or specify `--db-repository mirror.gcr.io/aquasecurity/trivy-db`.
- **Large Scans / High Memory**: Use `--skip-dirs` to exclude build artifacts, large datasets, or `.git/`.
- **Offline Scanning**: Pre-download the DB on a connected machine via `trivy image --download-db-only --cache-dir /path/to/cache`, then run with `--offline-scan`.
