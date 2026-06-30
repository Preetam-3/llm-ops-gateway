from app.config import settings
from fastapi import Request, HTTPException


async def verify_api_key(request: Request) -> None:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    api_key = auth_header.removeprefix("Bearer ")
    if api_key != settings.gateway_api_key:
        raise HTTPException(status_code=403, detail="Invalid API key")
