from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from prometheus_client import generate_latest

from app.cache import cache_clear, close_cache, init_cache
from app.config import settings
from app.database import close_db, init_db
from app.guardrails import init_guardrails
from app.middleware.auth import verify_admin_key
from app.middleware.rate_limit import rate_limiter
from app.providers.router import provider_router
from app.routes import health, chat, keys, logs

_ADMIN_HTML: str | None = None


def _load_admin_html() -> str:
    path = Path(__file__).resolve().parent.parent / "ui" / "admin.html"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return "<html><body><h1>Admin dashboard not found</h1></body></html>"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(settings.database_path)
    await rate_limiter.init()
    await provider_router.init()
    await init_cache()
    init_guardrails(
        blocklist_path=settings.guardrails_blocklist_path or None,
        check_prompts=settings.guardrails_enabled,
        check_responses=settings.guardrails_enabled,
    )
    yield
    await provider_router.close()
    await close_cache()
    close_db()


app = FastAPI(title="LLM Ops Gateway", lifespan=lifespan)

app.include_router(health.router)
app.include_router(chat.router)
app.include_router(keys.router)
app.include_router(logs.router)


@app.get("/admin")
async def admin_dashboard(request: Request):
    """Serve the admin dashboard HTML (protected by admin key)."""
    await verify_admin_key(request)
    global _ADMIN_HTML
    if _ADMIN_HTML is None:
        _ADMIN_HTML = _load_admin_html()
    return HTMLResponse(_ADMIN_HTML)


@app.post("/admin/cache/clear")
async def clear_cache(request: Request):
    """Clear all cached LLM responses (admin only)."""
    await verify_admin_key(request)
    count = await cache_clear()
    return {"status": "ok", "cleared": count, "note": "Cached LLM responses cleared"}


@app.get("/metrics")
async def metrics():
    return PlainTextResponse(generate_latest(), media_type="text/plain; version=0.0.4")


@app.get("/")
async def root():
    return {"service": "llm-ops-gateway", "status": "running"}
