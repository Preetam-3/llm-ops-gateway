from contextlib import asynccontextmanager
from fastapi import FastAPI
from prometheus_client import generate_latest
from fastapi.responses import PlainTextResponse

from app.middleware.rate_limit import rate_limiter
from app.proxy.groq_client import groq_client
from app.routes import health, chat


@asynccontextmanager
async def lifespan(app: FastAPI):
    await rate_limiter.init()
    yield
    await groq_client.close()


app = FastAPI(title="LLM Ops Gateway", lifespan=lifespan)

app.include_router(health.router)
app.include_router(chat.router)


@app.get("/metrics")
async def metrics():
    return PlainTextResponse(generate_latest(), media_type="text/plain; version=0.0.4")


@app.get("/")
async def root():
    return {"service": "llm-ops-gateway", "status": "running"}
