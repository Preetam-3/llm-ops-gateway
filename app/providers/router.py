"""Provider router — creates and serves the right LLM provider based on config."""

from app.config import settings
from app.providers.anthropic import AnthropicProvider
from app.providers.base import BaseLLMProvider
from app.providers.openai_like import OpenAILikeProvider


class ProviderRouter:
    """Manages provider lifecycle and selection."""

    def __init__(self) -> None:
        self._provider: BaseLLMProvider | None = None

    def get_provider(self) -> BaseLLMProvider:
        """Return the active provider instance."""
        if self._provider is None:
            raise RuntimeError("Provider not initialized. Call init() first.")
        return self._provider

    async def init(self) -> None:
        """Create the provider instance based on settings."""
        self._provider = _build_provider()

    async def close(self) -> None:
        """Shut down the active provider."""
        if self._provider is not None:
            await self._provider.close()
            self._provider = None


def _build_provider() -> BaseLLMProvider:
    """Factory — reads settings and returns the correct provider."""
    match settings.llm_provider:
        case "groq":
            return OpenAILikeProvider(
                name="groq",
                base_url="https://api.groq.com/openai/v1",
                api_key=settings.groq_api_key,
                model=settings.groq_model if not settings.llm_model else settings.llm_model,
            )
        case "openai":
            return OpenAILikeProvider(
                name="openai",
                base_url="https://api.openai.com/v1",
                api_key=settings.openai_api_key,
                model=settings.openai_model if not settings.llm_model else settings.llm_model,
            )
        case "anthropic":
            return AnthropicProvider(
                api_key=settings.anthropic_api_key,
                model=settings.anthropic_model if not settings.llm_model else settings.llm_model,
            )
        case _:
            raise ValueError(
                f"Unknown provider '{settings.llm_provider}'. "
                f"Choose from: groq, openai, anthropic"
            )


provider_router = ProviderRouter()
