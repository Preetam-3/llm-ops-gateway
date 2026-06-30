"""Tests for the /metrics endpoint."""


def test_metrics_endpoint(test_client):
    resp = test_client.get("/metrics")
    assert resp.status_code == 200
    # Prometheus exposition format
    content = resp.text
    assert "llm_request_total" in content
    assert "llm_request_duration_seconds" in content
    assert "llm_tokens_total" in content
    assert "llm_estimated_cost_dollars" in content
    assert "llm_rate_limited_total" in content
