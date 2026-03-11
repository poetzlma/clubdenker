"""Documents and Protokoll (meeting minutes) router."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from sportverein.api.schemas import (
    ProtokollCreate,
    ProtokollListResponse,
    ProtokollResponse,
    ProtokollUpdate,
)
from sportverein.auth.dependencies import get_current_token, get_db_session
from sportverein.auth.models import ApiToken
from sportverein.services.protokoll import ProtokollService

router = APIRouter(prefix="/api/dokumente", tags=["dokumente"])


def _protokoll_to_response(p) -> ProtokollResponse:  # type: ignore[no-untyped-def]
    return ProtokollResponse(
        id=p.id,
        titel=p.titel,
        datum=p.datum,
        inhalt=p.inhalt,
        typ=p.typ.value if hasattr(p.typ, "value") else str(p.typ),
        erstellt_von=p.erstellt_von,
        teilnehmer=p.teilnehmer,
        beschluesse=p.beschluesse,
        created_at=p.created_at,
    )


# ---------------------------------------------------------------------------
# Protokolle
# ---------------------------------------------------------------------------


@router.get("/protokolle", response_model=ProtokollListResponse)
async def list_protokolle(
    typ: str | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> ProtokollListResponse:
    svc = ProtokollService(session)
    try:
        items, total = await svc.list_protokolle(typ=typ, search=search, page=page, page_size=page_size)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return ProtokollListResponse(
        items=[_protokoll_to_response(p) for p in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/protokolle/{protokoll_id}", response_model=ProtokollResponse)
async def get_protokoll(
    protokoll_id: int,
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> ProtokollResponse:
    svc = ProtokollService(session)
    try:
        p = await svc.get_protokoll(protokoll_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _protokoll_to_response(p)


@router.post(
    "/protokolle",
    response_model=ProtokollResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_protokoll(
    body: ProtokollCreate,
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> ProtokollResponse:
    svc = ProtokollService(session)
    try:
        p = await svc.create_protokoll(
            titel=body.titel,
            datum=body.datum,
            inhalt=body.inhalt,
            typ=body.typ,
            erstellt_von=body.erstellt_von,
            teilnehmer=body.teilnehmer,
            beschluesse=body.beschluesse,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await session.commit()
    return _protokoll_to_response(p)


@router.put("/protokolle/{protokoll_id}", response_model=ProtokollResponse)
async def update_protokoll(
    protokoll_id: int,
    body: ProtokollUpdate,
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> ProtokollResponse:
    svc = ProtokollService(session)
    updates = body.model_dump(exclude_unset=True)
    try:
        p = await svc.update_protokoll(protokoll_id, **updates)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await session.commit()
    return _protokoll_to_response(p)


@router.delete("/protokolle/{protokoll_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_protokoll(
    protokoll_id: int,
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    svc = ProtokollService(session)
    try:
        await svc.delete_protokoll(protokoll_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await session.commit()
