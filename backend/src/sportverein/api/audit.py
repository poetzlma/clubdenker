"""Audit log router."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from sportverein.api.schemas import AuditLogListResponse, AuditLogResponse
from sportverein.auth.dependencies import get_current_token, get_db_session
from sportverein.auth.models import ApiToken
from sportverein.services.audit import AuditService

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("", response_model=AuditLogListResponse)
async def list_audit_logs(
    entity_type: str | None = None,
    entity_id: int | None = None,
    user_id: int | None = None,
    action: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = 1,
    page_size: int = 20,
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> AuditLogListResponse:
    svc = AuditService(session)
    filters: dict = {}
    if entity_type:
        filters["entity_type"] = entity_type
    if entity_id:
        filters["entity_id"] = entity_id
    if user_id:
        filters["user_id"] = user_id
    if action:
        filters["action"] = action
    if date_from:
        filters["date_from"] = date_from
    if date_to:
        filters["date_to"] = date_to

    logs, total = await svc.get_logs(filters=filters or None, page=page, page_size=page_size)
    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/recent", response_model=list[AuditLogResponse])
async def get_recent_audit(
    limit: int = Query(default=20, le=100),
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> list[AuditLogResponse]:
    svc = AuditService(session)
    logs = await svc.get_recent(limit=limit)
    return [AuditLogResponse.model_validate(log) for log in logs]
