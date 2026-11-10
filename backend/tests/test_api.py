import os
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

# Set required env vars before importing app
os.environ["DATABASE_URL"] = "sqlite:///./test_suite.db"
os.environ["SECRET_KEY"] = "test-secret-key-for-ci-harness"
os.environ["GROQ_API_KEY"] = "test-groq-api-key"

from app.main import app, seed_default_plan
from app.db.base import Base
from app.db.session import engine


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

    # 2. Login returns AuthResponse shape
    login_res = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "password123"},
    )
    assert login_res.status_code == 200
    login_data = login_res.json()
    token = login_data["accessToken"]
    assert token

    # 3. /auth/me validates token
    me_res = client.get(f"/auth/me?token={token}")
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "alice@example.com"


@patch("app.services.chat.agent.invoke")
def test_chat_quota_and_conversation_ownership(mock_invoke):
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

    # User A sends a chat message with model selection
    chat_res = client.post(
        "/chat",
        headers=headers_a,
        json={"message": "Build me an AI app", "model": "llama3-8b-8192"},
    )
    assert chat_res.status_code == 200
    chat_data = chat_res.json()
    assert chat_data["response"] == "Hello from mocked GPTCraft AI!"
    assert chat_data["tokens_used"] == 42
    assert chat_data["tokens_remaining"] == 4958
    conv_id = chat_data["conversation_id"]

    # Check updated quota for User A
    quota_after = client.get("/chat/quota", headers=headers_a).json()
    assert quota_after["requestsRemaining"] == 49
    assert quota_after["tokensRemaining"] == 4958

    # User A can read conversation history
    hist_a = client.get(f"/chat/{conv_id}/history", headers=headers_a)
    assert hist_a.status_code == 200
    assert len(hist_a.json()) == 2

    # User B CANNOT read User A's conversation history
    hist_b = client.get(f"/chat/{conv_id}/history", headers=headers_b)
    assert hist_b.status_code == 404
