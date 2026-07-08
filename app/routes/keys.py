"""API key management endpoints (admin-only)."""

from fastapi import APIRouter, Depends, HTTPException, Request

from app.database import create_api_key, list_api_keys, revoke_api_key
from app.middleware.auth import verify_admin_key

router = APIRouter(
    prefix="/v1/admin",
    dependencies=[Depends(verify_admin_key)],
)


@router.post("/keys")
async def create_key(request: Request):
    body = await request.json()
    name = (body.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name field is required")
    key = await create_api_key(name)
    return {
        "id": key["id"],
        "raw_key": key["raw_key"],
        "name": key["name"],
        "prefix": key["prefix"],
        "warning": "Save this key — it will not be shown again.",
    }


@router.get("/keys")
async def list_keys():
    keys = await list_api_keys()
    return {"keys": keys}


@router.delete("/keys/{key_id}")
async def revoke_key(key_id: str):
    ok = await revoke_api_key(key_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Key not found or already revoked")
    return {"status": "revoked"}
