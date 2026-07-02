import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    gateway_api_key: str = os.getenv("GATEWAY_API_KEY", "dev-key")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    groq_model: str = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    max_requests_per_minute: int = int(os.getenv("MAX_REQUESTS_PER_MINUTE", "30"))
    groq_base_url: str = "https://api.groq.com/openai/v1"


settings = Settings()
