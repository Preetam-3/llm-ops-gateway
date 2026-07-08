"""Tests for response caching."""
import json
from unittest.mock import AsyncMock, patch

from app.cache import _cache_key
from app.providers.router import provider_router

_ADMIN = {"Authorization": "Bearer test-key"}


def test_cache_key_deterministic():
    """Same model + messages produces the same cache key."""
    messages = [{"role": "user", "content": "hello"}]
    k1 = _cache_key("test-model", messages)
    k2 = _cache_key("test-model", messages)
    assert k1 == k2
    assert k1.startswith("llm_cache:")


def test_cache_key_different_inputs():
    """Different model or messages produce different keys."""
    msgs1 = [{"role": "user", "content": "hello"}]
    msgs2 = [{"role": "user", "content": "world"}]
    k1 = _cache_key("model-a", msgs1)
    k2 = _cache_key("model-b", msgs1)
    k3 = _cache_key("model-a", msgs2)
    assert len({k1, k2, k3}) == 3  # all unique


def test_cache_clear_no_auth(test_client):
    resp = test_client.post("/admin/cache/clear")
    assert resp.status_code == 401


def test_cache_clear_wrong_key(test_client):
    resp = test_client.post(
        "/admin/cache/clear",
        headers={"Authorization": "Bearer wrong-key"},
    )
    assert resp.status_code == 403


def test_cache_clear_with_admin(test_client):
    """Cache clear endpoint works with admin key (cache is empty but endpoint works)."""
    with patch("app.main.cache_clear", AsyncMock(return_value=0)):
        resp = test_client.post("/admin/cache/clear", headers=_ADMIN)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "cleared" in data
