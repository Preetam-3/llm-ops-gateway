"""Abstract base class for LLM providers.

All providers normalize responses to OpenAI-compatible shapes so routes
don't need to know which provider is behind them.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator


class BaseLLMProvider(ABC):
    """Interface every LLM provider must implement."""

    model: str

    @abstractmethod
    async def chat_completion(self, messages: list[dict]) -> dict:
        """Non-streaming chat completion.

        Returns a dict in OpenAI-compatible shape:
            {"choices": [{"message": {"content": "..."}}],
             "model": "...",
             "usage": {"prompt_tokens": N, "completion_tokens": N, "total_tokens": N}}
        """
        ...

    @abstractmethod
    async def chat_completion_stream(
        self, messages: list[dict]
    ) -> AsyncGenerator[dict, None]:
        """Streaming chat completion.

        Yields chunk dicts in OpenAI-compatible shape:
            {"choices": [{"delta": {"content": "..."}, "index": 0}]}
        Final chunk has finish_reason instead of content:
            {"choices": [{"delta": {}, "finish_reason": "stop", "index": 0}]}
        """
        ...
        if False:
            yield  # make generator-returning happy  # pragma: no cover

    @abstractmethod
    async def close(self) -> None:
        """Release any resources (HTTP clients, etc.)."""
        ...
