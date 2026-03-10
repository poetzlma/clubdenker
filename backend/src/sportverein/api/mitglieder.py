"""Members router — CRUD, department assignment, and DSGVO."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from sportverein.api.audit_helper import log_audit
from sportverein.api.schemas import (
    AbteilungResponse,
    DsgvoAuskunftResponse,
    EinwilligungRequest,
    KuendigenRequest,
    MitgliedAbteilungResponse,
    MitgliedListResponse,
    MitgliedResponse,
)
from sportverein.auth.dependencies import get_current_token, get_db_session
from sportverein.auth.models import ApiToken
from sportverein.models.mitglied import BeitragKategorie, MitgliedStatus
from sportverein.services.datenschutz import DatenschutzService
from sportverein.services.mitglieder import MitgliedCreate, MitgliedFilter, MitgliedUpdate, MitgliederService

router = APIRouter(prefix="/api/mitglieder", tags=["mitglieder"])


def _member_to_response(member, include_abteilungen: bool = True) -> MitgliedResponse:
    """Convert a Mitglied ORM object to the response model."""
    abteilungen = []
    if include_abteilungen:
        from sqlalchemy.orm import attributes
        state = attributes.instance_state(member)
        # Only access abteilungen if already loaded (avoid lazy load)
        if "abteilungen" in state.dict:
            for ma in member.abteilungen:
                abteilungen.append(
                    MitgliedAbteilungResponse(
                        abteilung_id=ma.abteilung_id,
                        abteilung_name=ma.abteilung.name if ma.abteilung else str(ma.abteilung_id),
                        beitrittsdatum=ma.beitrittsdatum,
                    )
                )
    return MitgliedResponse(
        id=member.id,
        mitgliedsnummer=member.mitgliedsnummer,
        vorname=member.vorname,
        nachname=member.nachname,
        email=member.email,
        telefon=member.telefon,
        geburtsdatum=member.geburtsdatum,
        strasse=member.strasse,
        plz=member.plz,
        ort=member.ort,
        eintrittsdatum=member.eintrittsdatum,
        austrittsdatum=member.austrittsdatum,
        status=member.status.value if hasattr(member.status, "value") else str(member.status),
        beitragskategorie=member.beitragskategorie.value if hasattr(member.beitragskategorie, "value") else str(member.beitragskategorie),
        notizen=member.notizen,
        abteilungen=abteilungen,
    )


# IMPORTANT: /abteilungen must come before /{member_id} to avoid route conflict
@router.get("/abteilungen", response_model=list[AbteilungResponse])
async def list_departments(
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> list[AbteilungResponse]:
    svc = MitgliederService(session)
    departments = await svc.get_departments()
    return [AbteilungResponse.model_validate(d) for d in departments]


@router.get("", response_model=MitgliedListResponse)
async def list_members(
    name: str | None = None,
    search: str | None = None,
    member_status: MitgliedStatus | None = Query(None, alias="status"),
    beitragskategorie: BeitragKategorie | None = None,
    abteilung_id: int | None = None,
    page: int = 1,
    page_size: int = 20,
    sort_by: str = "nachname",
    sort_order: Literal["asc", "desc"] = "asc",
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> MitgliedListResponse:
    svc = MitgliederService(session)
    filters = MitgliedFilter(
        name=name or search,
        status=member_status,
        beitragskategorie=beitragskategorie,
        abteilung_id=abteilung_id,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    members, total = await svc.search_members(filters)
    return MitgliedListResponse(
        items=[_member_to_response(m) for m in members],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=MitgliedResponse, status_code=status.HTTP_201_CREATED)
async def create_member(
    body: MitgliedCreate,
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> MitgliedResponse:
    svc = MitgliederService(session)
    try:
        member = await svc.create_member(body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await log_audit(
        session,
        user_id=_token.admin_user_id,
        action="create",
        entity_type="mitglied",
        entity_id=member.id,
        details={"vorname": member.vorname, "nachname": member.nachname},
    )
    await session.commit()
    # Re-fetch with eager-loaded relationships
    refreshed = await svc.get_member(member.id)
    assert refreshed is not None  # just created, must exist
    return _member_to_response(refreshed)


@router.get("/{member_id}", response_model=MitgliedResponse)
async def get_member(
    member_id: int,
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> MitgliedResponse:
    svc = MitgliederService(session)
    member = await svc.get_member(member_id)
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    return _member_to_response(member)


@router.put("/{member_id}", response_model=MitgliedResponse)
async def update_member(
    member_id: int,
    body: MitgliedUpdate,
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> MitgliedResponse:
    svc = MitgliederService(session)
    try:
        await svc.update_member(member_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await log_audit(
        session,
        user_id=_token.admin_user_id,
        action="update",
        entity_type="mitglied",
        entity_id=member_id,
        details=body.model_dump(exclude_unset=True),
    )
    await session.commit()
    # Re-fetch with abteilungen loaded
    refreshed = await svc.get_member(member_id)
    assert refreshed is not None  # just updated, must exist
    return _member_to_response(refreshed)


@router.post("/{member_id}/kuendigen", response_model=MitgliedResponse)
async def cancel_membership(
    member_id: int,
    body: KuendigenRequest | None = None,
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> MitgliedResponse:
    svc = MitgliederService(session)
    austrittsdatum = body.austrittsdatum if body else None
    try:
        await svc.cancel_member(member_id, austrittsdatum=austrittsdatum)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await log_audit(
        session,
        user_id=_token.admin_user_id,
        action="delete",
        entity_type="mitglied",
        entity_id=member_id,
        details={"austrittsdatum": str(austrittsdatum)},
    )
    await session.commit()
    refreshed = await svc.get_member(member_id)
    assert refreshed is not None  # just cancelled, must exist
    return _member_to_response(refreshed)


@router.post("/{member_id}/abteilungen/{abteilung_id}", status_code=status.HTTP_201_CREATED)
async def assign_department(
    member_id: int,
    abteilung_id: int,
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    svc = MitgliederService(session)
    try:
        assoc = await svc.assign_department(member_id, abteilung_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await session.commit()
    return {"mitglied_id": assoc.mitglied_id, "abteilung_id": assoc.abteilung_id}


@router.delete("/{member_id}/abteilungen/{abteilung_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_department(
    member_id: int,
    abteilung_id: int,
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    svc = MitgliederService(session)
    ok = await svc.remove_department(member_id, abteilung_id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Department assignment not found"
        )
    await session.commit()


# ---------------------------------------------------------------------------
# DSGVO endpoints
# ---------------------------------------------------------------------------


@router.get("/{member_id}/datenschutz", response_model=DsgvoAuskunftResponse)
async def get_dsgvo_data(
    member_id: int,
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> DsgvoAuskunftResponse:
    svc = DatenschutzService(session)
    try:
        data = await svc.generate_auskunft(member_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await log_audit(
        session,
        user_id=_token.admin_user_id,
        action="export",
        entity_type="mitglied",
        entity_id=member_id,
        details={"type": "dsgvo_auskunft"},
    )
    await session.commit()
    return DsgvoAuskunftResponse(**data)


@router.delete("/{member_id}/dsgvo-loeschen")
async def dsgvo_delete_member(
    member_id: int,
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """DSGVO-Datenlöschung: Anonymisiert personenbezogene Daten eines Mitglieds."""
    svc = DatenschutzService(session)
    try:
        member = await svc.delete_member_data(member_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await log_audit(
        session,
        user_id=_token.admin_user_id,
        action="dsgvo_loeschung",
        entity_type="mitglied",
        entity_id=member_id,
        details={"type": "dsgvo_anonymisierung"},
    )
    await session.commit()
    return {
        "mitglied_id": member.id,
        "geloescht_am": member.geloescht_am.isoformat() if member.geloescht_am else None,
        "message": "Personenbezogene Daten wurden DSGVO-konform anonymisiert.",
    }


@router.post("/{member_id}/einwilligung")
async def set_consent(
    member_id: int,
    body: EinwilligungRequest,
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    svc = DatenschutzService(session)
    try:
        member = await svc.set_consent(member_id, body.consent)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await log_audit(
        session,
        user_id=_token.admin_user_id,
        action="update",
        entity_type="mitglied",
        entity_id=member_id,
        details={"dsgvo_einwilligung": body.consent},
    )
    await session.commit()
    return {
        "member_id": member.id,
        "dsgvo_einwilligung": member.dsgvo_einwilligung,
        "einwilligung_datum": member.einwilligung_datum.isoformat() if member.einwilligung_datum else None,
    }
