"""Finance router — bookings, invoices, payments, SEPA, and dunning."""

from __future__ import annotations

import io
import zipfile
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import extract, select
from sqlalchemy.ext.asyncio import AsyncSession

from sportverein.api.audit_helper import log_audit
from sportverein.api.schemas import (
    BeitragslaufRequest,
    BuchungCreate,
    BuchungListResponse,
    BuchungResponse,
    EingangsrechnungDetailResponse,
    EingangsrechnungListResponse,
    EingangsrechnungResponse,
    EingangsrechnungStatusUpdate,
    EingangsrechnungUploadResponse,
    EuerReportResponse,
    KassenstandResponse,
    KassenstandSphare,
    KostenstelleBudgetResponse,
    KostenstelleCreate,
    KostenstelleResponse,
    KostenstelleUpdate,
    LeistungsverrechnungRequest,
    LeistungsverrechnungResponse,
    MahnungResponse,
    RechnungCreate,
    RechnungListResponse,
    RechnungResponse,
    RechnungspositionResponse,
    RechnungTemplatePositionResponse,
    RechnungTemplateResponse,
    SepaMandatCreate,
    SepaMandatListResponse,
    SepaMandatResponse,
    SepaMandatUpdate,
    SepaRequest,
    SepaResponse,
    SkontoInfoResponse,
    StornoRequest,
    VereinsstammdatenResponse,
    VereinsstammdatenUpdate,
    VersandRequest,
    ZahlungCreate,
    ZahlungResponse,
)
from sportverein.auth.dependencies import get_current_token, get_db_session
from sportverein.auth.models import ApiToken
from sportverein.models.finanzen import Rechnung
from sportverein.services.beitraege import BeitraegeService
from sportverein.services.finanzen import FinanzenService
from sportverein.services.rechnung_pdf import RechnungPdfService
from sportverein.services.rechnung_templates import RechnungTemplateService
from sportverein.services.zugferd import ZugferdService

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
    positionen = []
    # Only include positionen if they were eagerly loaded (avoid lazy load in async)
    from sqlalchemy.orm import attributes
    pos_state = attributes.instance_state(r)
    if "positionen" in pos_state.dict:
        for p in r.positionen:
            positionen.append(RechnungspositionResponse(
                id=p.id,
                rechnung_id=p.rechnung_id,
                position_nr=p.position_nr,
                beschreibung=p.beschreibung,
                menge=float(p.menge),
                einheit=p.einheit,
                einzelpreis_netto=float(p.einzelpreis_netto),
                steuersatz=float(p.steuersatz),
                steuerbefreiungsgrund=p.steuerbefreiungsgrund,
                gesamtpreis_netto=float(p.gesamtpreis_netto),
                gesamtpreis_steuer=float(p.gesamtpreis_steuer),
                gesamtpreis_brutto=float(p.gesamtpreis_brutto),
                kostenstelle_id=p.kostenstelle_id,
            ))

    return RechnungResponse(
        id=r.id,
        rechnungsnummer=r.rechnungsnummer,
        mitglied_id=r.mitglied_id,
        betrag=float(r.betrag),
        beschreibung=r.beschreibung,
        rechnungsdatum=r.rechnungsdatum,
        faelligkeitsdatum=r.faelligkeitsdatum,
        status=r.status.value if hasattr(r.status, "value") else str(r.status),
        rechnungstyp=r.rechnungstyp.value if hasattr(r, "rechnungstyp") and r.rechnungstyp else None,
        mahnstufe=r.mahnstufe if hasattr(r, "mahnstufe") else 0,
        empfaenger_typ=r.empfaenger_typ.value if hasattr(r, "empfaenger_typ") and r.empfaenger_typ else None,
        empfaenger_name=getattr(r, "empfaenger_name", None),
        empfaenger_strasse=getattr(r, "empfaenger_strasse", None),
        empfaenger_plz=getattr(r, "empfaenger_plz", None),
        empfaenger_ort=getattr(r, "empfaenger_ort", None),
        empfaenger_ust_id=getattr(r, "empfaenger_ust_id", None),
        summe_netto=float(r.summe_netto) if hasattr(r, "summe_netto") and r.summe_netto is not None else None,
        summe_steuer=float(r.summe_steuer) if hasattr(r, "summe_steuer") and r.summe_steuer is not None else None,
        bezahlt_betrag=float(r.bezahlt_betrag) if hasattr(r, "bezahlt_betrag") and r.bezahlt_betrag is not None else None,
        offener_betrag=float(r.offener_betrag) if hasattr(r, "offener_betrag") and r.offener_betrag is not None else None,
        leistungsdatum=getattr(r, "leistungsdatum", None),
        leistungszeitraum_von=getattr(r, "leistungszeitraum_von", None),
        leistungszeitraum_bis=getattr(r, "leistungszeitraum_bis", None),
        sphaere=getattr(r, "sphaere", None),
        steuerhinweis_text=getattr(r, "steuerhinweis_text", None),
        zahlungsziel_tage=getattr(r, "zahlungsziel_tage", None),
        verwendungszweck=getattr(r, "verwendungszweck", None),
        storno_von_id=getattr(r, "storno_von_id", None),
        loeschdatum=getattr(r, "loeschdatum", None),
        gestellt_am=getattr(r, "gestellt_am", None),
        bezahlt_am=getattr(r, "bezahlt_am", None),
        format=r.format.value if hasattr(r, "format") and r.format else None,
        skonto_prozent=float(r.skonto_prozent) if getattr(r, "skonto_prozent", None) is not None else None,
        skonto_frist_tage=getattr(r, "skonto_frist_tage", None),
        skonto_betrag=float(r.skonto_betrag) if getattr(r, "skonto_betrag", None) is not None else None,
        versand_kanal=getattr(r, "versand_kanal", None),
        versendet_am=getattr(r, "versendet_am", None),
        versendet_an=getattr(r, "versendet_an", None),
        positionen=positionen,
    )


