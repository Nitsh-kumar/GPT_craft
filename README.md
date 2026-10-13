# GPTCraft — AI Chat Backend

A personal AI chat application built with FastAPI, SQLAlchemy, LangGraph, and Groq. The backend contains registration/login, persisted conversations, and an LLM response path.

**Status:** in development. Authentication, tier handling, quotas, and frontend integration need fixes and runtime verification. This personal project is separate from the employer CRAFT SAP code-migration project.

## Branches

| Branch | Contents |
| --- | --- |
| `backend` | Default branch: Python API and persistence |
| [`frontend`](https://github.com/Nitsh-kumar/GPT_craft/tree/frontend) | React/TypeScript interface and API client |

The UI and API are on separate branches; cloning only the default branch does not include the UI.

## Implemented components

- FastAPI auth, chat, and Google OAuth routes.
- SQLAlchemy user, conversation, message, and token-usage models.
- Conversation ownership checks in the chat/history flow.
- A LangGraph chatbot node that calls Groq.

The graph is a chat workflow, not evidence of tool use, multi-agent reasoning, or MCP integration.

## Backend setup

```bash
git clone --branch backend https://github.com/Nitsh-kumar/GPT_craft.git
cd GPT_craft
python -m venv .venv
```

Activate the virtual environment. Install dependencies with `python -m pip install -r requirements.txt`.

Create a local `.env` file:

```dotenv
DATABASE_URL=sqlite:///./test.db
SECRET_KEY=replace_with_a_new_random_secret
GROQ_API_KEY=replace_with_your_provider_key
FRONTEND_URL=http://localhost:3000
DEBUG=False
```

Use your own fresh values. Google OAuth additionally requires `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and the configured callback URI. Settings are defined in [app/core/config.py](app/core/config.py).

The manifest currently omits a direct `langgraph` dependency even though the graph imports it. Resolve and record a compatible version before treating setup as reproducible.

```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

After successful startup, inspect `http://localhost:8000/docs`. Startup currently creates tables and seeds plans; use an isolated development database.

## API entry points

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/auth/register` | Register |
| POST | `/auth/login` | Login |
| POST | `/chat` | Generate a reply |
| GET | `/chat/conversations` | List the user's conversations |
| GET | `/chat/{conversation_id}/history` | Read owned history |
| GET | `/chat/quota` | Return quota information |

## Frontend setup

Clone `frontend` into a separate directory. Install its dependencies, set `VITE_API_BASE_URL=http://localhost:8000` in its local environment, and run `npm run dev`. Read that branch's README for its build and type-check commands.

Model lists, plan names, and quota contracts currently differ between branches. The UI reveals a completed reply gradually; this is not network token streaming.

## Engineering follow-up

Fix identity/plan contracts, disabled-user checks, OAuth token transport, and concurrency-safe quota accounting before public exposure. Rate-limit helpers exist, but the chat endpoint does not apply a limiter decorator. No automated backend test suite or CI workflow is present in the reviewed default branch.

See [project status](docs/PROJECT_STATUS.md).

## Validation

This documentation was checked against repository files on 13 October 2026. Builds, application runs, and test suites were not executed during this documentation pass. Commands below describe the intended local workflow, not a verified deployment.
