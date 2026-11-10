# GPTCraft Coding Standards

These standards define the quality, architectural, and design judgement calls enforced during code reviews (`/code-review`). Automated linting and type-checking are enforced by CI and `scripts/verify.ps1`; this document covers conventions beyond what linters mechanically verify.

---

## 1. Architectural Boundaries & Layering

### 1.1 Backend Separation of Concerns
- **Routes (`app/api/routes/`)**: Transport layer only. Responsible for HTTP request/response parsing, query params, dependency injection (`get_db`, `get_current_user`), and HTTP status codes. **Never execute raw SQL queries, complex ORM transactions, or LLM graph invocations directly inside route functions.**
- **Services (`app/services/`)**: Business logic, policy checks (quota, active account verification), orchestration, and LangGraph workflow calls.
- **Data Access (`app/db/`)**: Database session management, SQLAlchemy declarative models (`app/db/models.py`), and atomic CRUD helpers.
- **AI Engine (`app/ai/`)**: State graphs, prompt templates, and model providers. LangGraph nodes must be pure functions of state whenever possible.

### 1.2 Frontend Component Hierarchy
- **Pages (`frontend/src/pages/`)**: Route containers that compose layouts, hooks, and section components. Keep page files lean (< 250 lines).
- **Custom Hooks (`frontend/src/hooks/`)**: Encapsulate non-trivial component state, network subscriptions, and event listeners.
- **Components (`frontend/src/components/`)**: Reusable UI primitives and isolated widgets. Must handle `loading`, `error`, and `empty` states explicitly.

---

## 2. Cross-Stack Contract Conventions

### 2.1 Casing and Data Serialization
- **Public API Responses**: All external JSON payloads consumed by the frontend must use camelCase for properties (e.g., `accessToken`, `tokenType`, `totalTokens`, `createdAt`).
- **Internal Python**: Models, schemas, database columns, and service methods use `snake_case`. Pydantic schemas must use aliases or camelCase population configs for frontend-facing models.
- **TypeScript Sync**: When changing a Pydantic schema in `backend/app/schemas/`, simultaneously update the corresponding TypeScript interface in `frontend/src/types/index.ts`.

### 2.2 Tier & Quota Hierarchy
- User plans follow the strict tier hierarchy: `free` -> `super` -> `hyper`.
- Legacy `pro` references must always map to the paid tier equivalent.
- Every feature or model gate must cleanly fall back to informing the user of the upgrade requirement rather than returning generic `500` server errors.

---

## 3. Security, Privacy & Ownership

### 3.1 Strict Data Isolation
- **Conversation Ownership**: Every query retrieving, mutating, or streaming conversation messages must enforce `conversation.user_id == current_user.id`.
- **Active Account Check**: `AuthService.get_user_by_token` and auth dependencies must verify `user.is_active` and raise `403 Forbidden` for disabled accounts.

### 3.2 Secrets & Token Exposure
- LLM provider API keys (`GROQ_API_KEY`, etc.) and JWT signing secrets (`SECRET_KEY`) must **never** be exposed to frontend client bundles, `VITE_*` environment variables, or client-side error logs.
- All AI token accounting and rate limiting must execute server-side.

---

## 4. UI Design System & Theme Compatibility

### 4.1 Semantic CSS Tokens
- The GPTCraft visual system uses the "Paper & Ink" design tokens.
- **Never use hardcoded hex or raw Tailwind colors** (such as `#ffffff`, `bg-gray-100`, `text-black`) for main structural elements.
- Use semantic CSS variables and tokens:
  - Backgrounds: `var(--canvas)`, `var(--surface)`, `var(--raised)`
  - Text & Lines: `var(--ink)`, `var(--line)`
  - Accent/Brand: `var(--ember)`
- Ensure every new UI element renders with high contrast and readable typography in both light and dark modes.

---

## 5. Streaming & Network Resilience

### 5.1 SSE (Server-Sent Events) Hygiene
- Real-time token streaming endpoints (`/chat`) must use Server-Sent Events (`text/event-stream`).
- Handle client disconnections gracefully: ensure generator functions terminate without orphan background LLM tasks when the connection drops or the user clicks "Stop Generating" (`AbortController`).

---

## 6. Testing & Deterministic Verification

### 6.1 Zero-Network Offline Testing
- Backend unit and integration tests (`backend/tests/`) must **never** call live external LLM APIs (Groq, Anthropic, OpenAI). Always mock AI graph execution (`agent.invoke`) in automated test runs.
- Test suites must use an isolated temporary database fixture and leave no persistent `.db` artifacts behind.

### 6.2 Full-Stack Verification Rule
- Before completing any task or preparing a PR, run the verification harness:
  ```powershell
  powershell -ExecutionPolicy Bypass -File scripts/verify.ps1
  ```
  Both backend pytest and frontend `tsc --noEmit` + `vite build` must pass with 0 errors.
