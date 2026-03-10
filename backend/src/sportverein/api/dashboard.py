"""Dashboard router — stats and recent activity."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from sportverein.api.schemas import ActivityItem, DashboardStats, RecentActivityResponse
from sportverein.auth.dependencies import get_current_token, get_db_session
from sportverein.auth.models import ApiToken
from sportverein.services.mitglieder import MitgliederService

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def get_stats(
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> DashboardStats:
    svc = MitgliederService(session)
    stats = await svc.get_member_stats()
    return DashboardStats(
        total_active=stats["total_active"],
        total_passive=stats["total_passive"],
        new_this_month=stats["new_this_month"],
        by_department=stats["by_department"],
        financial_summary={},
    )


@router.get("/recent-activity", response_model=RecentActivityResponse)
async def get_recent_activity(
    _token: ApiToken = Depends(get_current_token),
) -> RecentActivityResponse:
    # Placeholder — will be wired up when activity tracking is implemented.
    return RecentActivityResponse(items=[
        ActivityItem(
            type="placeholder",
            description="Activity tracking coming soon",
            timestamp="2026-01-01T00:00:00Z",
        ),
    ])
