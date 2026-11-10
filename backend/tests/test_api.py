import json
import os
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

# Set required env vars before importing app
os.environ["DATABASE_URL"] = "sqlite:///./test_suite.db"
os.environ["SECRET_KEY"] = "test-secret-key-for-ci-harness"
os.environ["GROQ_API_KEY"] = "test-groq-api-key"

from app.main import app, seed_default_plan
from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.db.models import User
from app.db.crud_token import TokenUsageCRUD


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    seed_default_plan()
    yield
    Base.metadata.drop_all(bind=engine)


client = TestClient(app)


def test_health_check():
    res = client.get("/")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"


def test_register_and_login_contract():
    # 1. Register returns AuthResponse shape (accessToken, tokenType, user)
    reg_res = client.post(
        "/auth/register",
        json={"name": "Alice", "email": "alice@example.com", "password": "password123"},
    )
    assert reg_res.status_code == 201
    reg_data = reg_res.json()
    assert "accessToken" in reg_data
    assert reg_data["user"]["email"] == "alice@example.com"
    assert reg_data["user"]["plan"] == "free"

    # 2. Duplicate registration returns 400
    dup_res = client.post(
        "/auth/register",
        json={"name": "Alice2", "email": "alice@example.com", "password": "password123"},
    )
    assert dup_res.status_code == 400

    # 3. Login returns AuthResponse shape
    login_res = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "password123"},
    )
    assert login_res.status_code == 200
    login_data = login_res.json()
    token = login_data["accessToken"]
    assert token

    # 4. /auth/me validates token
    me_res = client.get(f"/auth/me?token={token}")
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "alice@example.com"


def test_inactive_user_blocked():
    reg_res = client.post(
        "/auth/register",
        json={"name": "Bob", "email": "bob@example.com", "password": "password123"},
    ).json()
    token = reg_res["accessToken"]

    # Deactivate Bob in DB
    db = SessionLocal()
    bob = db.query(User).filter(User.email == "bob@example.com").first()
    bob.is_active = False
    db.commit()
    db.close()

    # Token check should return 403 Forbidden
    me_res = client.get(f"/auth/me?token={token}")
    assert me_res.status_code == 403

    # Login should also return 403 Forbidden
    login_res = client.post(
        "/auth/login",
        json={"email": "bob@example.com", "password": "password123"},
    )
    assert login_res.status_code == 403


def test_models_catalog_and_plan_upgrade_unlocks_models():
    models_res = client.get("/chat/models")
    assert models_res.status_code == 200
    models = models_res.json()
    assert len(models) == 4
    assert {m["id"] for m in models} == {
        "llama3-8b-8192",
        "gemma-7b-it",
        "mixtral-8x7b-32768",
        "llama3-70b-8192",
    }

    # Register Free user
    user_data = client.post(
        "/auth/register",
        json={"name": "Charlie", "email": "charlie@example.com", "password": "password123"},
    ).json()
    headers = {"Authorization": f"Bearer {user_data['accessToken']}"}

    # Free user cannot call Hyper model (llama3-70b-8192)
    locked_res = client.post(
        "/chat",
        headers=headers,
        json={"message": "Test 70b lock", "model": "llama3-70b-8192"},
    )
    assert locked_res.status_code == 403

    # Upgrade to Super plan -> unlocks Mixtral (50,000 tokens, 500 requests)
    up_super = client.post("/auth/plan", headers=headers, json={"plan": "super"})
    assert up_super.status_code == 200
    assert up_super.json()["plan"] == "super"

    quota_super = client.get("/chat/quota", headers=headers).json()
    assert quota_super["totalTokens"] == 50000
    assert quota_super["totalRequests"] == 500

    # Upgrade to Hyper plan -> unlocks Llama 3.3 70B (500,000 tokens, 5,000 requests)
    up_hyper = client.post("/auth/plan", headers=headers, json={"plan": "hyper"})
    assert up_hyper.status_code == 200
    assert up_hyper.json()["plan"] == "hyper"

    unlocked_res = client.post(
        "/chat",
        headers=headers,
        json={"message": "Now I have Hyper access", "model": "llama3-70b-8192", "mode": "architect"},
    )
    assert unlocked_res.status_code == 200
    assert unlocked_res.json()["mode_used"] == "architect"


