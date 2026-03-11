"""Health check endpoint for deployment monitoring."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from sportverein.auth.dependencies import get_db_session

router = APIRouter(tags=["health"])

VERSION = "1.0.0"


@router.get("/health")
async def health_check(
    session: AsyncSession = Depends(get_db_session),
) -> JSONResponse:
    """Return system health status including database connectivity."""
    try:
        await session.execute(text("SELECT 1"))
        return JSONResponse(
            status_code=200,
            content={"status": "ok", "version": VERSION, "database": "ok"},
        )
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={
                "status": "degraded",
                "version": VERSION,
                "database": "error",
                "detail": str(exc),
            },
        )
