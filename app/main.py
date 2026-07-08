from contextlib import asynccontextmanager
from fastapi import FastAPI
from prometheus_client import generate_latest
from fastapi.responses import PlainTextResponse

from app.config import settings
from app.database import close_db, init_db
from app.middleware.rate_limit import rate_limiter
from app.providers.router import provider_router
from app.routes import health, chat, keys, logs


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(settings.database_path)
    await rate_limiter.init()
    await provider_router.init()
    yield
    await provider_router.close()
    close_db()


app = FastAPI(title="LLM Ops Gateway", lifespan=lifespan)

app.include_router(health.router)
app.include_router(chat.router)
app.include_router(keys.router)
app.include_router(logs.router)


@app.get("/metrics")
async def metrics():
    return PlainTextResponse(generate_latest(), media_type="text/plain; version=0.0.4")


@app.get("/")
async def root():
    return {"service": "llm-ops-gateway", "status": "running"}
