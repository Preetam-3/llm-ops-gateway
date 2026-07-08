"""Tests for multi-user API key management and DB-backed auth."""

from unittest.mock import AsyncMock, patch

from app.providers.router import provider_router

_ADMIN = {"Authorization": "Bearer test-key"}


# ── Admin key management endpoints ──


def test_admin_create_key(test_client):
    resp = test_client.post("/v1/admin/keys", json={"name": "Alice"}, headers=_ADMIN)
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Alice"
    assert data["raw_key"].startswith("gw_")
    assert "warning" in data


def test_admin_create_key_no_auth(test_client):
    resp = test_client.post("/v1/admin/keys", json={"name": "Alice"})
    assert resp.status_code == 401


def test_admin_create_key_wrong_key(test_client):
    headers = {"Authorization": "Bearer wrong-key"}
    resp = test_client.post("/v1/admin/keys", json={"name": "Alice"}, headers=headers)
    assert resp.status_code == 403  # admin required


def test_admin_create_key_no_name(test_client):
    resp = test_client.post("/v1/admin/keys", json={}, headers=_ADMIN)
    assert resp.status_code == 400


def test_admin_list_keys(test_client):
    # Create a couple keys
    test_client.post("/v1/admin/keys", json={"name": "Alice"}, headers=_ADMIN)
    test_client.post("/v1/admin/keys", json={"name": "Bob"}, headers=_ADMIN)

    resp = test_client.get("/v1/admin/keys", headers=_ADMIN)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["keys"]) >= 2

    # Keys should show prefix (not raw key) and is_active
    for k in data["keys"]:
        assert "prefix" in k
        assert "is_active" in k
        assert "key_hash" not in k  # hash must not leak


def test_admin_list_keys_no_auth(test_client):
    resp = test_client.get("/v1/admin/keys")
    assert resp.status_code == 401


# ── DB-managed key auth on chat endpoints ──


def test_user_key_can_chat(test_client):
    """Create a user key via admin, then use it to call /v1/chat."""
    # Create key
    create_resp = test_client.post(
        "/v1/admin/keys", json={"name": "Charlie"}, headers=_ADMIN
    )
    assert create_resp.status_code == 200
    raw_key = create_resp.json()["raw_key"]

    # Use it for chat (mock the provider since we're testing auth, not LLM)
    with patch.object(provider_router, "get_provider") as mock_get:
        mock_get.return_value.model = "test-model"
        mock_get.return_value.chat_completion = AsyncMock(return_value={
            "choices": [{"message": {"content": "ok"}}],
            "model": "test-model",
            "usage": {},
        })
        chat_resp = test_client.post(
            "/v1/chat",
            json={"messages": [{"role": "user", "content": "hi"}]},
            headers={"Authorization": f"Bearer {raw_key}"},
        )
    assert chat_resp.status_code == 200


def test_revoked_key_gets_403(test_client):
    """Create, revoke, then try to use the key — should fail."""
    create_resp = test_client.post(
        "/v1/admin/keys", json={"name": "Dave"}, headers=_ADMIN
    )
    key_id = create_resp.json()["id"]
    raw_key = create_resp.json()["raw_key"]

    # Revoke
    del_resp = test_client.delete(f"/v1/admin/keys/{key_id}", headers=_ADMIN)
    assert del_resp.status_code == 200

    # Try to chat with revoked key
    chat_resp = test_client.post(
        "/v1/chat",
        json={"messages": [{"role": "user", "content": "hi"}]},
        headers={"Authorization": f"Bearer {raw_key}"},
    )
    assert chat_resp.status_code == 403


def test_revoke_nonexistent_key(test_client):
    resp = test_client.delete(
        "/v1/admin/keys/nonexistent-id", headers=_ADMIN
    )
    assert resp.status_code == 404


def test_revoke_no_auth(test_client):
    resp = test_client.delete("/v1/admin/keys/some-id")
    assert resp.status_code == 401
