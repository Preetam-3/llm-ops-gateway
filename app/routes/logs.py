"""Request log search and statistics endpoints."""

from fastapi import APIRouter, Depends, Query, Request

from app.database import get_log_stats, search_request_logs
from app.middleware.auth import verify_admin_key

router = APIRouter(
    prefix="/v1",
    dependencies=[Depends(verify_admin_key)],
)


@router.get("/logs")
async def list_logs(
    request: Request,
    q: str | None = Query(None, description="Search in request/response body"),
    model: str | None = Query(None, description="Filter by model name"),
    status: str | None = Query(None, description="Filter by status (success/error)"),
    start_date: str | None = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: str | None = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    logs = await search_request_logs(
        q=q, model=model, status=status,
        start_date=start_date, end_date=end_date,
        limit=limit, offset=offset,
    )
    return {"logs": logs, "limit": limit, "offset": offset, "total": len(logs)}


@router.get("/logs/stats")
async def log_stats():
    stats = await get_log_stats()
    return {"stats": stats}