# -- Rechnungsvorlagen (templates) — must come before /rechnungen/{id} ------


def _template_to_response(t: dict) -> RechnungTemplateResponse:
    positionen = []
    for p in t.get("positionen", []):
        positionen.append(RechnungTemplatePositionResponse(
            beschreibung=p.get("beschreibung", ""),
            menge=p.get("menge", 1),
            einheit=p.get("einheit", "×"),
            einzelpreis_netto=p.get("einzelpreis_netto"),
            steuersatz=p.get("steuersatz", 0),
            steuerbefreiungsgrund=p.get("steuerbefreiungsgrund"),
            platzhalter=p.get("platzhalter"),
        ))
    return RechnungTemplateResponse(
        id=t["id"],
        name=t["name"],
        beschreibung=t["beschreibung"],
        rechnungstyp=t["rechnungstyp"],
        sphaere=t.get("sphaere"),
        empfaenger_typ=t.get("empfaenger_typ"),
        steuerhinweis_text=t.get("steuerhinweis_text"),
        zahlungsziel_tage=t["zahlungsziel_tage"],
        positionen=positionen,
    )


@router.get("/rechnungen/vorlagen", response_model=list[RechnungTemplateResponse])
async def list_rechnung_templates(
    _token: ApiToken = Depends(get_current_token),
) -> list[RechnungTemplateResponse]:
    """Return all available invoice templates."""
    svc = RechnungTemplateService()
    templates = svc.get_templates()
    return [_template_to_response(t) for t in templates]


