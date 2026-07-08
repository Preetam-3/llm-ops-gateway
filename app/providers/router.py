"""Provider router — creates and serves LLM providers with optional fallback."""

import logging

from app.config import settings
from app.providers.anthropic import AnthropicProvider
from app.providers.base import BaseLLMProvider
from app.providers.openai_like import OpenAILikeProvider

logger = logging.getLogger(__name__)


class ProviderRouter:
    """Manages provider lifecycle, selection, and fallback."""

    def __init__(self) -> None:
        self._providers: list[BaseLLMProvider] = []
        self._fallback_names: list[str] = []

    def get_provider(self) -> BaseLLMProvider:
        """Return the primary (first) provider instance."""
        if not self._providers:
            raise RuntimeError("Provider not initialized. Call init() first.")
        return self._providers[0]

    async def init(self) -> None:
        """Create all providers based on settings."""
        self._providers = _build_providers()
        self._fallback_names = _parse_fallback_names()
        logger.info(
            "Initialized %d provider(s): primary=%s, fallback=%s",
            len(self._providers),
            settings.llm_provider,
            self._fallback_names,
        )

    async def close(self) -> None:
        """Shut down all providers."""
        for p in self._providers:
            await p.close()
        self._providers = []

    async def chat_with_fallback(self, messages: list) -> dict:
        """Try primary provider, then fallbacks in order until one succeeds."""
        errors: list[str] = []

        # Primary provider (via get_provider so mocks work in tests)
        primary = self.get_provider()
        try:
            return await primary.chat_completion(messages)
        except Exception as e:
            msg = f"{primary.name}: {e}"
            errors.append(msg)
            logger.warning("Provider %s failed: %s", primary.name, e)

        # Configured fallback providers
        for provider in self._providers[1:]:
            try:
                return await provider.chat_completion(messages)
            except Exception as e:
                msg = f"{provider.name}: {e}"
                errors.append(msg)
                logger.warning("Provider %s failed: %s", provider.name, e)

        raise RuntimeError(
            f"All providers failed — {'; '.join(errors)}"
        )


def _parse_fallback_names() -> list[str]:
    """Parse comma-separated fallback list, excluding the primary provider."""
    raw = settings.provider_fallback.strip()
    if not raw:
        return []
    fallbacks = [p.strip() for p in raw.split(",") if p.strip()]
    # Remove primary from fallback list
    return [f for f in fallbacks if f != settings.llm_provider]


def _build_providers() -> list[BaseLLMProvider]:
    """Factory — returns list of all configured providers."""
    providers: list[BaseLLMProvider] = []

    def make(name: str) -> BaseLLMProvider | None:
        match name:
            case "groq":
                if not settings.groq_api_key:
                    logger.warning("Skipping groq: GROQ_API_KEY not set")
                    return None
                return OpenAILikeProvider(
                    name="groq",
                    base_url=settings.groq_base_url,
                    api_key=settings.groq_api_key,
                    model=settings.groq_model if not settings.llm_model else settings.llm_model,
                )
            case "openai":
                if not settings.openai_api_key:
                    logger.warning("Skipping openai: OPENAI_API_KEY not set")
                    return None
                return OpenAILikeProvider(
                    name="openai",
                    base_url="https://api.openai.com/v1",
                    api_key=settings.openai_api_key,
                    model=settings.openai_model if not settings.llm_model else settings.llm_model,
                )
            case "anthropic":
                if not settings.anthropic_api_key:
                    logger.warning("Skipping anthropic: ANTHROPIC_API_KEY not set")
                    return None
                return AnthropicProvider(
                    api_key=settings.anthropic_api_key,
                    model=settings.anthropic_model if not settings.llm_model else settings.llm_model,
                )
            case _:
                logger.warning("Unknown provider '%s' — skipping", name)
                return None

    primary = make(settings.llm_provider)
    if primary:
        providers.append(primary)
    else:
        raise ValueError(
            f"Primary provider '{settings.llm_provider}' could not be created. "
            f"Check that the required API key is set."
        )

    # Build fallback providers (if any)
    for name in _parse_fallback_names():
        p = make(name)
        if p:
            providers.append(p)

    return providers


provider_router = ProviderRouter()
