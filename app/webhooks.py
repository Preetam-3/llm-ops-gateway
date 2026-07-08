"""Webhook notifications for gateway events (Slack-compatible)."""

import json
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_client: httpx.AsyncClient | None = None


def init_webhook_client() -> None:
    global _client
    if settings.webhook_url:
        _client = httpx.AsyncClient(timeout=10.0)
        logger.info("Webhook client initialized for %s", settings.webhook_url)
    else:
        _client = None


async def close_webhook_client() -> None:
    global _client
    if _client:
        await _client.aclose()
        _client = None


async def send_notification(event: str, message: str, fields: dict | None = None) -> bool:
    """Send a Slack-compatible webhook notification. Returns True on success."""
    if not _client or not settings.webhook_url:
        return False

    payload = {
        "text": f"*LLM Ops Gateway — {event}*\n{message}",
    }

    if fields:
        attachments = [{
            "color": get_color(event),
            "fields": [{"title": k, "value": str(v), "short": True} for k, v in fields.items()],
        }]
        payload["attachments"] = attachments

    try:
        resp = await _client.post(settings.webhook_url, json=payload)
        resp.raise_for_status()
        logger.info("Webhook sent: %s", event)
        return True
    except Exception as e:
        logger.warning("Webhook failed for %s: %s", event, e)
        return False


def get_color(event: str) -> str:
    if event == "error":
        return "danger"
    if event == "warning":
        return "warning"
    return "good"