@patch("app.services.chat.agent.invoke")
def test_chat_quota_deletion_and_conversation_ownership(mock_invoke):
    mock_msg = AIMessage(
        content="Hello from mocked GPTCraft AI!",
        response_metadata={"token_usage": {"total_tokens": 42}},
    )
    mock_invoke.return_value = {"messages": [mock_msg]}

    # Register User A & User B
    user_a = client.post(
        "/auth/register",
        json={"name": "User A", "email": "a@example.com", "password": "password123"},
    ).json()
    user_b = client.post(
        "/auth/register",
        json={"name": "User B", "email": "b@example.com", "password": "password123"},
    ).json()

    headers_a = {"Authorization": f"Bearer {user_a['accessToken']}"}
    headers_b = {"Authorization": f"Bearer {user_b['accessToken']}"}

    # Check initial quota for User A
    quota_res = client.get("/chat/quota", headers=headers_a)
    assert quota_res.status_code == 200
    assert quota_res.json() == {
        "requestsRemaining": 50,
        "tokensRemaining": 5000,
        "totalRequests": 50,
        "totalTokens": 5000,
    }

    # User A sends a chat message with model & mode selection
    chat_res = client.post(
        "/chat",
        headers=headers_a,
        json={"message": "Build me an AI app", "model": "llama3-8b-8192", "mode": "code"},
    )
    assert chat_res.status_code == 200
    chat_data = chat_res.json()
    assert chat_data["response"] == "Hello from mocked GPTCraft AI!"
    assert chat_data["tokens_used"] == 42
    assert chat_data["tokens_remaining"] == 4958
    assert chat_data["mode_used"] == "code"
    conv_id = chat_data["conversation_id"]

    # Check updated quota for User A
    quota_after = client.get("/chat/quota", headers=headers_a).json()
    assert quota_after["requestsRemaining"] == 49
    assert quota_after["tokensRemaining"] == 4958

    # User A can read conversation history
    hist_a = client.get(f"/chat/{conv_id}/history", headers=headers_a)
    assert hist_a.status_code == 200
    assert len(hist_a.json()) == 2

    # User B CANNOT read or delete User A's conversation
    hist_b = client.get(f"/chat/{conv_id}/history", headers=headers_b)
    assert hist_b.status_code == 404
    del_b = client.delete(f"/chat/{conv_id}", headers=headers_b)
    assert del_b.status_code == 404

    # User A can delete their own conversation
    del_a = client.delete(f"/chat/{conv_id}", headers=headers_a)
    assert del_a.status_code == 204
    assert client.get(f"/chat/{conv_id}/history", headers=headers_a).status_code == 404


def test_sse_stream_endpoint_and_quota_exhaustion():
    user = client.post(
        "/auth/register",
        json={"name": "Streamer", "email": "stream@example.com", "password": "password123"},
    ).json()
    headers = {"Authorization": f"Bearer {user['accessToken']}"}

    # Test real SSE streaming endpoint (/chat/stream)
    with client.stream(
        "POST",
        "/chat/stream",
        headers=headers,
        json={"message": "Stream a response in architect mode", "model": "llama3-8b-8192", "mode": "architect"},
    ) as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        events = []
        for line in response.iter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))

    assert any(e["type"] == "chunk" for e in events)
    done_events = [e for e in events if e["type"] == "done"]
    assert len(done_events) == 1
    assert done_events[0]["mode_used"] == "architect"

    # Exhaust daily token limit and verify 402 Payment Required
    db = SessionLocal()
    u_obj = db.query(User).filter(User.email == "stream@example.com").first()
    limit = TokenUsageCRUD.get_user_limit(db, u_obj.id)
    limit.daily_limit = 0
    db.commit()
    db.close()

    exhausted_res = client.post(
        "/chat",
        headers=headers,
        json={"message": "Should fail with 402", "model": "llama3-8b-8192"},
    )
    assert exhausted_res.status_code == 402
