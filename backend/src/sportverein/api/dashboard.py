"""Dashboard router — stats, recent activity, and role-specific views."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from sportverein.api.schemas import (
    ActivityItem,
    DashboardStats,
    EngagementAnalyticsResponse,
    RecentActivityResponse,
    SchatzmeisterDashboardResponse,
    SpartenleiterDashboardResponse,
    VorstandDashboardResponse,
)
from sportverein.auth.dependencies import get_current_token, get_db_session
from sportverein.auth.models import ApiToken
from sportverein.services.audit import AuditService
from sportverein.services.dashboard import DashboardService
from sportverein.services.finanzen import FinanzenService
from sportverein.services.mitglieder import MitgliederService

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def get_stats(
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> DashboardStats:
    svc = MitgliederService(session)
    stats = await svc.get_member_stats()
    fin_svc = FinanzenService(session)
    total_balance = await fin_svc.get_total_balance()
    by_sphere = await fin_svc.get_balance_by_sphere()
    return DashboardStats(
        total_active=stats["total_active"],
        total_passive=stats["total_passive"],
        new_this_month=stats["new_this_month"],
        by_department=stats["by_department"],
        financial_summary={
            "total_balance": float(total_balance),
            "by_sphere": {k: float(v) for k, v in by_sphere.items()},
        },
    )


@router.get("/recent-activity", response_model=RecentActivityResponse)
async def get_recent_activity(
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> RecentActivityResponse:
    audit_svc = AuditService(session)
    logs = await audit_svc.get_recent(limit=20)
    if not logs:
        return RecentActivityResponse(items=[])
    items = []
    for log in logs:
        items.append(
            ActivityItem(
                type=log.action,
                description=f"{log.action} {log.entity_type}"
                + (f" #{log.entity_id}" if log.entity_id else ""),
                timestamp=log.timestamp.isoformat() if log.timestamp else "",
            )
        )
    return RecentActivityResponse(items=items)


@router.get("/engagement", response_model=EngagementAnalyticsResponse)
async def get_engagement_analytics(
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> EngagementAnalyticsResponse:
    svc = DashboardService(session)
    data = await svc.get_engagement_analytics()
    return EngagementAnalyticsResponse(**data)


@router.get("/vorstand", response_model=VorstandDashboardResponse)
async def get_vorstand_dashboard(
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> VorstandDashboardResponse:
    svc = DashboardService(session)
    data = await svc.get_vorstand_dashboard()
    return VorstandDashboardResponse(**data)


@router.get("/schatzmeister", response_model=SchatzmeisterDashboardResponse)
async def get_schatzmeister_dashboard(
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> SchatzmeisterDashboardResponse:
    svc = DashboardService(session)
    data = await svc.get_schatzmeister_dashboard()
    return SchatzmeisterDashboardResponse(**data)


@router.get(
    "/spartenleiter/{abteilung}",
    response_model=SpartenleiterDashboardResponse,
)
async def get_spartenleiter_dashboard(
    abteilung: str,
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> SpartenleiterDashboardResponse:
    svc = DashboardService(session)
    try:
        data = await svc.get_spartenleiter_dashboard(abteilung)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return SpartenleiterDashboardResponse(**data)
