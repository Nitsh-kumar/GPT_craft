# GPTCraft Backend — Agent Rules (`backend/`)

## Stack & Conventions
- **Framework**: FastAPI (`app/main.py`) with Pydantic v2 (`app/schemas/`) and `pydantic-settings` (`app/core/config.py`).
- **Database**: SQLAlchemy 2.x ORM (`app/db/models.py`, `app/db/session.py`). Default local dev uses SQLite (`sqlite:///./test.db`); production targets PostgreSQL.
- **AI / Agent Engine**: LangGraph (`app/ai/graph/agent.py`, `app/ai/graph/state.py`) + Groq (`app/ai/llm.py`).
- **Authentication**: JWT Bearer tokens (`python-jose`) + Argon2 password hashing (`passlib[argon2]`) + Google OAuth (`authlib`).

## Strict Engineering Rules
1. **Virtual Environment**:
   - Never run global `pip install`. Always use `backend/.venv/Scripts/python.exe` and `backend/.venv/Scripts/python.exe -m pip` (or `.venv/bin/python -m pip` on POSIX).
   - Keep `backend/requirements.txt` updated whenever adding packages.

2. **Layered Architecture**:
   - `app/api/routes/`: HTTP transport, request validation, dependency injection (`get_db`, `get_current_user`), and rate limiting only.
   - `app/services/`: Business logic, policy/quota enforcement, and LangGraph invocation (`AuthService`, `ChatService`).
   - `app/db/`: CRUD helpers (`ChatCRUD`, `TokenUsageCRUD`) and SQLAlchemy models.
   - `app/ai/`: LangGraph state machines, nodes, tools, and LLM provider initialization.
3. **Security & Ownership**:
   - Every conversation and message query must verify `conversation.user_id == current_user.id`.
   - `AuthService.get_user_by_token` must always verify `user.is_active` and raise `403 Forbidden` for inactive accounts.
4. **Testing**:
   - Write and maintain `pytest` tests in `backend/tests/` for every new endpoint, service method, or LangGraph node.
   - Mock external LLM calls (`agent.invoke`) in unit/contract tests so tests run deterministically offline without consuming provider tokens.
