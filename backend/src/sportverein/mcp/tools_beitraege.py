"""MCP tools for finance (Beitraege/Finanzen) management."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sportverein.mcp.server import mcp
from sportverein.mcp.session import get_mcp_session
from sportverein.services.agents import (
    AufwandMonitorAgent,
    BeitragseinzugAgent,
    MahnwesenAgent,
)
from sportverein.services.beitraege import BeitraegeService
from sportverein.services.ehrenamt import EhrenamtService
from sportverein.services.eingangsrechnung import EingangsrechnungService
from sportverein.services.finanzen import FinanzenService
from sportverein.services.rechnung_pdf import RechnungPdfService
from sportverein.services.rechnung_templates import RechnungTemplateService
from sportverein.services.zugferd import ZugferdService


@mcp.tool(description="Beitraege berechnen fuer ein Mitglied oder alle Mitglieder fuer ein Jahr.")
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


@mcp.tool(description="SEPA-XML fuer gegebene Rechnungs-IDs generieren.")
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


@mcp.tool(description="Rechnung fuer ein Mitglied erstellen (mit optionalen Positionen und Steuerinformationen).")
async def rechnung_erstellen(
    mitglied_id: int | None = None,
    betrag: float | None = None,
    beschreibung: str = "",
    faelligkeitsdatum: str | None = None,
    rechnungsdatum: str | None = None,
    rechnungstyp: str = "sonstige",
    empfaenger_typ: str = "mitglied",
    empfaenger_name: str | None = None,
    sphaere: str | None = None,
    steuerhinweis_text: str | None = None,
    zahlungsziel_tage: int = 14,
    positionen: list[dict] | None = None,
) -> dict:
    async with get_mcp_session() as session:
        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            mitglied_id=mitglied_id,
            betrag=Decimal(str(betrag)) if betrag is not None else None,
            beschreibung=beschreibung,
            faelligkeitsdatum=date.fromisoformat(faelligkeitsdatum) if faelligkeitsdatum else None,
            rechnungsdatum=date.fromisoformat(rechnungsdatum) if rechnungsdatum else None,
            rechnungstyp=rechnungstyp,
            empfaenger_typ=empfaenger_typ,
            empfaenger_name=empfaenger_name,
            sphaere=sphaere,
            steuerhinweis_text=steuerhinweis_text,
            zahlungsziel_tage=zahlungsziel_tage,
            positionen=positionen,
        )
        await session.commit()
        return {
            "id": rechnung.id,
            "rechnungsnummer": rechnung.rechnungsnummer,
            "mitglied_id": rechnung.mitglied_id,
            "betrag": float(rechnung.betrag),
            "summe_netto": float(rechnung.summe_netto),
            "summe_steuer": float(rechnung.summe_steuer),
            "beschreibung": rechnung.beschreibung,
            "rechnungsdatum": rechnung.rechnungsdatum.isoformat(),
            "faelligkeitsdatum": rechnung.faelligkeitsdatum.isoformat(),
            "status": rechnung.status.value,
            "rechnungstyp": rechnung.rechnungstyp.value,
            "sphaere": rechnung.sphaere,
            "verwendungszweck": rechnung.verwendungszweck,
        }


@mcp.tool(description="Rechnung stellen (Status von Entwurf auf Gestellt setzen, sperrt Bearbeitung).")
async def rechnung_stellen(rechnung_id: int) -> dict:
    async with get_mcp_session() as session:
        svc = FinanzenService(session)
        try:
            rechnung = await svc.stelle_rechnung(rechnung_id)
        except ValueError as exc:
            return {"error": str(exc)}
        await session.commit()
        return {
            "id": rechnung.id,
            "rechnungsnummer": rechnung.rechnungsnummer,
            "status": rechnung.status.value,
            "gestellt_am": rechnung.gestellt_am.isoformat() if rechnung.gestellt_am else None,
        }


@mcp.tool(description="Rechnung stornieren (Stornorechnung erstellen, Original wird als storniert markiert).")
async def rechnung_stornieren(rechnung_id: int, grund: str | None = None) -> dict:
    async with get_mcp_session() as session:
        svc = FinanzenService(session)
        try:
            storno = await svc.storniere_rechnung(rechnung_id, grund=grund)
        except ValueError as exc:
            return {"error": str(exc)}
        await session.commit()
        return {
            "storno_id": storno.id,
            "storno_rechnungsnummer": storno.rechnungsnummer,
            "original_rechnung_id": rechnung_id,
            "storno_betrag": float(storno.betrag),
            "status": storno.status.value,
        }


@mcp.tool(description="Zahlung fuer eine Rechnung verbuchen.")
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


@mcp.tool(description="Mahnlauf starten — ueberfaellige Rechnungen ermitteln.")
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


@mcp.tool(description="Spendenbescheinigung fuer ein Mitglied erstellen.")
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


@mcp.tool(description="Finanzbericht erstellen — Kassenstand nach Sphaere und Gesamtsaldo.")
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


@mcp.tool(description="Budget einer Kostenstelle pruefen. Zeigt Budget, Ausgaben, verbleibendes Budget und Freigabelimit.")
async def budget_pruefen(kostenstelle_id: int) -> dict:
    async with get_mcp_session() as session:
        svc = FinanzenService(session)
        try:
            budget_status = await svc.get_budget_status(kostenstelle_id)
        except ValueError as exc:
            return {"error": str(exc)}
        await session.commit()
        return {
            "kostenstelle_id": budget_status["kostenstelle_id"],
            "name": budget_status["name"],
            "budget": float(budget_status["budget"]),
            "spent": float(budget_status["spent"]),
            "remaining": float(budget_status["remaining"]),
            "freigabelimit": float(budget_status["freigabelimit"]) if budget_status["freigabelimit"] is not None else None,
        }


@mcp.tool(description="Aufwandsentschaedigung: Freibetraege pruefen und verwalten (Paragraph 3 Nr.26/26a EStG).")
async def aufwandsentschaedigung(
    member_id: int,
    year: int,
    betrag: float | None = None,
    typ: str | None = None,
    beschreibung: str | None = None,
    datum: str | None = None,
) -> dict:
    """If betrag/typ/beschreibung provided: create new entry.
    Otherwise: check current limits."""
    async with get_mcp_session() as session:
        svc = EhrenamtService(session)
        if betrag is not None and typ is not None and beschreibung is not None:
            entry = await svc.create_compensation({
                "mitglied_id": member_id,
                "betrag": Decimal(str(betrag)),
                "datum": date.fromisoformat(datum) if datum else date.today(),
                "typ": typ,
                "beschreibung": beschreibung,
            })
            limits = await svc.check_limits(member_id, year)
            await session.commit()
            return {
                "created": {
                    "id": entry.id,
                    "betrag": float(entry.betrag),
                    "typ": entry.typ.value,
                    "datum": entry.datum.isoformat(),
                },
                "limits": {
                    k: {kk: float(vv) if isinstance(vv, Decimal) else vv for kk, vv in v.items()}
                    for k, v in limits.items()
                },
            }
        else:
            limits = await svc.check_limits(member_id, year)
            await session.commit()
            return {
                "limits": {
                    k: {kk: float(vv) if isinstance(vv, Decimal) else vv for kk, vv in v.items()}
                    for k, v in limits.items()
                },
            }


@mcp.tool(description="Interne Leistungsverrechnung: Buchung auf mehrere Kostenstellen verteilen.")
async def leistungsverrechnung(
    buchung_id: int,
    allocations: list[dict],
) -> dict:
    """allocations: list of {kostenstelle_id: int, anteil: float, beschreibung?: str}"""
    async with get_mcp_session() as session:
        svc = FinanzenService(session)
        parsed = [
            {
                "kostenstelle_id": a["kostenstelle_id"],
                "anteil": Decimal(str(a["anteil"])),
                "beschreibung": a.get("beschreibung"),
            }
            for a in allocations
        ]
        try:
            children = await svc.allocate_shared_costs(buchung_id, parsed)
        except ValueError as exc:
            return {"error": str(exc)}
        await session.commit()
        return {
            "parent_buchung_id": buchung_id,
            "children": [
                {
                    "id": c.id,
                    "betrag": float(c.betrag),
                    "kostenstelle_id": c.kostenstelle_id,
                    "beschreibung": c.beschreibung,
                }
                for c in children
            ],
        }


@mcp.tool(description="EUeR (Einnahmen-Ueberschuss-Rechnung) fuer ein Geschaeftsjahr erstellen. Gruppiert nach Sphaere, Monat und Kostenstelle.")
async def finanzen_euer(
    jahr: int,
    sphare: str | None = None,
) -> dict:
    async with get_mcp_session() as session:
        svc = FinanzenService(session)
        try:
            report = await svc.get_euer_report(year=jahr, sphare=sphare)
        except ValueError as exc:
            return {"error": str(exc)}
        await session.commit()
        return report


@mcp.tool(description="Beitragseinzug starten: Beitraege berechnen, Rechnungen erstellen, SEPA generieren.")
async def beitragseinzug_starten(year: int, month: int) -> dict:
    async with get_mcp_session() as session:
        agent = BeitragseinzugAgent(session)
        try:
            result = await agent.run(year, month)
        except Exception as exc:
            return {"error": str(exc)}
        await session.commit()
        return result


@mcp.tool(description="Mahnwesen-Agent: Ueberfaellige Rechnungen analysieren und Mahnstufen zuordnen.")
async def mahnwesen_agent() -> dict:
    async with get_mcp_session() as session:
        agent = MahnwesenAgent(session)
        result = await agent.run()
        await session.commit()
        return result


@mcp.tool(description="PDF-Dokument fuer eine Rechnung erzeugen. Gibt Base64-kodierten PDF-Inhalt zurueck.")
async def rechnung_pdf_generieren(rechnung_id: int) -> dict:
    import base64

    async with get_mcp_session() as session:
        pdf_svc = RechnungPdfService()
        try:
            pdf_bytes = await pdf_svc.generate_rechnung_pdf(session, rechnung_id)
        except ValueError as exc:
            return {"error": str(exc)}
        encoded = base64.b64encode(pdf_bytes).decode("ascii")
        return {
            "rechnung_id": rechnung_id,
            "pdf_base64": encoded,
            "size_bytes": len(pdf_bytes),
        }


@mcp.tool(description="ZUGFeRD 2.1 XML fuer eine Rechnung erzeugen (Factur-X BASIC Profil).")
async def rechnung_zugferd_xml(rechnung_id: int) -> dict:
    async with get_mcp_session() as session:
        zugferd_svc = ZugferdService()
        try:
            xml_bytes = await zugferd_svc.generate_zugferd_xml(session, rechnung_id)
        except ValueError as exc:
            return {"error": str(exc)}
        return {
            "rechnung_id": rechnung_id,
            "xml": xml_bytes.decode("utf-8"),
            "size_bytes": len(xml_bytes),
        }


@mcp.tool(description="Aufwand-Monitor: Ehrenamtliche Freibetraege ueberwachen, Warnungen bei >80%.")
async def aufwand_monitor() -> dict:
    async with get_mcp_session() as session:
        agent = AufwandMonitorAgent(session)
        result = await agent.run()
        await session.commit()
        return result


@mcp.tool(description="Versand einer Rechnung protokollieren (E-Mail, Post, Portal)")
async def rechnung_versenden(
    rechnung_id: int,
    kanal: str,
    empfaenger: str,
) -> dict:
    async with get_mcp_session() as session:
        svc = FinanzenService(session)
        try:
            rechnung = await svc.versende_rechnung(rechnung_id, kanal, empfaenger)
        except ValueError as exc:
            return {"error": str(exc)}
        await session.commit()
        return {
            "id": rechnung.id,
            "rechnungsnummer": rechnung.rechnungsnummer,
            "versand_kanal": rechnung.versand_kanal,
            "versendet_am": rechnung.versendet_am.isoformat() if rechnung.versendet_am else None,
            "versendet_an": rechnung.versendet_an,
        }


@mcp.tool(description="Vereinsstammdaten abrufen (Name, Adresse, Steuernummer, IBAN)")
async def vereinsstammdaten_abrufen() -> dict:
    async with get_mcp_session() as session:
        svc = FinanzenService(session)
        stammdaten = await svc.get_vereinsstammdaten()
        if stammdaten is None:
            return {"message": "Keine Vereinsstammdaten hinterlegt"}
        return {
            "id": stammdaten.id,
            "name": stammdaten.name,
            "strasse": stammdaten.strasse,
            "plz": stammdaten.plz,
            "ort": stammdaten.ort,
            "steuernummer": stammdaten.steuernummer,
            "ust_id": stammdaten.ust_id,
            "iban": stammdaten.iban,
            "bic": stammdaten.bic,
        }


@mcp.tool(description="Vereinsstammdaten aktualisieren (Name, Adresse, Steuernummer, IBAN)")
async def vereinsstammdaten_aktualisieren(
    name: str | None = None,
    strasse: str | None = None,
    plz: str | None = None,
    ort: str | None = None,
    steuernummer: str | None = None,
    ust_id: str | None = None,
    iban: str | None = None,
    bic: str | None = None,
) -> dict:
    async with get_mcp_session() as session:
        svc = FinanzenService(session)
        data = {}
        for key, value in [
            ("name", name),
            ("strasse", strasse),
            ("plz", plz),
            ("ort", ort),
            ("steuernummer", steuernummer),
            ("ust_id", ust_id),
            ("iban", iban),
            ("bic", bic),
        ]:
            if value is not None:
                data[key] = value
        stammdaten = await svc.update_vereinsstammdaten(data)
        await session.commit()
        return {
            "id": stammdaten.id,
            "name": stammdaten.name,
            "strasse": stammdaten.strasse,
            "plz": stammdaten.plz,
            "ort": stammdaten.ort,
            "steuernummer": stammdaten.steuernummer,
            "ust_id": stammdaten.ust_id,
            "iban": stammdaten.iban,
            "bic": stammdaten.bic,
        }


@mcp.tool(description="Rechnungsvorlagen auflisten (System-Templates fuer verschiedene Rechnungstypen)")
async def rechnungsvorlagen_auflisten() -> dict:
    svc = RechnungTemplateService()
    templates = svc.get_templates()
    return {
        "templates": [
            {
                "id": t["id"],
                "name": t["name"],
                "beschreibung": t["beschreibung"],
                "rechnungstyp": t.get("rechnungstyp", ""),
                "sphaere": t.get("sphaere", ""),
                "zahlungsziel_tage": t.get("zahlungsziel_tage", 14),
            }
            for t in templates
        ],
        "count": len(templates),
    }


@mcp.tool(description="Uebersicht der Rechnungen eines Jahres fuer ZIP-Export")
async def rechnungen_zip_exportieren(jahr: int) -> dict:
    async with get_mcp_session() as session:
        from sqlalchemy import extract, func, select as sa_select
        from sportverein.models.finanzen import Rechnung

        result = await session.execute(
            sa_select(func.count()).select_from(Rechnung).where(
                extract("year", Rechnung.rechnungsdatum) == jahr
            )
        )
        count = result.scalar_one()
        return {
            "jahr": jahr,
            "anzahl_rechnungen": count,
            "hinweis": f"{count} Rechnungen fuer {jahr} vorhanden. "
            "ZIP-Download ist ueber die REST-API verfuegbar: "
            f"GET /api/finanzen/rechnungen/export/{jahr}.zip",
        }


@mcp.tool(description="Eingangsrechnungen auflisten und filtern")
async def eingangsrechnungen_auflisten(
    status: str | None = None,
    page: int = 1,
) -> dict:
    async with get_mcp_session() as session:
        svc = EingangsrechnungService(session)
        filters = {}
        if status:
            filters["status"] = status
        items, total = await svc.list_eingangsrechnungen(
            session=session,
            filters=filters if filters else None,
            page=page,
        )
        return {
            "eingangsrechnungen": [
                {
                    "id": r.id,
                    "rechnungsnummer": r.rechnungsnummer,
                    "aussteller_name": r.aussteller_name,
                    "rechnungsdatum": r.rechnungsdatum.isoformat(),
                    "summe_brutto": float(r.summe_brutto),
                    "status": r.status.value,
                }
                for r in items
            ],
            "total": total,
            "page": page,
        }


@mcp.tool(description="Status einer Eingangsrechnung aendern (pruefen, freigeben, bezahlen)")
async def eingangsrechnung_status_aendern(
    rechnung_id: int,
    status: str,
    notiz: str | None = None,
) -> dict:
    async with get_mcp_session() as session:
        svc = EingangsrechnungService(session)
        try:
            rechnung = await svc.update_status(session, rechnung_id, status, notiz)
        except ValueError as exc:
            return {"error": str(exc)}
        await session.commit()
        return {
            "id": rechnung.id,
            "rechnungsnummer": rechnung.rechnungsnummer,
            "status": rechnung.status.value,
            "notiz": rechnung.notiz,
        }


@mcp.tool(description="Rechnungen auflisten und filtern (nach Status, Mitglied, Seite).")
async def rechnungen_auflisten(
    status: str | None = None,
    mitglied_id: int | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """List and filter invoices."""
    async with get_mcp_session() as session:
        svc = FinanzenService(session)
        filters = {}
        if status:
            filters["status"] = status
        if mitglied_id:
            filters["mitglied_id"] = mitglied_id
        invoices, total = await svc.get_invoices(
            filters=filters or None, page=page, page_size=page_size
        )
        await session.commit()
        return {
            "rechnungen": [
                {
                    "id": r.id,
                    "rechnungsnummer": r.rechnungsnummer,
                    "mitglied_id": r.mitglied_id,
                    "betrag": float(r.betrag),
                    "status": r.status.value,
                    "rechnungstyp": r.rechnungstyp.value,
                    "rechnungsdatum": r.rechnungsdatum.isoformat(),
                    "faelligkeitsdatum": r.faelligkeitsdatum.isoformat() if r.faelligkeitsdatum else None,
                    "beschreibung": r.beschreibung,
                }
                for r in invoices
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }


@mcp.tool(
    description="SEPA-Mandate verwalten: auflisten, erstellen, aktualisieren, deaktivieren."
)
async def sepa_mandate_verwalten(
    action: str = "list",
    mandat_id: int | None = None,
    mitglied_id: int | None = None,
    iban: str | None = None,
    bic: str | None = None,
    kontoinhaber: str | None = None,
    mandatsreferenz: str | None = None,
    unterschriftsdatum: str | None = None,
    gueltig_ab: str | None = None,
    gueltig_bis: str | None = None,
    aktiv: bool | None = None,
) -> dict:
    """Manage SEPA mandates.

    action: list | create | update | deactivate
    """
    async with get_mcp_session() as session:
        svc = FinanzenService(session)

        if action == "list":
            items, total = await svc.get_mandate(aktiv_filter=aktiv)
            await session.commit()
            return {"items": items, "total": total}

        if action == "create":
            if not all([mitglied_id, iban, kontoinhaber, mandatsreferenz]):
                return {
                    "error": "mitglied_id, iban, kontoinhaber und mandatsreferenz sind erforderlich."
                }
            data = {
                "mitglied_id": mitglied_id,
                "iban": iban,
                "bic": bic,
                "kontoinhaber": kontoinhaber,
                "mandatsreferenz": mandatsreferenz,
                "unterschriftsdatum": date.fromisoformat(unterschriftsdatum) if unterschriftsdatum else date.today(),
                "gueltig_ab": date.fromisoformat(gueltig_ab) if gueltig_ab else date.today(),
                "gueltig_bis": date.fromisoformat(gueltig_bis) if gueltig_bis else None,
            }
            try:
                mandat = await svc.create_mandat(data)
            except Exception as exc:
                return {"error": str(exc)}
            await session.commit()
            return {
                "id": mandat.id,
                "mitglied_id": mandat.mitglied_id,
                "iban": mandat.iban,
                "mandatsreferenz": mandat.mandatsreferenz,
                "aktiv": mandat.aktiv,
                "message": "SEPA-Mandat erfolgreich erstellt.",
            }

        if action == "update":
            if mandat_id is None:
                return {"error": "mandat_id ist erforderlich."}
            data = {}
            if iban is not None:
                data["iban"] = iban
            if bic is not None:
                data["bic"] = bic
            if kontoinhaber is not None:
                data["kontoinhaber"] = kontoinhaber
            if mandatsreferenz is not None:
                data["mandatsreferenz"] = mandatsreferenz
            if unterschriftsdatum is not None:
                data["unterschriftsdatum"] = date.fromisoformat(unterschriftsdatum)
            if gueltig_ab is not None:
                data["gueltig_ab"] = date.fromisoformat(gueltig_ab)
            if gueltig_bis is not None:
                data["gueltig_bis"] = date.fromisoformat(gueltig_bis)
            try:
                mandat = await svc.update_mandat(mandat_id, data)
            except ValueError as exc:
                return {"error": str(exc)}
            await session.commit()
            return {
                "id": mandat.id,
                "iban": mandat.iban,
                "mandatsreferenz": mandat.mandatsreferenz,
                "message": "SEPA-Mandat erfolgreich aktualisiert.",
            }

        if action == "deactivate":
            if mandat_id is None:
                return {"error": "mandat_id ist erforderlich."}
            try:
                mandat = await svc.deactivate_mandat(mandat_id)
            except ValueError as exc:
                return {"error": str(exc)}
            await session.commit()
            return {
                "id": mandat.id,
                "aktiv": mandat.aktiv,
                "message": "SEPA-Mandat deaktiviert.",
            }

        return {"error": f"Unbekannte Aktion: {action}. Erlaubt: list, create, update, deactivate."}


@mcp.tool(
    description="Kostenstellen verwalten: auflisten, erstellen, aktualisieren, loeschen."
)
async def kostenstellen_verwalten(
    action: str = "list",
    kostenstelle_id: int | None = None,
    name: str | None = None,
    beschreibung: str | None = None,
    abteilung_id: int | None = None,
    budget: float | None = None,
    freigabelimit: float | None = None,
) -> dict:
    """Manage cost centers.

    action: list | create | update | delete
    """
    async with get_mcp_session() as session:
        svc = FinanzenService(session)

        if action == "list":
            centers = await svc.get_cost_centers()
            await session.commit()
            return {
                "items": [
                    {
                        "id": ks.id,
                        "name": ks.name,
                        "beschreibung": ks.beschreibung,
                        "abteilung_id": ks.abteilung_id,
                        "budget": float(ks.budget) if ks.budget else None,
                        "freigabelimit": float(ks.freigabelimit) if ks.freigabelimit else None,
                    }
                    for ks in centers
                ]
            }

        if action == "create":
            if not name:
                return {"error": "Name ist erforderlich."}
            data = {"name": name}
            if beschreibung is not None:
                data["beschreibung"] = beschreibung
            if abteilung_id is not None:
                data["abteilung_id"] = abteilung_id
            if budget is not None:
                data["budget"] = Decimal(str(budget))
            if freigabelimit is not None:
                data["freigabelimit"] = Decimal(str(freigabelimit))
            try:
                ks = await svc.create_cost_center(data)
            except Exception as exc:
                return {"error": str(exc)}
            await session.commit()
            return {
                "id": ks.id,
                "name": ks.name,
                "budget": float(ks.budget) if ks.budget else None,
                "message": "Kostenstelle erfolgreich erstellt.",
            }

        if action == "update":
            if kostenstelle_id is None:
                return {"error": "kostenstelle_id ist erforderlich."}
            data = {}
            if name is not None:
                data["name"] = name
            if beschreibung is not None:
                data["beschreibung"] = beschreibung
            if abteilung_id is not None:
                data["abteilung_id"] = abteilung_id
            if budget is not None:
                data["budget"] = Decimal(str(budget))
            if freigabelimit is not None:
                data["freigabelimit"] = Decimal(str(freigabelimit))
            try:
                ks = await svc.update_cost_center(kostenstelle_id, data)
            except ValueError as exc:
                return {"error": str(exc)}
            await session.commit()
            return {
                "id": ks.id,
                "name": ks.name,
                "budget": float(ks.budget) if ks.budget else None,
                "message": "Kostenstelle erfolgreich aktualisiert.",
            }

        if action == "delete":
            if kostenstelle_id is None:
                return {"error": "kostenstelle_id ist erforderlich."}
            try:
                await svc.delete_cost_center(kostenstelle_id)
            except ValueError as exc:
                return {"error": str(exc)}
            await session.commit()
            return {"message": f"Kostenstelle {kostenstelle_id} erfolgreich geloescht."}

        return {"error": f"Unbekannte Aktion: {action}. Erlaubt: list, create, update, delete."}
