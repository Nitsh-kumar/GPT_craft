import os
import json
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = "sqlite:///./test_suite.db"
os.environ["SECRET_KEY"] = "test-secret-key-for-ci-harness"
os.environ["GROQ_API_KEY"] = "test-groq-api-key"

from app.main import app, seed_default_plan
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.services.memory import MemoryService

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_db():
    os.environ["GROQ_API_KEY"] = "test-groq-api-key"
    get_settings.cache_clear()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    seed_default_plan()
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def cleanup_sqlite_file():
    yield
    engine.dispose()
    for db_file in ("test_suite.db", "backend/test_suite.db"):
        if os.path.exists(db_file):
            try:
                os.remove(db_file)
            except OSError:
                pass


def register_user(name="MemUser", email="mem@example.com", password="password123"):
    res = client.post(
        "/auth/register",
        json={"name": name, "email": email, "password": password},
    )
    assert res.status_code == 201
    data = res.json()
    return data["accessToken"], data["user"]["id"]


def test_preferences_lifecycle_and_camelcase_contract():
    token, _ = register_user()
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Fetch default preferences and verify camelCase serialization
    res = client.get("/memory/preferences", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "userId" in data
    assert "memoryEnabled" in data
    assert "customInstructionsProfile" in data
    assert "customInstructionsStyle" in data
    assert "user_id" not in data
    assert "memory_enabled" not in data
    assert data["memoryEnabled"] is True
    assert data["customInstructionsProfile"] is None
    assert data["customInstructionsStyle"] is None

    # 2. Update custom instructions using camelCase payload
    update_res = client.put(
        "/memory/preferences",
        headers=headers,
        json={
            "customInstructionsProfile": "Full-stack engineer using Python and React",
            "customInstructionsStyle": "Be direct, code-first, and concise",
            "memoryEnabled": True,
        },
    )
    assert update_res.status_code == 200
    updated = update_res.json()
    assert updated["customInstructionsProfile"] == "Full-stack engineer using Python and React"
    assert updated["customInstructionsStyle"] == "Be direct, code-first, and concise"
    assert updated["memoryEnabled"] is True

    # 3. Toggle memory off
    toggle_res = client.put(
        "/memory/preferences",
        headers=headers,
        json={"memoryEnabled": False},
    )
    assert toggle_res.status_code == 200
    assert toggle_res.json()["memoryEnabled"] is False


def test_memory_crud_and_listing_camelcase():
    token, _ = register_user()
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Initially empty
    list_res = client.get("/memory", headers=headers)
    assert list_res.status_code == 200
    assert list_res.json()["total"] == 0
    assert list_res.json()["memoryEnabled"] is True

    # 2. Add memories
    mem1 = client.post(
        "/memory",
        headers=headers,
        json={"content": "Prefers FastAPI over Flask", "category": "tech_stack"},
    )
    assert mem1.status_code == 201
    mem1_json = mem1.json()
    assert "userId" in mem1_json
    assert "isActive" in mem1_json
    assert "createdAt" in mem1_json
    assert "user_id" not in mem1_json
    mem1_id = mem1_json["id"]
    assert mem1_json["content"] == "Prefers FastAPI over Flask"

    mem2 = client.post(
        "/memory",
        headers=headers,
        json={"content": "Project name is GPTCraft", "category": "project"},
    )
    assert mem2.status_code == 201
    mem2_id = mem2.json()["id"]

    # 3. List memories
    list_res = client.get("/memory", headers=headers)
    assert list_res.status_code == 200
    memories = list_res.json()["memories"]
    assert len(memories) == 2

    # 4. Delete one memory
    del_res = client.delete(f"/memory/{mem1_id}", headers=headers)
    assert del_res.status_code == 204

    list_res2 = client.get("/memory", headers=headers)
    assert list_res2.json()["total"] == 1
    assert list_res2.json()["memories"][0]["id"] == mem2_id

    # 5. Clear all memories
    clear_res = client.delete("/memory", headers=headers)
    assert clear_res.status_code == 200
    assert clear_res.json()["count"] == 1

    list_res3 = client.get("/memory", headers=headers)
    assert list_res3.json()["total"] == 0


def test_invalid_memory_category_rejected():
    token, _ = register_user(email="invalidcat@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post(
        "/memory",
        headers=headers,
        json={"content": "Some fact", "category": "invalid_category_name"},
    )
    assert res.status_code == 422


def test_memory_relevance_ranking():
    db = SessionLocal()
    try:
        _, user_id = register_user(email="ranking@example.com")

        MemoryService.add_memory(db, user_id, "User works with Python and FastAPI", category="tech_stack")
        MemoryService.add_memory(db, user_id, "User prefers dark roast coffee", category="preference")
        MemoryService.add_memory(db, user_id, "User prefers Tailwind CSS for frontend styling", category="tech_stack")

        relevant = MemoryService.get_relevant_memories(db, user_id, "How do I structure my FastAPI routes in Python?")
        assert len(relevant) > 0
        assert "FastAPI" in relevant[0]
    finally:
        db.close()


def test_memory_extraction_heuristic():
    text1 = "Please remember that I prefer TypeScript strict mode. How do I set it up?"
    extracted1 = MemoryService.extract_memories_from_text(text1)
    assert len(extracted1) == 1
    assert "TypeScript strict mode" in extracted1[0]["content"]
    assert "How do I set it up" not in extracted1[0]["content"]

    text2 = "My tech stack is Python, FastAPI, and React"
    extracted2 = MemoryService.extract_memories_from_text(text2)
    assert len(extracted2) >= 1
    assert "tech stack is" in extracted2[0]["content"].lower() or "python" in extracted2[0]["content"].lower()


def test_chat_with_memory_injection():
    token, _ = register_user(email="chatmem@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    client.put(
        "/memory/preferences",
        headers=headers,
        json={
            "customInstructionsProfile": "Full-stack architect with Python expertise",
            "customInstructionsStyle": "Concise and code-focused",
            "memoryEnabled": True,
        },
    )
    client.post(
        "/memory",
        headers=headers,
        json={"content": "Project name is AlphaCore", "category": "project"},
    )

    chat_res = client.post(
        "/chat",
        headers=headers,
        json={"message": "Can you review my project architecture?", "mode": "architect"},
    )
    assert chat_res.status_code == 200
    data = chat_res.json()
    assert data["mode_used"] == "architect"
    assert "Personalization Active" in data["response"]
    assert "AlphaCore" in data["response"]
    assert "Full-stack architect with Python expertise" in data["response"]


def test_memory_disabled_toggle():
    """
    When memoryEnabled is False:
    1. MemoryService.get_relevant_memories returns []
    2. /chat does NOT inject personalization or memories into the system prompt
    3. /chat does NOT auto-extract new memories from user turns
    """
    token, user_id = register_user(email="disabledmem@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Seed instructions and an existing memory while enabled
    client.post(
        "/memory",
        headers=headers,
        json={"content": "Project name is SecretVault", "category": "project"},
    )
    client.put(
        "/memory/preferences",
        headers=headers,
        json={
            "customInstructionsProfile": "Senior Rust Engineer",
            "customInstructionsStyle": "Minimalist",
            "memoryEnabled": False,
        },
    )

    db = SessionLocal()
    try:
        assert MemoryService.get_relevant_memories(db, user_id, "Tell me about SecretVault") == []
    finally:
        db.close()

    # Chat turn with explicit extraction trigger while memoryEnabled=False
    chat_res = client.post(
        "/chat",
        headers=headers,
        json={"message": "Please remember that I use Rust and tell me about SecretVault"},
    )
    assert chat_res.status_code == 200
    assert "Personalization Active" not in chat_res.json()["response"]

    # Verify the Rust memory was NOT extracted/persisted
    memories = client.get("/memory", headers=headers).json()["memories"]
    assert len(memories) == 1
    assert not any("Rust" in m["content"] for m in memories)


def test_chat_auto_memory_extraction_and_post_turn_safety():
    token, _ = register_user(email="autoextract@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. If LLM invocation fails mid-turn, post-turn extraction must NOT persist memories
    with patch("app.services.chat.agent.invoke") as mock_invoke:
        mock_invoke.side_effect = RuntimeError("Upstream provider failure")
        fail_res = client.post(
            "/chat",
            headers=headers,
            json={"message": "Please remember that I use Cobol on mainframes"},
        )
        assert fail_res.status_code == 500

    assert client.get("/memory", headers=headers).json()["total"] == 0

    # 2. Successful turn extracts and persists the memory post-turn
    res = client.post(
        "/chat",
        headers=headers,
        json={"message": "Please remember that I use Tailwind v4 on all components"},
    )
    assert res.status_code == 200

    list_res = client.get("/memory", headers=headers)
    assert list_res.status_code == 200
    memories = list_res.json()["memories"]
    assert any("Tailwind v4" in m["content"] for m in memories)


def test_streaming_sse_endpoint():
    token, _ = register_user(email="streamuser@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post(
        "/chat/stream",
        headers=headers,
        json={"message": "Explain what is FastAPI", "mode": "code"},
    )
    assert res.status_code == 200
    assert "text/event-stream" in res.headers["content-type"]

    body = res.text
    assert "data: " in body
    assert '"type": "chunk"' in body
    assert '"type": "done"' in body
