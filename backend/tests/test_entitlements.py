import pytest


@pytest.mark.parametrize("plan", ["super", "hyper", "free"])
def test_public_plan_mutation_is_disabled(client, registered, plan):
    user, headers = registered()
    before = client.get("/chat/quota", headers=headers).json()
    response = client.post("/auth/plan", headers=headers, json={"plan": plan})
    assert response.status_code == 403
    assert client.get("/auth/me", params={"token": user["accessToken"]}).json()["plan"] == "free"
    assert client.get("/chat/quota", headers=headers).json() == before
