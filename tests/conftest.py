"""Pytest fixtures for the LLM Ops Gateway tests."""

import os
from unittest.mock import AsyncMock, patch

os.environ["GATEWAY_API_KEY"] = "test-key"
os.environ["GROQ_API_KEY"] = "test-groq-key"
os.environ["DATABASE_PATH"] = ":memory:"

import pytest
from fastapi.testclient import TestClient
from app.database import close_db
from app.main import app
from app.middleware.rate_limit import rate_limiter


@pytest.fixture(autouse=True)
def db_lifecycle():
    """Clean up DB after each test (app lifespan handles init)."""
    yield
    close_db()


@pytest.fixture
def test_client(db_lifecycle):
    with patch.object(rate_limiter, "init", AsyncMock(return_value=None)):
        with TestClient(app) as client:
            yield client
