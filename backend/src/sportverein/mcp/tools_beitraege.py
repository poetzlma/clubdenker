"""MCP tools for finance (Beitraege/Finanzen) management."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sportverein.mcp.server import mcp
from sportverein.mcp.session import get_mcp_session
from sportverein.services.beitraege import BeitraegeService
from sportverein.services.finanzen import FinanzenService


@mcp.tool(description="Beiträge berechnen für ein Mitglied oder alle Mitglieder für ein Jahr.")
async def beitraege_berechnen(
    billing_year: int,
    member_id: int | None = None,
) -> dict:
    async with get_mcp_session() as session:
        svc = BeitraegeService(session)
        if member_id is not None:
            result = await svc.calculate_member_fee(member_id, billing_year)
            # Convert Decimal to float for JSON serialization
            result["jahresbeitrag"] = float(result["jahresbeitrag"])
            result["prorata_betrag"] = float(result["prorata_betrag"])
            await session.commit()
            return {"fees": [result]}
        else:
            results = await svc.calculate_all_fees(billing_year)
            for r in results:
                r["jahresbeitrag"] = float(r["jahresbeitrag"])
                r["prorata_betrag"] = float(r["prorata_betrag"])
            await session.commit()
            return {"fees": results, "count": len(results)}


@mcp.tool(description="SEPA-XML für gegebene Rechnungs-IDs generieren.")
async def sepa_xml_generieren(
    rechnungen_ids: list[int],
) -> dict:
    async with get_mcp_session() as session:
        svc = FinanzenService(session)
        try:
            xml = await svc.generate_sepa_xml(rechnungen_ids)
        except ValueError as exc:
            return {"error": str(exc)}
        await session.commit()
        return {"xml": xml, "count": len(rechnungen_ids)}


@mcp.tool(description="Rechnung für ein Mitglied erstellen.")
async def rechnung_erstellen(
    mitglied_id: int,
    betrag: float,
    beschreibung: str,
    faelligkeitsdatum: str,
    rechnungsdatum: str | None = None,
) -> dict:
    async with get_mcp_session() as session:
        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            mitglied_id=mitglied_id,
            betrag=Decimal(str(betrag)),
            beschreibung=beschreibung,
            faelligkeitsdatum=date.fromisoformat(faelligkeitsdatum),
            rechnungsdatum=date.fromisoformat(rechnungsdatum) if rechnungsdatum else None,
        )
        await session.commit()
        return {
            "id": rechnung.id,
            "rechnungsnummer": rechnung.rechnungsnummer,
            "mitglied_id": rechnung.mitglied_id,
            "betrag": float(rechnung.betrag),
            "beschreibung": rechnung.beschreibung,
            "rechnungsdatum": rechnung.rechnungsdatum.isoformat(),
            "faelligkeitsdatum": rechnung.faelligkeitsdatum.isoformat(),
            "status": rechnung.status.value,
        }


@mcp.tool(description="Zahlung für eine Rechnung verbuchen.")
async def zahlung_verbuchen(
    rechnung_id: int,
    betrag: float,
    zahlungsart: str = "ueberweisung",
    referenz: str | None = None,
) -> dict:
    async with get_mcp_session() as session:
        svc = FinanzenService(session)
        zahlung = await svc.record_payment(
            rechnung_id=rechnung_id,
            betrag=Decimal(str(betrag)),
            zahlungsart=zahlungsart,
            referenz=referenz,
        )
        await session.commit()
        return {
            "id": zahlung.id,
            "rechnung_id": zahlung.rechnung_id,
            "betrag": float(zahlung.betrag),
            "zahlungsdatum": zahlung.zahlungsdatum.isoformat(),
            "zahlungsart": zahlung.zahlungsart.value,
            "referenz": zahlung.referenz,
        }


@mcp.tool(description="Mahnlauf starten — überfällige Rechnungen ermitteln.")
async def mahnlauf_starten() -> dict:
    async with get_mcp_session() as session:
        svc = FinanzenService(session)
        overdue = await svc.get_overdue_invoices()
        await session.commit()
        return {
            "mahnungen": [
                {
                    "id": r.id,
                    "rechnungsnummer": r.rechnungsnummer,
                    "mitglied_id": r.mitglied_id,
                    "betrag": float(r.betrag),
                    "faelligkeitsdatum": r.faelligkeitsdatum.isoformat(),
                }
                for r in overdue
            ],
            "count": len(overdue),
        }


@mcp.tool(description="Spendenbescheinigung für ein Mitglied erstellen.")
async def spendenbescheinigung_erstellen(
    mitglied_id: int,
    betrag: float,
    zweck: str,
) -> dict:
    async with get_mcp_session() as session:
        svc = FinanzenService(session)
        bescheinigung = await svc.create_donation_receipt(
            mitglied_id=mitglied_id,
            betrag=Decimal(str(betrag)),
            zweck=zweck,
        )
        await session.commit()
        return {
            "id": bescheinigung.id,
            "mitglied_id": bescheinigung.mitglied_id,
            "betrag": float(bescheinigung.betrag),
            "ausstellungsdatum": bescheinigung.ausstellungsdatum.isoformat(),
            "zweck": bescheinigung.zweck,
        }


@mcp.tool(description="Finanzbericht erstellen — Kassenstand nach Sphäre und Gesamtsaldo.")
async def finanzbericht_erstellen() -> dict:
    async with get_mcp_session() as session:
        svc = FinanzenService(session)
        by_sphere = await svc.get_balance_by_sphere()
        total = await svc.get_total_balance()
        await session.commit()
        return {
            "by_sphere": {k: float(v) for k, v in by_sphere.items()},
            "total": float(total),
        }


@mcp.tool(description="Buchung anlegen (Finanzbuchung).")
async def buchung_anlegen(
    buchungsdatum: str,
    betrag: float,
    beschreibung: str,
    konto: str,
    gegenkonto: str,
    sphare: str,
    mitglied_id: int | None = None,
) -> dict:
    async with get_mcp_session() as session:
        svc = FinanzenService(session)
        buchung = await svc.create_booking({
            "buchungsdatum": date.fromisoformat(buchungsdatum),
            "betrag": Decimal(str(betrag)),
            "beschreibung": beschreibung,
            "konto": konto,
            "gegenkonto": gegenkonto,
            "sphare": sphare,
            "mitglied_id": mitglied_id,
        })
        await session.commit()
        return {
            "id": buchung.id,
            "buchungsdatum": buchung.buchungsdatum.isoformat(),
            "betrag": float(buchung.betrag),
            "beschreibung": buchung.beschreibung,
            "konto": buchung.konto,
            "gegenkonto": buchung.gegenkonto,
            "sphare": buchung.sphare.value,
            "mitglied_id": buchung.mitglied_id,
        }
