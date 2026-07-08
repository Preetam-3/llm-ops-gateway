"""Tests for the chat endpoint."""

from unittest.mock import AsyncMock, MagicMock, patch

from app.providers.router import provider_router

# ── Mock streaming helpers ──


async def _mock_stream_success(messages):
    yield {"choices": [{"delta": {"content": "Hello"}, "index": 0}]}
    yield {"choices": [{"delta": {"content": " world"}, "index": 0}]}
    yield {"choices": [{"delta": {}, "finish_reason": "stop", "index": 0}]}


async def _mock_stream_error(messages):
    raise RuntimeError("Upstream failure")
    yield  # pragma: no cover


def _mock_provider(*, stream=_mock_stream_success):
    """Build a mock provider with a controllable stream method."""
    m = MagicMock()
    m.model = "test-model"
    m.chat_completion_stream = stream
    m.chat_completion = MagicMock()
    return m


# ── Tests ──


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
    resp = test_client.post("/v1/chat", json={"messages": []}, headers=_AUTH)
    assert resp.status_code == 400


# ── Stream endpoint tests ──


def test_chat_stream_no_auth(test_client):
    resp = test_client.post("/v1/chat/stream", json={"messages": [{"role": "user", "content": "hi"}]})
    assert resp.status_code == 401


def test_chat_stream_invalid_key(test_client):
    headers = {"Authorization": "Bearer wrong-key"}
    resp = test_client.post(
        "/v1/chat/stream",
        json={"messages": [{"role": "user", "content": "hi"}]},
        headers=headers,
    )
    assert resp.status_code == 403


def test_chat_stream_empty_messages(test_client):
    resp = test_client.post("/v1/chat/stream", json={"messages": []}, headers=_AUTH)
    assert resp.status_code == 400


def test_chat_stream_success(test_client):
    with patch.object(provider_router, "get_provider", return_value=_mock_provider()):
        resp = test_client.post(
            "/v1/chat/stream",
            json={"messages": [{"role": "user", "content": "hi"}]},
            headers=_AUTH,
        )
    assert resp.status_code == 200
    assert resp.headers.get("content-type", "").startswith("text/event-stream")
    assert "Hello" in resp.text
    assert "world" in resp.text
    assert '"finish_reason": "stop"' in resp.text
    assert "[DONE]" in resp.text


def _mock_provider_with_response():
    """Mock provider that returns a static completion response."""
    m = MagicMock()
    m.model = "test-model"
    m.chat_completion_stream = _mock_stream_success
    m.chat_completion = AsyncMock(return_value={
        "choices": [{"message": {"content": "Hello from mock"}}],
        "model": "test-model",
        "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
    })
    return m


# ── History endpoint tests ──


_AUTH = {"Authorization": "Bearer test-key"}


# ── Fallback tests ──


def _make_provider_mock(name: str, model: str = "test-model"):
    m = MagicMock()
    m.name = name
    m.model = model
    return m


def test_chat_fallback_primary_fails_fallback_succeeds(test_client):
    """When primary provider fails, fallback provider should handle the request."""
    primary = _make_provider_mock("groq")
    primary.chat_completion = MagicMock(side_effect=RuntimeError("primary down"))

    fallback = _make_provider_mock("openai")
    fallback.chat_completion = AsyncMock(return_value={
        "choices": [{"message": {"content": "from fallback"}}],
        "model": "gpt-4o",
        "usage": {},
    })

    with (
        patch.object(provider_router, "get_provider", return_value=primary),
        patch.object(provider_router, "_providers", [primary, fallback]),
    ):
        resp = test_client.post(
            "/v1/chat",
            json={"messages": [{"role": "user", "content": "hi"}]},
            headers=_AUTH,
        )

    assert resp.status_code == 200
    assert resp.json()["reply"] == "from fallback"
    assert resp.json()["model"] == "gpt-4o"


def test_chat_all_providers_fail(test_client):
    """When all providers fail, return 502."""
    primary = _make_provider_mock("groq")
    primary.chat_completion = MagicMock(side_effect=RuntimeError("primary crash"))

    fallback = _make_provider_mock("openai")
    fallback.chat_completion = MagicMock(side_effect=RuntimeError("fallback crash"))

    with (
        patch.object(provider_router, "get_provider", return_value=primary),
        patch.object(provider_router, "_providers", [primary, fallback]),
    ):
        resp = test_client.post(
            "/v1/chat",
            json={"messages": [{"role": "user", "content": "hi"}]},
            headers=_AUTH,
        )

    assert resp.status_code == 502


def test_chat_history_no_auth(test_client):
    resp = test_client.get("/v1/chat/history")
    assert resp.status_code == 401


def test_chat_history_empty(test_client):
    resp = test_client.get("/v1/chat/history", headers=_AUTH)
    assert resp.status_code == 200
    assert resp.json() == {"conversations": [], "limit": 20, "offset": 0}


def test_chat_history_not_found(test_client):
    resp = test_client.get("/v1/chat/history/nonexistent-id", headers=_AUTH)
    assert resp.status_code == 404


def test_chat_persistence(test_client):
    """Send a chat, then verify it shows up in history."""
    with patch.object(
        provider_router, "get_provider", return_value=_mock_provider_with_response()
    ):
        chat_resp = test_client.post(
            "/v1/chat",
            json={"messages": [{"role": "user", "content": "hello"}]},
            headers=_AUTH,
        )
    assert chat_resp.status_code == 200
    data = chat_resp.json()
    assert "conversation_id" in data
    assert data["reply"] == "Hello from mock"
    assert data["usage"]["total_tokens"] == 8

    # Verify it appears in history
    hist_resp = test_client.get("/v1/chat/history", headers=_AUTH)
    assert hist_resp.status_code == 200
    hist = hist_resp.json()
    assert len(hist["conversations"]) == 1
    assert hist["conversations"][0]["id"] == data["conversation_id"]

    # Verify we can fetch the conversation messages
    msg_resp = test_client.get(
        f"/v1/chat/history/{data['conversation_id']}", headers=_AUTH
    )
    assert msg_resp.status_code == 200
    msg_data = msg_resp.json()
    assert len(msg_data["messages"]) == 2  # user + assistant
    assert msg_data["messages"][0]["role"] == "user"
    assert msg_data["messages"][1]["role"] == "assistant"
    assert msg_data["messages"][1]["content"] == "Hello from mock"


def test_chat_stream_upstream_error(test_client):
    with patch.object(
        provider_router,
        "get_provider",
        return_value=_mock_provider(stream=_mock_stream_error),
    ):
        resp = test_client.post(
            "/v1/chat/stream",
            json={"messages": [{"role": "user", "content": "hi"}]},
            headers=_AUTH,
        )
    assert resp.status_code == 200  # SSE stream with error event inside
    assert "Upstream failure" in resp.text
    assert "[DONE]" in resp.text
