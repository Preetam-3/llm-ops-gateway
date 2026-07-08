"""LLM provider for OpenAI-compatible APIs (OpenAI, Groq, etc.)."""

import json

import httpx

from app.providers.base import BaseLLMProvider


class OpenAILikeProvider(BaseLLMProvider):
    """Client for any OpenAI-compatible chat completion API."""

    def __init__(
        self,
        *,
        name: str,
        base_url: str,
        api_key: str,
        model: str,
        timeout: float = 60.0,
        stream_timeout: float = 300.0,
    ) -> None:
        self.name = name
        self.model = model
        self._api_key = api_key
        self._stream_timeout = stream_timeout
        self.client = httpx.AsyncClient(
            base_url=base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )

    async def chat_completion(self, messages: list[dict]) -> dict:
        """Send a non-streaming chat completion request."""
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }
        response = await self.client.post("/chat/completions", json=payload)
        response.raise_for_status()
        return response.json()

    async def chat_completion_stream(self, messages: list[dict]):
        """Stream a chat completion. Yields parsed chunk dicts."""
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
        }
        async with self.client.stream(
            "POST",
            "/chat/completions",
            json=payload,
            timeout=self._stream_timeout,
        ) as response:
            if not response.is_success:
                error_body = await response.aread()
                raise RuntimeError(
                    f"{self.name} API error {response.status_code}: {error_body.decode()}"
                )
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        yield json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

    async def close(self) -> None:
        await self.client.aclose()
