"""Live end-to-end tests that exercise the gateway against real LLM providers.

These tests are skipped unless ALL of the following are true:

1.  ``E2E_REAL_LLM=1`` (or ``true``/``yes``) is set, AND
2.  a real provider API key is present
    (``GROQ_API_KEY`` / ``OPENAI_API_KEY`` / ``ANTHROPIC_API_KEY``).

They boot the actual FastAPI app with real settings, make real LLM
requests, and verify the full pipeline: auth -> rate limit -> provider ->
persistence -> logs -> analytics. Redis is optional (degraded mode).

Run them with:

.. code-block:: bash

    E2E_REAL_LLM=1 GROQ_API_KEY=gsk_... pytest e2e/ -v
"""

import os
import tempfile
from pathlib import Path

import pytest

# ── Gate the whole module behind an explicit opt-in ──────────────────

_e2e_mark = os.getenv("E2E_REAL_LLM", "").lower() in ("1", "true", "yes")

_real_keys = {
    "GROQ_API_KEY": os.getenv("GROQ_API_KEY", ""),
    "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", ""),
    "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY", ""),
}
_any_real_key = any(v and "test" not in v.lower() for v in _real_keys.values())

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        not (_e2e_mark and _any_real_key),
        reason=(
            "Live E2E tests require E2E_REAL_LLM=1 and a real provider API key "
            "(GROQ_API_KEY / OPENAI_API_KEY / ANTHROPIC_API_KEY)"
        ),
    ),
]

# ── Configure real-app settings before importing the gateway ─────────

os.environ["GATEWAY_API_KEY"] = os.getenv("E2E_GATEWAY_API_KEY", "e2e-admin-key")
os.environ["DATABASE_PATH"] = (
    os.getenv("E2E_DB_PATH")
    or str(Path(tempfile.gettempdir()) / f"llm-gateway-e2e-{os.getpid()}.db")
)
# Don't clobber a real Redis if E2E_REDIS_URL is provided; default to
# localhost which may be absent (degraded mode) or running.
os.environ["REDIS_URL"] = os.getenv("E2E_REDIS_URL", "redis://localhost:6379")
os.environ["CACHE_ENABLED"] = "true"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

_AUTH = {"Authorization": f"Bearer {os.environ['GATEWAY_API_KEY']}"}


@pytest.fixture(scope="module")
def live_client():
    """Boot the real gateway app (lifespan included) for the whole module."""
    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="module")
def conv_dicts(live_client):
    """Collect per-test conversation ids so history tests target our own data."""
    return {}


# ── Tests ─────────────────────────────────────────────────────────────


def test_health(live_client):
    resp = live_client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_no_auth_rejected(live_client):
    resp = live_client.post(
        "/v1/chat", json={"messages": [{"role": "user", "content": "hi"}]}
    )
    assert resp.status_code == 401


def test_real_chat_completion(live_client, conv_dicts):
    resp = live_client.post(
        "/v1/chat",
        json={"messages": [{"role": "user", "content": "Reply with the single word: ok"}]},
        headers=_AUTH,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["reply"]
    assert data["model"]
    assert data["usage"]["total_tokens"] > 0
    assert data["duration_seconds"] >= 0
    conv_dicts["chat"] = data["conversation_id"]


def test_real_chat_stream(live_client):
    resp = live_client.post(
        "/v1/chat/stream",
        json={"messages": [{"role": "user", "content": "Count from 1 to 3."}]},
        headers=_AUTH,
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    assert "data: [DONE]" in resp.text
    assert '"content"' in resp.text


def test_chat_persisted_to_history(live_client, conv_dicts):
    resp = live_client.post(
        "/v1/chat",
        json={"messages": [{"role": "user", "content": "Repeat after me: hello"}]},
        headers=_AUTH,
    )
    assert resp.status_code == 200
    conv_id = resp.json()["conversation_id"]

    history = live_client.get("/v1/chat/history", headers=_AUTH).json()
    ids = [c["id"] for c in history["conversations"]]
    assert conv_id in ids

    detail = live_client.get(f"/v1/chat/history/{conv_id}", headers=_AUTH)
    assert detail.status_code == 200
    roles = [m["role"] for m in detail.json()["messages"]]
    assert roles == ["user", "assistant"]


def test_logs_and_analytics_updated(live_client):
    resp = live_client.get("/v1/logs/stats", headers=_AUTH)
    assert resp.status_code == 200
    stats = resp.json()["stats"]
    assert stats["total_requests"] >= 1

    periods = live_client.get(
        "/v1/logs/costs/by-period?period=day", headers=_AUTH
    ).json()["data"]
    assert len(periods) >= 1


def test_metrics_endpoint(live_client):
    resp = live_client.get("/metrics")
    assert resp.status_code == 200
    assert "llm_request_total" in resp.text
    assert "llm_request_duration_seconds" in resp.text


def test_key_lifecycle_end_to_end(live_client):
    """Create a DB-managed key, then use the raw key for a real chat."""
    create = live_client.post("/v1/admin/keys", json={"name": "e2e-user"}, headers=_AUTH)
    assert create.status_code == 200
    raw_key = create.json()["raw_key"]

    # Rotate: revoke then confirm the revoked key no longer authenticates.
    key_id = create.json()["id"]
    live_client.delete(f"/v1/admin/keys/{key_id}", headers=_AUTH)

    revoked = live_client.post(
        "/v1/chat",
        json={"messages": [{"role": "user", "content": "should fail"}]},
        headers={"Authorization": f"Bearer {raw_key}"},
    )
    assert revoked.status_code == 403