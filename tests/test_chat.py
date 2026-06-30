"""Tests for the chat endpoint."""


def test_health_check(test_client):
    resp = test_client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_chat_no_auth(test_client):
    resp = test_client.post("/v1/chat", json={"messages": [{"role": "user", "content": "hi"}]})
    assert resp.status_code == 401


def test_chat_invalid_key(test_client):
    headers = {"Authorization": "Bearer wrong-key"}
    resp = test_client.post(
        "/v1/chat",
        json={"messages": [{"role": "user", "content": "hi"}]},
        headers=headers,
    )
    assert resp.status_code == 403


def test_chat_empty_messages(test_client):
    headers = {"Authorization": "Bearer test-key"}
    resp = test_client.post("/v1/chat", json={"messages": []}, headers=headers)
    assert resp.status_code == 400
