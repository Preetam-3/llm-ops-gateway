"""Tests for webhook notifications."""
from unittest.mock import AsyncMock, patch

import pytest

from app.webhooks import close_webhook_client, init_webhook_client, send_notification


@pytest.mark.anyio
async def test_send_no_url():
    """Without a webhook URL, send_notification returns False silently."""
    init_webhook_client()  # no WEBHOOK_URL set
    result = await send_notification("test", "test message")
    assert result is False
    await close_webhook_client()


@pytest.mark.anyio
async def test_send_success():
    """With a URL, webhook POSTs successfully."""
    with patch("app.webhooks.settings.webhook_url", "https://hooks.example.com/hook"):
        init_webhook_client()
        with patch("app.webhooks._client") as mock_client:
            from unittest.mock import MagicMock
            mock_resp = MagicMock()
            mock_resp.raise_for_status.return_value = None
            mock_client.post = AsyncMock(return_value=mock_resp)

            result = await send_notification("test", "hello", {"key": "val"})
            assert result is True
            mock_client.post.assert_called_once()

        await close_webhook_client()


@pytest.mark.anyio
async def test_send_http_error():
    """When webhook returns error, send_notification returns False."""
    with patch("app.webhooks.settings.webhook_url", "https://hooks.example.com/hook"):
        init_webhook_client()
        with patch("app.webhooks._client") as mock_client:
            mock_client.post = AsyncMock(side_effect=Exception("HTTP 500"))

            result = await send_notification("error", "msg")
            assert result is False

        await close_webhook_client()
