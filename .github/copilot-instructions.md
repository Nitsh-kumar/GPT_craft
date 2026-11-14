# GitHub Copilot Instructions — GPTCraft Monorepo

You are assisting with development on **GPTCraft**, a production AI chat platform built with FastAPI + LangGraph + SQLAlchemy on the backend and React 19 + TypeScript + Vite + Tailwind CSS v4 on the frontend.

---

## 1. Monorepo Working Directory Discipline

- **Backend**: Python FastAPI service in `backend/`. Commands (`pytest`, `uvicorn`, `alembic`) must be run with working directory `backend/` or `PYTHONPATH=backend` because imports use `from app....`.
- **Frontend**: React 19 SPA in `frontend/`. Commands (`npm run dev`, `npm run build`, `npm run lint`) must be run with working directory `frontend/`.
- User tier hierarchy is `free` -> `super` -> `hyper`.
- Auth endpoints (`/auth/login`, `/auth/register`) return camelCase (`accessToken`, `tokenType`, `user`).

---

## 2. Integrated Agent Skills

The repository includes modular skills in `.github/skills/` that specify procedures and tooling workflows:

1. **`keploy`** ([`.github/skills/keploy/SKILL.md`](./skills/keploy/SKILL.md)):
   - **Purpose**: Automated API test generation, network interaction recording, and dependency mock stubbing.
   - **Trigger**: When recording API traffic, replaying tests without external dependencies, or verifying breaking API changes.

2. **`mitmproxy`** ([`.github/skills/mitmproxy/SKILL.md`](./skills/mitmproxy/SKILL.md)):
   - **Purpose**: Interactive SSL/TLS intercepting proxy, packet manipulation, and API security testing.
   - **Trigger**: When inspecting, modifying, or fuzzing REST/WebSocket traffic, writing custom Python proxy addons (`mitmdump -s`), or auditing for OWASP API flaws.

3. **`trivy`** ([`.github/skills/trivy/SKILL.md`](./skills/trivy/SKILL.md)):
   - **Purpose**: Comprehensive security scanner for CVE vulnerabilities, exposed secrets, IaC misconfigurations, and SBOM generation.
   - **Trigger**: When scanning filesystems, dependencies (`requirements.txt`, `package.json`), Dockerfiles, or container images for security risks.

---

## 3. Verification & Quality Gates

Before finalizing changes or declaring work complete:
- Run backend test suite: `pytest` inside `backend/`
- Run frontend type check and build: `npm run build` inside `frontend/`
- Ensure no secret keys (`GROQ_API_KEY`, `SECRET_KEY`, etc.) are exposed to frontend client bundles.
