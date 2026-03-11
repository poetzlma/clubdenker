"""Training and attendance router."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from sportverein.api.schemas import (
    AnwesenheitCreate,
    AnwesenheitResponse,
    AnwesenheitStatistik,
    MitgliedAnwesenheitResponse,
    TrainerLizenzCreate,
    TrainerLizenzResponse,
    TrainingsgruppeCreate,
    TrainingsgruppeResponse,
    TrainingsgruppeUpdate,
)
from sportverein.auth.dependencies import get_current_token, get_db_session
from sportverein.auth.models import ApiToken
from sportverein.models.training import Lizenztyp, Wochentag
from sportverein.services.training import TrainingService

router = APIRouter(prefix="/api/training", tags=["training"])


def _gruppe_to_response(g) -> TrainingsgruppeResponse:  # type: ignore[no-untyped-def]
    return TrainingsgruppeResponse(
        id=g.id,
        name=g.name,
        abteilung_id=g.abteilung_id,
        trainer=g.trainer,
        wochentag=g.wochentag.value if hasattr(g.wochentag, "value") else str(g.wochentag),
        uhrzeit=g.uhrzeit,
        dauer_minuten=g.dauer_minuten,
        max_teilnehmer=g.max_teilnehmer,
        ort=g.ort,
        aktiv=g.aktiv,
        created_at=g.created_at,
    )


def _anwesenheit_to_response(a) -> AnwesenheitResponse:  # type: ignore[no-untyped-def]
    return AnwesenheitResponse(
        id=a.id,
        trainingsgruppe_id=a.trainingsgruppe_id,
        mitglied_id=a.mitglied_id,
        datum=a.datum,
        anwesend=a.anwesend,
        notiz=a.notiz,
        created_at=a.created_at,
    )


# ---------------------------------------------------------------------------
# Trainingsgruppen
# ---------------------------------------------------------------------------


@router.get("/gruppen", response_model=list[TrainingsgruppeResponse])
async def list_trainingsgruppen(
    abteilung_id: int | None = None,
    aktiv: bool | None = Query(True),
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> list[TrainingsgruppeResponse]:
    svc = TrainingService(session)
    gruppen = await svc.list_trainingsgruppen(abteilung_id=abteilung_id, aktiv=aktiv)
    return [_gruppe_to_response(g) for g in gruppen]


@router.post(
    "/gruppen",
    response_model=TrainingsgruppeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_trainingsgruppe(
    body: TrainingsgruppeCreate,
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> TrainingsgruppeResponse:
    svc = TrainingService(session)
    try:
        wochentag = Wochentag(body.wochentag)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ungültiger Wochentag: {body.wochentag}. Erlaubt: {', '.join(w.value for w in Wochentag)}",
        )
    try:
        gruppe = await svc.create_trainingsgruppe(
            name=body.name,
            abteilung_id=body.abteilung_id,
            wochentag=wochentag,
            uhrzeit=body.uhrzeit,
            trainer=body.trainer,
            dauer_minuten=body.dauer_minuten,
            max_teilnehmer=body.max_teilnehmer,
            ort=body.ort,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await session.commit()
    return _gruppe_to_response(gruppe)


@router.put("/gruppen/{gruppe_id}", response_model=TrainingsgruppeResponse)
async def update_trainingsgruppe(
    gruppe_id: int,
    body: TrainingsgruppeUpdate,
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> TrainingsgruppeResponse:
    svc = TrainingService(session)
    updates = body.model_dump(exclude_unset=True)
    if "wochentag" in updates and updates["wochentag"] is not None:
        try:
            updates["wochentag"] = Wochentag(updates["wochentag"])
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ungültiger Wochentag: {updates['wochentag']}. Erlaubt: {', '.join(w.value for w in Wochentag)}",
            )
    try:
        gruppe = await svc.update_trainingsgruppe(gruppe_id, **updates)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await session.commit()
    return _gruppe_to_response(gruppe)


@router.delete("/gruppen/{gruppe_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trainingsgruppe(
    gruppe_id: int,
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    svc = TrainingService(session)
    try:
        await svc.delete_trainingsgruppe(gruppe_id)
    except ValueError as exc:
        # Distinguish "not found" from "has attendance records"
        code = status.HTTP_404_NOT_FOUND if "nicht gefunden" in str(exc) else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=str(exc)) from exc
    await session.commit()


# ---------------------------------------------------------------------------
# Anwesenheit
# ---------------------------------------------------------------------------


@router.post(
    "/anwesenheit",
    response_model=list[AnwesenheitResponse],
    status_code=status.HTTP_201_CREATED,
)
async def record_anwesenheit(
    body: AnwesenheitCreate,
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> list[AnwesenheitResponse]:
    svc = TrainingService(session)
    teilnehmer_dicts = [t.model_dump() for t in body.teilnehmer]
    try:
        records = await svc.record_anwesenheit(
            trainingsgruppe_id=body.trainingsgruppe_id,
            datum=body.datum,
            teilnehmer=teilnehmer_dicts,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await session.commit()
    return [_anwesenheit_to_response(r) for r in records]


@router.get("/anwesenheit", response_model=list[AnwesenheitResponse])
async def get_anwesenheit(
    gruppe_id: int | None = None,
    mitglied_id: int | None = None,
    datum_von: date | None = None,
    datum_bis: date | None = None,
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> list[AnwesenheitResponse]:
    svc = TrainingService(session)
    records = await svc.get_anwesenheit(
        trainingsgruppe_id=gruppe_id,
        mitglied_id=mitglied_id,
        datum_von=datum_von,
        datum_bis=datum_bis,
    )
    return [_anwesenheit_to_response(r) for r in records]


@router.get("/anwesenheit/statistik/{abteilung_id}", response_model=AnwesenheitStatistik)
async def get_anwesenheit_statistik(
    abteilung_id: int,
    wochen: int = Query(12, ge=1, le=52),
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> AnwesenheitStatistik:
    svc = TrainingService(session)
    stats = await svc.get_anwesenheit_statistik(abteilung_id, wochen=wochen)
    return AnwesenheitStatistik(**stats)


@router.get(
    "/anwesenheit/mitglied/{mitglied_id}",
    response_model=MitgliedAnwesenheitResponse,
)
async def get_mitglied_anwesenheit(
    mitglied_id: int,
    wochen: int = Query(12, ge=1, le=52),
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> MitgliedAnwesenheitResponse:
    svc = TrainingService(session)
    stats = await svc.get_mitglied_anwesenheit(mitglied_id, wochen=wochen)
    return MitgliedAnwesenheitResponse(**stats)


# ---------------------------------------------------------------------------
# Trainer-Lizenzen
# ---------------------------------------------------------------------------


def _lizenz_to_response(liz) -> TrainerLizenzResponse:  # type: ignore[no-untyped-def]
    return TrainerLizenzResponse(
        id=liz.id,
        mitglied_id=liz.mitglied_id,
        lizenztyp=liz.lizenztyp.value if hasattr(liz.lizenztyp, "value") else str(liz.lizenztyp),
        bezeichnung=liz.bezeichnung,
        ausstellungsdatum=liz.ausstellungsdatum,
        ablaufdatum=liz.ablaufdatum,
        lizenznummer=liz.lizenznummer,
        ausstellende_stelle=liz.ausstellende_stelle,
        created_at=liz.created_at,
    )


@router.get("/lizenzen", response_model=list[TrainerLizenzResponse])
async def list_lizenzen(
    mitglied_id: int | None = None,
    expired: bool | None = None,
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> list[TrainerLizenzResponse]:
    svc = TrainingService(session)
    lizenzen = await svc.list_licenses(mitglied_id=mitglied_id, expired=expired)
    return [_lizenz_to_response(liz) for liz in lizenzen]


@router.post(
    "/lizenzen",
    response_model=TrainerLizenzResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_lizenz(
    body: TrainerLizenzCreate,
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> TrainerLizenzResponse:
    svc = TrainingService(session)
    try:
        lizenztyp = Lizenztyp(body.lizenztyp)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ungültiger Lizenztyp: {body.lizenztyp}. Erlaubt: {', '.join(lt.value for lt in Lizenztyp)}",
        )
    try:
        lizenz = await svc.create_license(
            mitglied_id=body.mitglied_id,
            lizenztyp=lizenztyp,
            bezeichnung=body.bezeichnung,
            ausstellungsdatum=body.ausstellungsdatum,
            ablaufdatum=body.ablaufdatum,
            lizenznummer=body.lizenznummer,
            ausstellende_stelle=body.ausstellende_stelle,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await session.commit()
    return _lizenz_to_response(lizenz)


@router.get("/lizenzen/expiring", response_model=list[TrainerLizenzResponse])
async def get_expiring_lizenzen(
    days: int = Query(90, ge=1, le=365),
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> list[TrainerLizenzResponse]:
    svc = TrainingService(session)
    lizenzen = await svc.get_expiring_licenses(days=days)
    return [_lizenz_to_response(liz) for liz in lizenzen]


@router.delete("/lizenzen/{lizenz_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lizenz(
    lizenz_id: int,
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    svc = TrainingService(session)
    try:
        await svc.delete_license(lizenz_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await session.commit()
