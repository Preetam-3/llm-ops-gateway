import hashlib

from fastapi import Request, HTTPException

from app.config import settings
from app.database import get_api_key_by_hash


async def verify_api_key(request: Request) -> None:
    """Accept either the admin key (env var) or a valid DB-managed key."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    api_key = auth_header.removeprefix("Bearer ")

    # Admin key (env var) — fast path
    if api_key == settings.gateway_api_key:
        return

    # DB-managed key — hash and look up
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    key_data = await get_api_key_by_hash(key_hash)
    if key_data is None or not key_data["is_active"]:
        raise HTTPException(status_code=403, detail="Invalid or revoked API key")


async def verify_admin_key(request: Request) -> None:
    """Only accept the admin key (env var) — for admin endpoints."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    api_key = auth_header.removeprefix("Bearer ")
    if api_key != settings.gateway_api_key:
        raise HTTPException(status_code=403, detail="Admin access required")
