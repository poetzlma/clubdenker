"""Finance router — bookings, invoices, payments, SEPA, and dunning."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from sportverein.api.schemas import (
    BeitragslaufRequest,
    BuchungCreate,
    BuchungListResponse,
    BuchungResponse,
    KassenstandResponse,
    KassenstandSphare,
    MahnungResponse,
    RechnungCreate,
    RechnungListResponse,
    RechnungResponse,
    SepaRequest,
    SepaResponse,
    ZahlungCreate,
    ZahlungResponse,
)
from sportverein.auth.dependencies import get_current_token, get_db_session
from sportverein.auth.models import ApiToken
from sportverein.services.beitraege import BeitraegeService
from sportverein.services.finanzen import FinanzenService

router = APIRouter(prefix="/api/finanzen", tags=["finanzen"])


def _buchung_to_response(b) -> BuchungResponse:
    return BuchungResponse(
        id=b.id,
        buchungsdatum=b.buchungsdatum,
        betrag=float(b.betrag),
        beschreibung=b.beschreibung,
        konto=b.konto,
        gegenkonto=b.gegenkonto,
        sphare=b.sphare.value if hasattr(b.sphare, "value") else str(b.sphare),
        mitglied_id=b.mitglied_id,
    )


def _rechnung_to_response(r) -> RechnungResponse:
    return RechnungResponse(
        id=r.id,
        rechnungsnummer=r.rechnungsnummer,
        mitglied_id=r.mitglied_id,
        betrag=float(r.betrag),
        beschreibung=r.beschreibung,
        rechnungsdatum=r.rechnungsdatum,
        faelligkeitsdatum=r.faelligkeitsdatum,
        status=r.status.value if hasattr(r.status, "value") else str(r.status),
    )


@router.get("/buchungen", response_model=BuchungListResponse)
async def list_bookings(
    sphare: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    mitglied_id: int | None = None,
    page: int = 1,
    page_size: int = 20,
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> BuchungListResponse:
    svc = FinanzenService(session)
    filters = {}
    if sphare:
        filters["sphare"] = sphare
    if date_from:
        filters["date_from"] = date_from
    if date_to:
        filters["date_to"] = date_to
    if mitglied_id:
        filters["mitglied_id"] = mitglied_id

    bookings, total = await svc.get_bookings(filters=filters or None, page=page, page_size=page_size)
    return BuchungListResponse(
        items=[_buchung_to_response(b) for b in bookings],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/buchungen", response_model=BuchungResponse, status_code=status.HTTP_201_CREATED)
async def create_booking(
    body: BuchungCreate,
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> BuchungResponse:
    svc = FinanzenService(session)
    try:
        buchung = await svc.create_booking(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await session.commit()
    return _buchung_to_response(buchung)


@router.get("/kassenstand", response_model=KassenstandResponse)
async def get_balance(
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> KassenstandResponse:
    svc = FinanzenService(session)
    by_sphere = await svc.get_balance_by_sphere()
    total = await svc.get_total_balance()
    return KassenstandResponse(
        by_sphere=[
            KassenstandSphare(sphare=k, betrag=float(v))
            for k, v in by_sphere.items()
        ],
        total=float(total),
    )


@router.post("/sepa", response_model=SepaResponse)
async def generate_sepa(
    body: SepaRequest,
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> SepaResponse:
    svc = FinanzenService(session)
    try:
        xml = await svc.generate_sepa_xml(body.rechnungen_ids)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return SepaResponse(xml=xml, count=len(body.rechnungen_ids))


@router.get("/rechnungen", response_model=RechnungListResponse)
async def list_invoices(
    rechnung_status: str | None = Query(None, alias="status"),
    mitglied_id: int | None = None,
    page: int = 1,
    page_size: int = 20,
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> RechnungListResponse:
    svc = FinanzenService(session)
    filters = {}
    if rechnung_status:
        filters["status"] = rechnung_status
    if mitglied_id:
        filters["mitglied_id"] = mitglied_id

    invoices, total = await svc.get_invoices(filters=filters or None, page=page, page_size=page_size)
    return RechnungListResponse(
        items=[_rechnung_to_response(r) for r in invoices],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/rechnungen", response_model=RechnungResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    body: RechnungCreate,
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> RechnungResponse:
    svc = FinanzenService(session)
    try:
        rechnung = await svc.create_invoice(
            mitglied_id=body.mitglied_id,
            betrag=Decimal(str(body.betrag)),
            beschreibung=body.beschreibung,
            faelligkeitsdatum=body.faelligkeitsdatum,
            rechnungsdatum=body.rechnungsdatum,
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await session.commit()
    return _rechnung_to_response(rechnung)


@router.post("/rechnungen/{rechnung_id}/zahlungen", response_model=ZahlungResponse, status_code=status.HTTP_201_CREATED)
async def record_payment(
    rechnung_id: int,
    body: ZahlungCreate,
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> ZahlungResponse:
    svc = FinanzenService(session)
    try:
        zahlung = await svc.record_payment(
            rechnung_id=rechnung_id,
            betrag=Decimal(str(body.betrag)),
            zahlungsart=body.zahlungsart,
            referenz=body.referenz,
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await session.commit()
    return ZahlungResponse(
        id=zahlung.id,
        rechnung_id=zahlung.rechnung_id,
        betrag=float(zahlung.betrag),
        zahlungsdatum=zahlung.zahlungsdatum,
        zahlungsart=zahlung.zahlungsart.value if hasattr(zahlung.zahlungsart, "value") else str(zahlung.zahlungsart),
        referenz=zahlung.referenz,
    )


@router.post("/beitragslaeufe", response_model=list[RechnungResponse], status_code=status.HTTP_201_CREATED)
async def run_fee_generation(
    body: BeitragslaufRequest,
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> list[RechnungResponse]:
    beitraege_svc = BeitraegeService(session)
    finanzen_svc = FinanzenService(session)

    fees = await beitraege_svc.calculate_all_fees(body.billing_year)
    created_invoices = []

    for fee in fees:
        if fee["prorata_betrag"] > 0:
            rechnung = await finanzen_svc.create_invoice(
                mitglied_id=fee["member_id"],
                betrag=fee["prorata_betrag"],
                beschreibung=f"Mitgliedsbeitrag {body.billing_year}",
                faelligkeitsdatum=date(body.billing_year, 3, 31),
            )
            created_invoices.append(rechnung)

    await session.commit()
    return [_rechnung_to_response(r) for r in created_invoices]


@router.get("/mahnungen", response_model=list[MahnungResponse])
async def get_dunning_candidates(
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> list[MahnungResponse]:
    svc = FinanzenService(session)
    overdue = await svc.get_overdue_invoices()
    return [
        MahnungResponse(
            id=r.id,
            rechnungsnummer=r.rechnungsnummer,
            mitglied_id=r.mitglied_id,
            betrag=float(r.betrag),
            beschreibung=r.beschreibung,
            rechnungsdatum=r.rechnungsdatum,
            faelligkeitsdatum=r.faelligkeitsdatum,
            status=r.status.value if hasattr(r.status, "value") else str(r.status),
        )
        for r in overdue
    ]