@router.get("/rechnungen/vorlagen/{template_id}", response_model=RechnungTemplateResponse)
async def get_rechnung_template(
    template_id: str,
    _token: ApiToken = Depends(get_current_token),
) -> RechnungTemplateResponse:
    """Return a single invoice template by ID."""
    svc = RechnungTemplateService()
    template = svc.get_template(template_id)
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vorlage '{template_id}' nicht gefunden.",
        )
    return _template_to_response(template)


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
    filters: dict[str, str | date | int] = {}
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
    await log_audit(
        session,
        user_id=_token.admin_user_id,
        action="create",
        entity_type="buchung",
        entity_id=buchung.id,
        details={"beschreibung": buchung.beschreibung, "betrag": str(buchung.betrag)},
    )
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
    filters: dict[str, str | int] = {}
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
        positionen_data = [p.model_dump() for p in body.positionen] if body.positionen else None
        rechnung = await svc.create_invoice(
            mitglied_id=body.mitglied_id,
            betrag=Decimal(str(body.betrag)) if body.betrag is not None else None,
            beschreibung=body.beschreibung,
            faelligkeitsdatum=body.faelligkeitsdatum,
            rechnungsdatum=body.rechnungsdatum,
            rechnungstyp=body.rechnungstyp,
            empfaenger_typ=body.empfaenger_typ,
            empfaenger_name=body.empfaenger_name,
            empfaenger_strasse=body.empfaenger_strasse,
            empfaenger_plz=body.empfaenger_plz,
            empfaenger_ort=body.empfaenger_ort,
            empfaenger_ust_id=body.empfaenger_ust_id,
            leistungsdatum=body.leistungsdatum,
            leistungszeitraum_von=body.leistungszeitraum_von,
            leistungszeitraum_bis=body.leistungszeitraum_bis,
            sphaere=body.sphaere,
            steuerhinweis_text=body.steuerhinweis_text,
            zahlungsziel_tage=body.zahlungsziel_tage,
            positionen=positionen_data,
            format=body.format,
            skonto_prozent=Decimal(str(body.skonto_prozent)) if body.skonto_prozent is not None else None,
            skonto_frist_tage=body.skonto_frist_tage,
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await log_audit(
        session,
        user_id=_token.admin_user_id,
        action="create",
        entity_type="rechnung",
        entity_id=rechnung.id,
        details={"rechnungsnummer": rechnung.rechnungsnummer, "betrag": str(rechnung.betrag)},
    )
    await session.commit()
    return _rechnung_to_response(rechnung)


@router.post("/rechnungen/{rechnung_id}/stellen", response_model=RechnungResponse)
async def stelle_rechnung(
    rechnung_id: int,
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> RechnungResponse:
    """Set invoice status to GESTELLT (locks editing)."""
    svc = FinanzenService(session)
    try:
        rechnung = await svc.stelle_rechnung(rechnung_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await log_audit(
        session,
        user_id=_token.admin_user_id,
        action="stelle",
        entity_type="rechnung",
        entity_id=rechnung.id,
        details={"rechnungsnummer": rechnung.rechnungsnummer},
    )
    await session.commit()
    return _rechnung_to_response(rechnung)


@router.post("/rechnungen/{rechnung_id}/stornieren", response_model=RechnungResponse)
async def storniere_rechnung(
    rechnung_id: int,
    body: StornoRequest | None = None,
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> RechnungResponse:
    """Cancel an invoice and create a Stornorechnung."""
    svc = FinanzenService(session)
    grund = body.grund if body else None
    try:
        storno = await svc.storniere_rechnung(rechnung_id, grund=grund)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await log_audit(
        session,
        user_id=_token.admin_user_id,
        action="storniere",
        entity_type="rechnung",
        entity_id=rechnung_id,
        details={"storno_rechnung_id": storno.id, "storno_nummer": storno.rechnungsnummer},
    )
    await session.commit()
    return _rechnung_to_response(storno)


@router.delete("/rechnungen/{rechnung_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invoice(
    rechnung_id: int,
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    """Delete an invoice (Löschsperre enforcement / GoBD compliance)."""
    svc = FinanzenService(session)
    try:
        await svc.delete_invoice(rechnung_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc
    await log_audit(
        session,
        user_id=_token.admin_user_id,
        action="delete",
        entity_type="rechnung",
        entity_id=rechnung_id,
    )
    await session.commit()


@router.post("/rechnungen/{rechnung_id}/versenden", response_model=RechnungResponse)
async def versende_rechnung(
    rechnung_id: int,
    body: VersandRequest,
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> RechnungResponse:
    """Record invoice dispatch (Versand-Kanal tracking)."""
    svc = FinanzenService(session)
    try:
        rechnung = await svc.versende_rechnung(
            rechnung_id=rechnung_id,
            kanal=body.kanal,
            empfaenger=body.empfaenger,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    await log_audit(
        session,
        user_id=_token.admin_user_id,
        action="versenden",
        entity_type="rechnung",
        entity_id=rechnung.id,
        details={"kanal": body.kanal, "empfaenger": body.empfaenger},
    )
    await session.commit()
    return _rechnung_to_response(rechnung)


@router.get("/rechnungen/{rechnung_id}/skonto", response_model=SkontoInfoResponse)
async def get_skonto_info(
    rechnung_id: int,
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> SkontoInfoResponse:
    """Return skonto (early payment discount) info for an invoice."""
    svc = FinanzenService(session)
    try:
        info = await svc.calculate_skonto(rechnung_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    return SkontoInfoResponse(
        skonto_betrag=float(info["skonto_betrag"]),
        zahlbetrag=float(info["zahlbetrag"]),
        skonto_frist_bis=info["skonto_frist_bis"],
        skonto_verfuegbar=info["skonto_verfuegbar"],
        skonto_prozent=float(info["skonto_prozent"]),
    )


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
            apply_skonto=body.apply_skonto,
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
                rechnungstyp="mitgliedsbeitrag",
                sphaere="ideell",
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


# -- EUeR (Einnahmen-Ueberschuss-Rechnung) ------------------------------------


@router.get("/euer", response_model=EuerReportResponse)
async def get_euer_report(
    jahr: int = Query(..., description="Geschaeftsjahr"),
    sphare: str | None = Query(None, description="Optional: Sphaere filtern"),
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> EuerReportResponse:
    """Einnahmen-Ueberschuss-Rechnung fuer ein Geschaeftsjahr."""
    svc = FinanzenService(session)
    try:
        report = await svc.get_euer_report(year=jahr, sphare=sphare)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return EuerReportResponse(**report)


# -- Kostenstellen ----------------------------------------------------------


def _kostenstelle_to_response(ks) -> KostenstelleResponse:
    return KostenstelleResponse(
        id=ks.id,
        name=ks.name,
        beschreibung=ks.beschreibung,
        abteilung_id=ks.abteilung_id,
        budget=float(ks.budget) if ks.budget is not None else None,
        freigabelimit=float(ks.freigabelimit) if ks.freigabelimit is not None else None,
    )


@router.get("/kostenstellen", response_model=list[KostenstelleBudgetResponse])
async def list_cost_centers(
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> list[KostenstelleBudgetResponse]:
    svc = FinanzenService(session)
    centers = await svc.get_cost_centers()
    result = []
    for ks in centers:
        budget_status = await svc.get_budget_status(ks.id)
        result.append(KostenstelleBudgetResponse(
            kostenstelle_id=budget_status["kostenstelle_id"],
            name=budget_status["name"],
            budget=float(budget_status["budget"]),
            spent=float(budget_status["spent"]),
            remaining=float(budget_status["remaining"]),
            freigabelimit=float(budget_status["freigabelimit"]) if budget_status["freigabelimit"] is not None else None,
        ))
    return result


@router.post("/kostenstellen", response_model=KostenstelleResponse, status_code=status.HTTP_201_CREATED)
async def create_cost_center(
    body: KostenstelleCreate,
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> KostenstelleResponse:
    svc = FinanzenService(session)
    data = body.model_dump(exclude_unset=True)
    if "budget" in data and data["budget"] is not None:
        data["budget"] = Decimal(str(data["budget"]))
    if "freigabelimit" in data and data["freigabelimit"] is not None:
        data["freigabelimit"] = Decimal(str(data["freigabelimit"]))
    try:
        ks = await svc.create_cost_center(data)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await log_audit(
        session,
        user_id=_token.admin_user_id,
        action="create",
        entity_type="kostenstelle",
        entity_id=ks.id,
        details={"name": ks.name},
    )
    await session.commit()
    return _kostenstelle_to_response(ks)


@router.put("/kostenstellen/{kostenstelle_id}", response_model=KostenstelleResponse)
async def update_cost_center(
    kostenstelle_id: int,
    body: KostenstelleUpdate,
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> KostenstelleResponse:
    svc = FinanzenService(session)
    data = body.model_dump(exclude_unset=True)
    if "budget" in data and data["budget"] is not None:
        data["budget"] = Decimal(str(data["budget"]))
    if "freigabelimit" in data and data["freigabelimit"] is not None:
        data["freigabelimit"] = Decimal(str(data["freigabelimit"]))
    try:
        ks = await svc.update_cost_center(kostenstelle_id, data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await log_audit(
        session,
        user_id=_token.admin_user_id,
        action="update",
        entity_type="kostenstelle",
        entity_id=ks.id,
        details={"name": ks.name},
    )
    await session.commit()
    return _kostenstelle_to_response(ks)


# -- Leistungsverrechnung ---------------------------------------------------


@router.post("/leistungsverrechnung", response_model=LeistungsverrechnungResponse, status_code=status.HTTP_201_CREATED)
async def allocate_shared_costs(
    body: LeistungsverrechnungRequest,
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> LeistungsverrechnungResponse:
    svc = FinanzenService(session)
    allocations = [
        {
            "kostenstelle_id": a.kostenstelle_id,
            "anteil": Decimal(str(a.anteil)),
            "beschreibung": a.beschreibung,
        }
        for a in body.allocations
    ]
    try:
        children = await svc.allocate_shared_costs(body.buchung_id, allocations)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await session.commit()
    return LeistungsverrechnungResponse(
        parent_buchung_id=body.buchung_id,
        children=[_buchung_to_response(c) for c in children],
    )


# -- Vereinsstammdaten ------------------------------------------------------


@router.get("/vereinsstammdaten", response_model=VereinsstammdatenResponse | None)
async def get_vereinsstammdaten(
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> VereinsstammdatenResponse | None:
    svc = FinanzenService(session)
    stammdaten = await svc.get_vereinsstammdaten()
    if stammdaten is None:
        return None
    return VereinsstammdatenResponse.model_validate(stammdaten)


@router.put("/vereinsstammdaten", response_model=VereinsstammdatenResponse)
async def update_vereinsstammdaten(
    body: VereinsstammdatenUpdate,
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> VereinsstammdatenResponse:
    svc = FinanzenService(session)
    data = body.model_dump(exclude_unset=True)
    try:
        stammdaten = await svc.update_vereinsstammdaten(data)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await log_audit(
        session,
        user_id=_token.admin_user_id,
        action="update",
        entity_type="vereinsstammdaten",
        entity_id=stammdaten.id,
        details={"name": stammdaten.name},
    )
    await session.commit()
    return VereinsstammdatenResponse.model_validate(stammdaten)


# -- SEPA Mandate -----------------------------------------------------------


@router.get("/mandate", response_model=SepaMandatListResponse)
async def list_mandate(
    aktiv: bool | None = None,
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> SepaMandatListResponse:
    svc = FinanzenService(session)
    items, total = await svc.get_mandate(aktiv_filter=aktiv)
    return SepaMandatListResponse(
        items=[SepaMandatResponse(**item) for item in items],
        total=total,
    )


@router.post("/mandate", response_model=SepaMandatResponse, status_code=status.HTTP_201_CREATED)
async def create_mandat(
    body: SepaMandatCreate,
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> SepaMandatResponse:
    svc = FinanzenService(session)
    try:
        mandat = await svc.create_mandat(body.model_dump())
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await log_audit(
        session,
        user_id=_token.admin_user_id,
        action="create",
        entity_type="sepa_mandat",
        entity_id=mandat.id,
        details={"mandatsreferenz": mandat.mandatsreferenz},
    )
    await session.commit()
    return SepaMandatResponse(
        id=mandat.id,
        mitglied_id=mandat.mitglied_id,
        iban=mandat.iban,
        bic=mandat.bic,
        kontoinhaber=mandat.kontoinhaber,
        mandatsreferenz=mandat.mandatsreferenz,
        unterschriftsdatum=mandat.unterschriftsdatum,
        gueltig_ab=mandat.gueltig_ab,
        gueltig_bis=mandat.gueltig_bis,
        aktiv=mandat.aktiv,
    )


@router.put("/mandate/{mandat_id}", response_model=SepaMandatResponse)
async def update_mandat(
    mandat_id: int,
    body: SepaMandatUpdate,
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> SepaMandatResponse:
    svc = FinanzenService(session)
    data = body.model_dump(exclude_unset=True)
    try:
        mandat = await svc.update_mandat(mandat_id, data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await log_audit(
        session,
        user_id=_token.admin_user_id,
        action="update",
        entity_type="sepa_mandat",
        entity_id=mandat.id,
        details={"mandatsreferenz": mandat.mandatsreferenz},
    )
    await session.commit()
    return SepaMandatResponse(
        id=mandat.id,
        mitglied_id=mandat.mitglied_id,
        iban=mandat.iban,
        bic=mandat.bic,
        kontoinhaber=mandat.kontoinhaber,
        mandatsreferenz=mandat.mandatsreferenz,
        unterschriftsdatum=mandat.unterschriftsdatum,
        gueltig_ab=mandat.gueltig_ab,
        gueltig_bis=mandat.gueltig_bis,
        aktiv=mandat.aktiv,
    )


@router.delete("/mandate/{mandat_id}", response_model=SepaMandatResponse)
async def deactivate_mandat(
    mandat_id: int,
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> SepaMandatResponse:
    svc = FinanzenService(session)
    try:
        mandat = await svc.deactivate_mandat(mandat_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await log_audit(
        session,
        user_id=_token.admin_user_id,
        action="deactivate",
        entity_type="sepa_mandat",
        entity_id=mandat.id,
        details={"mandatsreferenz": mandat.mandatsreferenz},
    )
    await session.commit()
    return SepaMandatResponse(
        id=mandat.id,
        mitglied_id=mandat.mitglied_id,
        iban=mandat.iban,
        bic=mandat.bic,
        kontoinhaber=mandat.kontoinhaber,
        mandatsreferenz=mandat.mandatsreferenz,
        unterschriftsdatum=mandat.unterschriftsdatum,
        gueltig_ab=mandat.gueltig_ab,
        gueltig_bis=mandat.gueltig_bis,
        aktiv=mandat.aktiv,
    )


# -- Rechnung PDF -----------------------------------------------------------


@router.get("/rechnungen/export")
async def export_rechnungen_zip(
    jahr: int = Query(..., description="Jahr fuer den PDF-Export"),
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    """Generate a ZIP archive of all invoice PDFs for a given year."""
    result = await session.execute(
        select(Rechnung.id, Rechnung.rechnungsnummer).where(
            extract("year", Rechnung.rechnungsdatum) == jahr,
        )
    )
    invoices = result.all()
    if not invoices:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Keine Rechnungen fuer Jahr {jahr} gefunden",
        )

    pdf_svc = RechnungPdfService()
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for inv_id, inv_nummer in invoices:
            try:
                pdf_bytes = await pdf_svc.generate_rechnung_pdf(session, inv_id)
                zf.writestr(f"RE-{inv_nummer}.pdf", pdf_bytes)
            except ValueError:
                continue  # Skip invoices that fail to generate

    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="Rechnungen-{jahr}.zip"',
        },
    )


@router.get("/rechnungen/{rechnung_id}/pdf")
async def get_rechnung_pdf(
    rechnung_id: int,
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    """Generate and return a PDF for the given invoice."""
    pdf_svc = RechnungPdfService()
    try:
        pdf_bytes = await pdf_svc.generate_rechnung_pdf(session, rechnung_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    # Fetch rechnungsnummer for filename
    result = await session.execute(
        select(Rechnung.rechnungsnummer).where(Rechnung.id == rechnung_id)
    )
    nummer = result.scalar_one_or_none() or str(rechnung_id)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="RE-{nummer}.pdf"',
        },
    )


@router.get("/rechnungen/{rechnung_id}/xml")
async def get_rechnung_zugferd_xml(
    rechnung_id: int,
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    """Generate and return ZUGFeRD 2.1 BASIC profile XML for the given invoice."""
    zugferd_svc = ZugferdService()
    try:
        xml_bytes = await zugferd_svc.generate_zugferd_xml(session, rechnung_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    # Fetch rechnungsnummer for filename
    result = await session.execute(
        select(Rechnung.rechnungsnummer).where(Rechnung.id == rechnung_id)
    )
    nummer = result.scalar_one_or_none() or str(rechnung_id)

    return Response(
        content=xml_bytes,
        media_type="application/xml",
        headers={
            "Content-Disposition": f'inline; filename="RE-{nummer}-zugferd.xml"',
        },
    )


# -- Eingangsrechnungen (incoming e-invoices) --------------------------------


def _eingangsrechnung_to_response(r) -> EingangsrechnungResponse:
    return EingangsrechnungResponse(
        id=r.id,
        rechnungsnummer=r.rechnungsnummer,
        aussteller_name=r.aussteller_name,
        aussteller_strasse=r.aussteller_strasse,
        aussteller_plz=r.aussteller_plz,
        aussteller_ort=r.aussteller_ort,
        aussteller_steuernr=r.aussteller_steuernr,
        aussteller_ust_id=r.aussteller_ust_id,
        rechnungsdatum=r.rechnungsdatum,
        faelligkeitsdatum=r.faelligkeitsdatum,
        leistungsdatum=r.leistungsdatum,
        summe_netto=float(r.summe_netto),
        summe_steuer=float(r.summe_steuer),
        summe_brutto=float(r.summe_brutto),
        waehrung=r.waehrung,
        status=r.status.value if hasattr(r.status, "value") else str(r.status),
        kostenstelle_id=r.kostenstelle_id,
        sphaere=r.sphaere,
        quell_format=r.quell_format,
        notiz=r.notiz,
        created_at=r.created_at,
    )


def _eingangsrechnung_to_detail(r) -> EingangsrechnungDetailResponse:
    return EingangsrechnungDetailResponse(
        id=r.id,
        rechnungsnummer=r.rechnungsnummer,
        aussteller_name=r.aussteller_name,
        aussteller_strasse=r.aussteller_strasse,
        aussteller_plz=r.aussteller_plz,
        aussteller_ort=r.aussteller_ort,
        aussteller_steuernr=r.aussteller_steuernr,
        aussteller_ust_id=r.aussteller_ust_id,
        rechnungsdatum=r.rechnungsdatum,
        faelligkeitsdatum=r.faelligkeitsdatum,
        leistungsdatum=r.leistungsdatum,
        summe_netto=float(r.summe_netto),
        summe_steuer=float(r.summe_steuer),
        summe_brutto=float(r.summe_brutto),
        waehrung=r.waehrung,
        status=r.status.value if hasattr(r.status, "value") else str(r.status),
        kostenstelle_id=r.kostenstelle_id,
        sphaere=r.sphaere,
        quell_format=r.quell_format,
        quell_xml=r.quell_xml,
        notiz=r.notiz,
        created_at=r.created_at,
        updated_at=r.updated_at,
    )


@router.post(
    "/eingangsrechnungen/upload",
    response_model=EingangsrechnungUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_eingangsrechnung(
    file: UploadFile = File(...),
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> EingangsrechnungUploadResponse:
    """Upload an XRechnung/ZUGFeRD XML file and create an Eingangsrechnung."""
    from sportverein.services.eingangsrechnung import EingangsrechnungService

    content = await file.read()
    svc = EingangsrechnungService(session)

    try:
        rechnung, warnungen = await svc.create_from_xml(session, content)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    await log_audit(
        session,
        user_id=_token.admin_user_id,
        action="upload",
        entity_type="eingangsrechnung",
        entity_id=rechnung.id,
        details={
            "rechnungsnummer": rechnung.rechnungsnummer,
            "aussteller": rechnung.aussteller_name,
        },
    )
    await session.commit()
    return EingangsrechnungUploadResponse(
        rechnung=_eingangsrechnung_to_response(rechnung),
        warnungen=warnungen,
    )


@router.get("/eingangsrechnungen", response_model=EingangsrechnungListResponse)
async def list_eingangsrechnungen(
    eingangsrechnung_status: str | None = Query(None, alias="status"),
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = 1,
    page_size: int = 20,
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> EingangsrechnungListResponse:
    """List incoming invoices with optional filters."""
    from sportverein.services.eingangsrechnung import EingangsrechnungService

    svc = EingangsrechnungService(session)
    filters: dict = {}
    if eingangsrechnung_status:
        filters["status"] = eingangsrechnung_status
    if date_from:
        filters["date_from"] = date_from
    if date_to:
        filters["date_to"] = date_to

    items, total = await svc.list_eingangsrechnungen(
        session, filters=filters or None, page=page, page_size=page_size
    )
    return EingangsrechnungListResponse(
        items=[_eingangsrechnung_to_response(r) for r in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/eingangsrechnungen/{rechnung_id}",
    response_model=EingangsrechnungDetailResponse,
)
async def get_eingangsrechnung(
    rechnung_id: int,
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> EingangsrechnungDetailResponse:
    """Get a single incoming invoice with full details including XML."""
    from sportverein.services.eingangsrechnung import EingangsrechnungService

    svc = EingangsrechnungService(session)
    rechnung = await svc.get_eingangsrechnung(session, rechnung_id)
    if rechnung is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Eingangsrechnung {rechnung_id} nicht gefunden",
        )
    return _eingangsrechnung_to_detail(rechnung)


@router.put(
    "/eingangsrechnungen/{rechnung_id}/status",
    response_model=EingangsrechnungResponse,
)
async def update_eingangsrechnung_status(
    rechnung_id: int,
    body: EingangsrechnungStatusUpdate,
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> EingangsrechnungResponse:
    """Update the status of an incoming invoice."""
    from sportverein.services.eingangsrechnung import EingangsrechnungService

    svc = EingangsrechnungService(session)
    try:
        rechnung = await svc.update_status(
            session, rechnung_id, body.status, body.notiz
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    await log_audit(
        session,
        user_id=_token.admin_user_id,
        action="status_update",
        entity_type="eingangsrechnung",
        entity_id=rechnung.id,
        details={"status": body.status, "notiz": body.notiz},
    )
    await session.commit()
    return _eingangsrechnung_to_response(rechnung)
