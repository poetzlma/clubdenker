"""Agent workflow router — orchestrated business processes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from sportverein.api.schemas import (
    AufwandMonitorResponse,
    BeitragseinzugRequest,
    BeitragseinzugResponse,
    ComplianceMonitorResponse,
    MahnwesenResponse,
)
from sportverein.auth.dependencies import get_current_token, get_db_session
from sportverein.auth.models import ApiToken
from sportverein.services.agents import (
    AufwandMonitorAgent,
    BeitragseinzugAgent,
    ComplianceMonitorAgent,
    MahnwesenAgent,
)

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.post(
    "/beitragseinzug", response_model=BeitragseinzugResponse, status_code=status.HTTP_200_OK
)
async def run_beitragseinzug(
    body: BeitragseinzugRequest,
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> BeitragseinzugResponse:
    agent = BeitragseinzugAgent(session)
    try:
        result = await agent.run(body.year, body.month)
    except (ValueError, PermissionError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await session.commit()
    return BeitragseinzugResponse(**result)


@router.post("/mahnwesen", response_model=MahnwesenResponse, status_code=status.HTTP_200_OK)
async def run_mahnwesen(
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> MahnwesenResponse:
    agent = MahnwesenAgent(session)
    result = await agent.run()
    return MahnwesenResponse(**result)


@router.get("/aufwand-monitor", response_model=AufwandMonitorResponse)
async def run_aufwand_monitor(
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> AufwandMonitorResponse:
    agent = AufwandMonitorAgent(session)
    result = await agent.run()
    return AufwandMonitorResponse(**result)


@router.post(
    "/compliance-monitor", response_model=ComplianceMonitorResponse, status_code=status.HTTP_200_OK
)
async def run_compliance_monitor(
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> ComplianceMonitorResponse:
    agent = ComplianceMonitorAgent(session)
    result = await agent.run()
    return ComplianceMonitorResponse(**result)
