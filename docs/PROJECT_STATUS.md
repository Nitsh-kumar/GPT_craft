# Project Status

Updated: 10 November 2026

## Completed in Monorepo Merge & Harness Pass

1. **Unified Monorepo (`main` branch)**:
   - Merged `backend` and `origin/frontend` into a clean `backend/` + `frontend/` monorepo structure while preserving Git history from both branches.
   - Removed duplicate root OpenAPI dumps (`openapi*.json`), accidental `app/db/__init__,py` typo file, and unused server/AI packages from `frontend/package.json`.
2. **Contract & Build Fixes**:
   - Added missing `langgraph`, `langchain-core`, and `pytest` dependencies to `backend/requirements.txt`.
   - Fixed `POST /auth/register` to return an `AuthResponse` (`accessToken`, `tokenType`, `user`) matching `frontend/src/context/AuthContext.tsx`.
   - Fixed `useQuota.ts` 0-argument `chatService.getQuota()` call and aligned `User.id` typing (`string | number`).
   - Wired `model` selection from `frontend/src/services/chatService.ts` through `ChatRequest` -> `ChatService` -> LangGraph `chatbot_node` -> `get_llm()`.
   - Fixed `chat.py` attribute bug (`current_user.plan` on `UserResponse`) and added inactive-user (`403 Forbidden`) check to `AuthService.get_user_by_token`.
3. **AGY CLI Harness**:
   - Added root and directory-scoped `AGENTS.md` rule files.
   - Added `.agents/skills/gptcraft-verify` and `.agents/skills/gptcraft-dev` skills.
   - Added `.agents/hooks.json` (`SessionStart` hook) and `scripts/verify.ps1` + `backend/tests/test_api.py`.

## Next Production Milestones

1. **Real SSE / WebSocket Token Streaming**: Replace simulated client-side word delay in `chatService.ts` with FastAPI `StreamingResponse` + LangGraph `.astream_events()`.
2. **Database Migrations**: Add Alembic migrations to `backend/` and remove `Base.metadata.create_all` from startup.
3. **Atomic Quota Reservation & Rate Limiting**: Apply SlowAPI limiter decorators to `/chat` and use atomic SQL updates for token deduction.
4. **Unique Differentiator Features**: Expand the LangGraph `agent.py` state machine with custom tools, branching workflows, or artifact/canvas generation.
