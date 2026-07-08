"""LLM provider for Anthropic's Messages API.

Normalizes responses to OpenAI-compatible shapes so routes stay clean.
"""

import json

import httpx

from app.providers.base import BaseLLMProvider

_ANTHROPIC_BASE = "https://api.anthropic.com/v1"
_ANTHROPIC_VERSION = "2023-06-01"


def _normalize_response(anthropic_resp: dict) -> dict:
    """Convert an Anthropic response to OpenAI-compatible shape."""
    content = ""
    blocks = anthropic_resp.get("content", [])
    if blocks:
        content = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")

    usage = anthropic_resp.get("usage", {})
    prompt_tokens = usage.get("input_tokens", 0)
    completion_tokens = usage.get("output_tokens", 0)

    return {
        "choices": [
            {
                "message": {
                    "role": anthropic_resp.get("role", "assistant"),
                    "content": content,
                }
            }
        ],
        "model": anthropic_resp.get("model", ""),
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }


class AnthropicProvider(BaseLLMProvider):
    """Client for Anthropic's Messages API."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str = _ANTHROPIC_BASE,
        timeout: float = 60.0,
        stream_timeout: float = 300.0,
    ) -> None:
        self.name = "anthropic"
        self.model = model
        self._stream_timeout = stream_timeout
        self.client = httpx.AsyncClient(
            base_url=base_url,
            headers={
                "x-api-key": api_key,
                "anthropic-version": _ANTHROPIC_VERSION,
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )

    async def chat_completion(self, messages: list[dict]) -> dict:
        """Send a non-streaming request to Anthropic and normalize the response."""
        payload = {
            "model": self.model,
            "max_tokens": 1024,
            "messages": messages,
        }
        response = await self.client.post("/messages", json=payload)
        response.raise_for_status()
        return _normalize_response(response.json())

    async def chat_completion_stream(self, messages: list[dict]):
        """Stream from Anthropic, yielding OpenAI-compatible chunk dicts."""
        payload = {
            "model": self.model,
            "max_tokens": 1024,
            "messages": messages,
            "stream": True,
        }
        async with self.client.stream(
            "POST",
            "/messages",
            json=payload,
            timeout=self._stream_timeout,
        ) as response:
            if not response.is_success:
                error_body = await response.aread()
                raise RuntimeError(
                    f"Anthropic API error {response.status_code}: {error_body.decode()}"
                )

            current_event = ""
            async for line in response.aiter_lines():
                line = line.strip()
                if not line:
                    current_event = ""
                    continue
                if line.startswith("event: "):
                    current_event = line[7:]
                    continue
                if line.startswith("data: "):
                    data_str = line[6:]
                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

                    event_type = data.get("type", current_event)

                    if event_type == "content_block_delta":
                        delta = data.get("delta", {})
                        if delta.get("type") == "text_delta":
                            text = delta.get("text", "")
                            if text:
                                yield {
                                    "choices": [
                                        {
                                            "delta": {"content": text},
                                            "index": data.get("index", 0),
                                        }
                                    ]
                                }

                    elif event_type == "content_block_start":
                        block = data.get("content_block", {})
                        if block.get("type") == "text":
                            text = block.get("text", "")
                            if text:
                                yield {
                                    "choices": [
                                        {
                                            "delta": {"content": text},
                                            "index": data.get("index", 0),
                                        }
                                    ]
                                }

                    elif event_type == "message_delta":
                        delta = data.get("delta", {})
                        stop_reason = delta.get("stop_reason")
                        if stop_reason:
                            yield {
                                "choices": [
                                    {
                                        "delta": {},
                                        "finish_reason": stop_reason,
                                        "index": 0,
                                    }
                                ]
                            }

                    elif event_type == "error":
                        error = data.get("error", {})
                        raise RuntimeError(
                            f"Anthropic streaming error: {error.get('message', str(data))}"
                        )

    async def close(self) -> None:
        await self.client.aclose()
