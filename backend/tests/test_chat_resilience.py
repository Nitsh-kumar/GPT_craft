import os
import json
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = "sqlite:///./test_suite.db"
os.environ["SECRET_KEY"] = "test-secret-key-for-ci-harness"
# Do not override GROQ_API_KEY if we want to test model failure, or mock agent to raise the exact Groq error:

from app.main import app, seed_default_plan
from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.db.models import User

@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    seed_default_plan()
    yield
    Base.metadata.drop_all(bind=engine)

client = TestClient(app, raise_server_exceptions=True)

def test_chat_stream_when_llm_fails_does_not_crash_connection():
    """
    When the LLM provider fails (e.g. model not found / decommissioned / API error),
    the streaming endpoint must NOT crash with 'RuntimeError: Caught handled exception, but response already started.'
    It should either yield an SSE error event or return an HTTP error before streaming starts.
    """
    # Register user
    reg = client.post(
        "/auth/register",
        json={"name": "Alice", "email": "alice@example.com", "password": "password123"},
    )
    assert reg.status_code == 201
    token = reg.json()["accessToken"]
    headers = {"Authorization": f"Bearer {token}"}

    # Simulate Groq 404 model_not_found error on the LangGraph streaming seam
    with patch("app.services.chat.agent.stream") as mock_stream:
        mock_stream.side_effect = Exception("The model `llama-3.1-8b-instant` does not exist or you do not have access to it.")
        
        # Test stream endpoint
        with client.stream(
            "POST",
            "/chat/stream",
            headers=headers,
            json={"message": "Break down vector embeddings", "model": "llama3-8b-8192"},
        ) as response:
            lines = [line for line in response.iter_lines() if line]
            events = [json.loads(line[6:]) for line in lines if line.startswith("data: ")]
            
            # The client should receive an error event rather than a connection crash
            error_events = [e for e in events if e.get("type") == "error"]
            assert len(error_events) == 1, f"Expected 1 error event, got events: {events}"
            assert "The model `llama-3.1-8b-instant` does not exist" in error_events[0]["error"]
