import json
import pytest


@pytest.mark.parametrize("path", ["/chat", "/chat/stream"])
def test_provider_failure_is_sanitized_and_never_saved_as_success(client, registered, provider, path):
    _, headers = registered()
    provider.failure = "connection failed: provider-key=secret-should-never-leak"
    response = client.post(path, headers=headers, json={"message": "hello"})
    if path == "/chat":
        assert response.status_code == 502
    else:
        events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
        assert [e["type"] for e in events] == ["start", "error"]
    assert "secret-should-never-leak" not in response.text
    assert "Architectural Insights" not in response.text
    assert client.get("/chat/quota", headers=headers).json()["tokensRemaining"] == 5000
    conversations = client.get("/chat/conversations", headers=headers).json()
    for conversation in conversations:
        history = client.get(f"/chat/{conversation['id']}/history", headers=headers).json()
        assert all(message["role"] != "assistant" for message in history)


def test_missing_provider_configuration_fails_clearly(client, registered):
    _, headers = registered()
    response = client.post("/chat", headers=headers, json={"message": "hello"})
    assert response.status_code == 503
    assert "not configured" in response.json()["detail"]
