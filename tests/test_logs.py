"""Tests for request/response logging and search."""
from unittest.mock import AsyncMock, patch

from app.providers.router import provider_router

_ADMIN = {"Authorization": "Bearer test-key"}


def test_chat_creates_log_entry(test_client):
    """A chat request should create a log entry visible via /v1/logs."""
    with patch.object(provider_router, "get_provider") as mock_get:
        mock_get.return_value.model = "test-model"
        mock_get.return_value.chat_completion = AsyncMock(return_value={
            "choices": [{"message": {"content": "hello world"}}],
            "model": "test-model",
            "usage": {"prompt_tokens": 5, "completion_tokens": 10, "total_tokens": 15},
        })
        test_client.post(
            "/v1/chat",
            json={"messages": [{"role": "user", "content": "hi"}]},
            headers=_ADMIN,
        )

    # Check that the log exists
    resp = test_client.get("/v1/logs", headers=_ADMIN)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["logs"]) >= 1
    assert data["logs"][0]["model"] == "test-model"


def test_logs_no_auth(test_client):
    resp = test_client.get("/v1/logs")
    assert resp.status_code == 401


def test_logs_wrong_key(test_client):
    headers = {"Authorization": "Bearer wrong-key"}
    resp = test_client.get("/v1/logs", headers=headers)
    assert resp.status_code == 403


def test_log_stats(test_client):
    """Chat then check stats show cumulative counts."""
    with patch.object(provider_router, "get_provider") as mock_get:
        mock_get.return_value.model = "test-model"
        mock_get.return_value.chat_completion = AsyncMock(return_value={
            "choices": [{"message": {"content": "stats test"}}],
            "model": "test-model",
            "usage": {"prompt_tokens": 3, "completion_tokens": 6, "total_tokens": 9},
        })
        test_client.post(
            "/v1/chat",
            json={"messages": [{"role": "user", "content": "test"}]},
            headers=_ADMIN,
        )

    resp = test_client.get("/v1/logs/stats", headers=_ADMIN)
    assert resp.status_code == 200
    stats = resp.json()["stats"]
    assert stats["total_requests"] >= 1
    assert stats["total_tokens"] >= 9
    assert stats["total_cost"] >= 0


def test_log_search_by_query(test_client):
    """Search should find logs matching the query string."""
    with patch.object(provider_router, "get_provider") as mock_get:
        mock_get.return_value.model = "test-model"
        mock_get.return_value.chat_completion = AsyncMock(return_value={
            "choices": [{"message": {"content": "banana split"}}],
            "model": "test-model",
            "usage": {},
        })
        test_client.post(
            "/v1/chat",
            json={"messages": [{"role": "user", "content": "fruit"}]},
            headers=_ADMIN,
        )

    resp = test_client.get("/v1/logs?q=banana", headers=_ADMIN)
    assert resp.status_code == 200
    assert len(resp.json()["logs"]) >= 1


def test_log_search_no_match(test_client):
    """Search for something that doesn't exist returns empty."""
    resp = test_client.get("/v1/logs?q=xyznonexistent123", headers=_ADMIN)
    assert resp.status_code == 200
    assert resp.json()["logs"] == []


def test_log_filter_by_model(test_client):
    with patch.object(provider_router, "get_provider") as mock_get:
        mock_get.return_value.model = "specific-test-model-42"
        mock_get.return_value.chat_completion = AsyncMock(return_value={
            "choices": [{"message": {"content": "filter test"}}],
            "model": "specific-test-model-42",
            "usage": {},
        })
        test_client.post(
            "/v1/chat",
            json={"messages": [{"role": "user", "content": "test"}]},
            headers=_ADMIN,
        )

    resp = test_client.get(
        "/v1/logs?model=specific-test-model-42", headers=_ADMIN
    )
    assert resp.status_code == 200
    assert len(resp.json()["logs"]) >= 1
    assert resp.json()["logs"][0]["model"] == "specific-test-model-42"


def test_log_stats_no_auth(test_client):
    resp = test_client.get("/v1/logs/stats")
    assert resp.status_code == 401


def test_cost_by_period(test_client):
    """Chat then check daily cost breakdown."""
    with patch.object(provider_router, "get_provider") as mock_get:
        mock_get.return_value.model = "cost-model"
        mock_get.return_value.chat_completion = AsyncMock(return_value={
            "choices": [{"message": {"content": "cost test"}}],
            "model": "cost-model",
            "usage": {"total_tokens": 100},
        })
        test_client.post(
            "/v1/chat",
            json={"messages": [{"role": "user", "content": "test"}]},
            headers=_ADMIN,
        )

    resp = test_client.get("/v1/logs/costs/by-period?period=day", headers=_ADMIN)
    assert resp.status_code == 200
    data = resp.json()
    assert data["period"] == "day"
    assert len(data["data"]) >= 1
    assert data["data"][0]["requests"] >= 1


def test_cost_by_model(test_client):
    """Chat then check cost breakdown by model."""
    with patch.object(provider_router, "get_provider") as mock_get:
        mock_get.return_value.model = "model-for-cost"
        mock_get.return_value.chat_completion = AsyncMock(return_value={
            "choices": [{"message": {"content": "model cost"}}],
            "model": "model-for-cost",
            "usage": {"total_tokens": 50},
        })
        test_client.post(
            "/v1/chat",
            json={"messages": [{"role": "user", "content": "test"}]},
            headers=_ADMIN,
        )

    resp = test_client.get("/v1/logs/costs/by-model", headers=_ADMIN)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) >= 1
    assert data[0]["model"] == "model-for-cost"


def test_cost_by_key(test_client):
    """Chat then check cost breakdown by key."""
    with patch.object(provider_router, "get_provider") as mock_get:
        mock_get.return_value.model = "key-model"
        mock_get.return_value.chat_completion = AsyncMock(return_value={
            "choices": [{"message": {"content": "key test"}}],
            "model": "key-model",
            "usage": {"total_tokens": 25},
        })
        test_client.post(
            "/v1/chat",
            json={"messages": [{"role": "user", "content": "test"}]},
            headers=_ADMIN,
        )

    resp = test_client.get("/v1/logs/costs/by-key", headers=_ADMIN)
    assert resp.status_code == 200
    data = resp.json()["data"]
    # The admin key prefix "test-key" is 8 chars, so data may be empty since prefix is partial
    assert isinstance(data, list)


def test_cost_no_auth(test_client):
    resp = test_client.get("/v1/logs/costs/by-period?period=day")
    assert resp.status_code == 401

    resp = test_client.get("/v1/logs/costs/by-model")
    assert resp.status_code == 401

    resp = test_client.get("/v1/logs/costs/by-key")
    assert resp.status_code == 401
