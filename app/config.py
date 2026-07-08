import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # Provider selection
    llm_provider: str = os.getenv("LLM_PROVIDER", "groq")  # groq | openai | anthropic
    llm_model: str = os.getenv("LLM_MODEL", "")  # overrides per-provider model if set

    # Groq
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_model: str = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

    # OpenAI
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o")

    # Anthropic
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

    # Gateway
    gateway_api_key: str = os.getenv("GATEWAY_API_KEY", "dev-key")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    max_requests_per_minute: int = int(os.getenv("MAX_REQUESTS_PER_MINUTE", "30"))
    max_requests_per_minute_per_ip: int = int(os.getenv("MAX_REQUESTS_PER_MINUTE_PER_IP", "60"))
    groq_base_url: str = "https://api.groq.com/openai/v1"
    provider_fallback: str = os.getenv("PROVIDER_FALLBACK", "")  # comma-separated, e.g. "groq,openai"

    # Caching
    cache_enabled: bool = os.getenv("CACHE_ENABLED", "true").lower() == "true"
    cache_ttl_seconds: int = int(os.getenv("CACHE_TTL_SECONDS", "300"))

    # Guardrails
    guardrails_enabled: bool = os.getenv("GUARDRAILS_ENABLED", "false").lower() == "true"
    guardrails_blocklist_path: str = os.getenv("GUARDRAILS_BLOCKLIST_PATH", "")

    # Persistence
    database_path: str = os.getenv("DATABASE_PATH", "gateway.db")


settings = Settings()
