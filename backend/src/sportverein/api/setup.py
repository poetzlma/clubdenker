"""Setup router — CRUD for BeitragsKategorien and Abteilungen."""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from sportverein.api.audit_helper import log_audit
from sportverein.api.schemas import (
    AbteilungCreate,
    AbteilungResponse,
    AbteilungUpdate,
    BeitragsKategorieCreate,
    BeitragsKategorieResponse,
    BeitragsKategorieUpdate,
)
from sportverein.auth.dependencies import get_current_token, get_db_session
from sportverein.auth.models import ApiToken
from sportverein.services.beitraege import BeitraegeService
from sportverein.services.mitglieder import MitgliederService

router = APIRouter(prefix="/api/setup", tags=["setup"])


# ---------------------------------------------------------------------------
# BeitragsKategorien
# ---------------------------------------------------------------------------


def _kategorie_to_response(k) -> BeitragsKategorieResponse:
    return BeitragsKategorieResponse(
        id=k.id,
        name=k.name,
        jahresbeitrag=float(k.jahresbeitrag),
        beschreibung=k.beschreibung,
        created_at=k.created_at,
    )


@router.get("/beitragskategorien", response_model=list[BeitragsKategorieResponse])
async def list_categories(
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> list[BeitragsKategorieResponse]:
    svc = BeitraegeService(session)
    categories = await svc.get_categories()
    return [_kategorie_to_response(k) for k in categories]


@router.post(
    "/beitragskategorien",
    response_model=BeitragsKategorieResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_category(
    body: BeitragsKategorieCreate,
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> BeitragsKategorieResponse:
    svc = BeitraegeService(session)
    try:
        category = await svc.create_category(
            name=body.name,
            jahresbeitrag=Decimal(str(body.jahresbeitrag)),
            beschreibung=body.beschreibung,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await log_audit(
        session,
        user_id=_token.admin_user_id,
        action="create",
        entity_type="beitragskategorie",
        entity_id=category.id,
        details={"name": category.name},
    )
    await session.commit()
    return _kategorie_to_response(category)


@router.put(
    "/beitragskategorien/{category_id}",
    response_model=BeitragsKategorieResponse,
)
async def update_category(
    category_id: int,
    body: BeitragsKategorieUpdate,
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> BeitragsKategorieResponse:
    svc = BeitraegeService(session)
    kwargs: dict = {}
    if body.jahresbeitrag is not None:
        kwargs["jahresbeitrag"] = Decimal(str(body.jahresbeitrag))
    if body.beschreibung is not None:
        kwargs["beschreibung"] = body.beschreibung
    try:
        category = await svc.update_category(category_id, **kwargs)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await log_audit(
        session,
        user_id=_token.admin_user_id,
        action="update",
        entity_type="beitragskategorie",
        entity_id=category.id,
        details={"name": category.name},
    )
    await session.commit()
    return _kategorie_to_response(category)


@router.delete(
    "/beitragskategorien/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_category(
    category_id: int,
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    svc = BeitraegeService(session)
    try:
        await svc.delete_category(category_id)
    except ValueError as exc:
        detail = str(exc)
        if "nicht gefunden" in detail:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail) from exc
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail) from exc
    await log_audit(
        session,
        user_id=_token.admin_user_id,
        action="delete",
        entity_type="beitragskategorie",
        entity_id=category_id,
        details={},
    )
    await session.commit()


# ---------------------------------------------------------------------------
# Abteilungen
# ---------------------------------------------------------------------------


def _abteilung_to_response(a) -> AbteilungResponse:
    return AbteilungResponse(
        id=a.id,
        name=a.name,
        beschreibung=a.beschreibung,
        created_at=a.created_at,
    )


@router.get("/abteilungen", response_model=list[AbteilungResponse])
async def list_departments(
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> list[AbteilungResponse]:
    svc = MitgliederService(session)
    departments = await svc.get_departments()
    return [_abteilung_to_response(d) for d in departments]


@router.post(
    "/abteilungen",
    response_model=AbteilungResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_department(
    body: AbteilungCreate,
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> AbteilungResponse:
    svc = MitgliederService(session)
    try:
        dept = await svc.create_department(name=body.name, beschreibung=body.beschreibung)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await log_audit(
        session,
        user_id=_token.admin_user_id,
        action="create",
        entity_type="abteilung",
        entity_id=dept.id,
        details={"name": dept.name},
    )
    await session.commit()
    return _abteilung_to_response(dept)


@router.put("/abteilungen/{department_id}", response_model=AbteilungResponse)
async def update_department(
    department_id: int,
    body: AbteilungUpdate,
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> AbteilungResponse:
    svc = MitgliederService(session)
    kwargs: dict = {}
    if body.name is not None:
        kwargs["name"] = body.name
    if body.beschreibung is not None:
        kwargs["beschreibung"] = body.beschreibung
    try:
        dept = await svc.update_department(department_id, **kwargs)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await log_audit(
        session,
        user_id=_token.admin_user_id,
        action="update",
        entity_type="abteilung",
        entity_id=dept.id,
        details={"name": dept.name},
    )
    await session.commit()
    return _abteilung_to_response(dept)


@router.delete(
    "/abteilungen/{department_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_department(
    department_id: int,
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    svc = MitgliederService(session)
    try:
        await svc.delete_department(department_id)
    except ValueError as exc:
        detail = str(exc)
        if "nicht gefunden" in detail:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail) from exc
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail) from exc
    await log_audit(
        session,
        user_id=_token.admin_user_id,
        action="delete",
        entity_type="abteilung",
        entity_id=department_id,
        details={},
    )
    await session.commit()
