"""Pytest fixtures for the LLM Ops Gateway tests."""

import os
from unittest.mock import AsyncMock, patch

os.environ["GATEWAY_API_KEY"] = "test-key"
os.environ["GROQ_API_KEY"] = "test-groq-key"

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.middleware.rate_limit import rate_limiter


@pytest.fixture
def test_client():
    with patch.object(rate_limiter, "init", AsyncMock(return_value=None)):
        with TestClient(app) as client:
            yield client
