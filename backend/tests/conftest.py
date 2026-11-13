"""Offline HTTP/provider tests. Never read a developer's service credentials."""
import atexit
import os
import tempfile

import pytest

_tmp = tempfile.TemporaryDirectory(prefix="gptcraft-tests-")
atexit.register(_tmp.cleanup)
test_url = os.environ.get("GPTCRAFT_TEST_DATABASE_URL") or f"sqlite:///{_tmp.name}/suite.db"
if not test_url.startswith("sqlite:") and "test" not in test_url.rsplit("/", 1)[-1]:
    raise RuntimeError("GPTCRAFT_TEST_DATABASE_URL must name a dedicated test database")
os.environ.update(DATABASE_URL=test_url, SECRET_KEY="offline-test-secret", GROQ_API_KEY="",
                  SUPABASE_URL="", SUPABASE_JWT_SECRET="", SUPABASE_ANON_KEY="",
                  GOOGLE_CLIENT_ID="", GOOGLE_CLIENT_SECRET="", LANGSMITH_TRACING="false",
                  LANGCHAIN_TRACING_V2="false")

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import engine
from app.main import app, seed_default_plan
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def reset_database(monkeypatch):
    for key in ("ALL_PROXY", "all_proxy", "HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy"):
        monkeypatch.delenv(key, raising=False)
    get_settings.cache_clear()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    seed_default_plan()
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def registered(client):
    def register(email="alice@example.com"):
        response = client.post("/auth/register", json={"name": "Alice", "email": email,
                                                       "password": "password123"})
        assert response.status_code == 201
        data = response.json()
        headers = {"Authorization": f"Bearer {data['accessToken']}"}
        assert client.get("/chat/quota", headers=headers).status_code == 200
        return data, headers
    return register


@pytest.fixture
def provider(monkeypatch):
    import importlib
    from tests.fakes import ProviderFake
    fake = ProviderFake()
    monkeypatch.setattr(importlib.import_module("app.ai.graph.agent"), "get_llm", lambda **kwargs: fake)
    return fake
