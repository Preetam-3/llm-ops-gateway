import httpx
from app.config import settings


class GroqClient:
    """Async HTTP client for the Groq API (OpenAI-compatible)."""

    def __init__(self) -> None:
        self.base_url = settings.groq_base_url
        self.api_key = settings.groq_api_key
        self.model = settings.groq_model
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=60.0,
        )

    async def chat_completion(self, messages: list[dict]) -> dict:
        """Send a chat completion request to Groq."""
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }
        response = await self.client.post("/chat/completions", json=payload)
        response.raise_for_status()
        return response.json()

    async def close(self) -> None:
        await self.client.aclose()


groq_client = GroqClient()
