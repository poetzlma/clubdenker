"""MCP tools for member (Mitglieder) management."""

from __future__ import annotations

from datetime import date
from typing import Any

from sportverein.mcp.server import mcp
from sportverein.mcp.session import get_mcp_session
from sportverein.models.mitglied import BeitragKategorie, MitgliedStatus
from sportverein.services.datenschutz import DatenschutzService
from sportverein.services.mitglieder import (
    MitgliedCreate,
    MitgliedFilter,
    MitgliedUpdate,
    MitgliederService,
)


def _mitglied_to_dict(m: Any) -> dict:
    """Convert a Mitglied ORM object to a plain dict."""
    return {
        "id": m.id,
        "mitgliedsnummer": m.mitgliedsnummer,
        "vorname": m.vorname,
        "nachname": m.nachname,
        "email": m.email,
        "telefon": m.telefon,
        "geburtsdatum": m.geburtsdatum.isoformat() if m.geburtsdatum else None,
        "strasse": m.strasse,
        "plz": m.plz,
        "ort": m.ort,
        "eintrittsdatum": m.eintrittsdatum.isoformat() if m.eintrittsdatum else None,
        "austrittsdatum": m.austrittsdatum.isoformat() if m.austrittsdatum else None,
        "status": m.status.value if m.status else None,
        "beitragskategorie": m.beitragskategorie.value if m.beitragskategorie else None,
        "notizen": m.notizen,
    }


def _mitglied_to_dict_with_abteilungen(m: Any) -> dict:
    """Convert a Mitglied ORM object including departments."""
    d = _mitglied_to_dict(m)
    d["abteilungen"] = [
        {
            "id": ma.abteilung.id,
            "name": ma.abteilung.name,
            "beitrittsdatum": ma.beitrittsdatum.isoformat() if ma.beitrittsdatum else None,
        }
        for ma in (m.abteilungen or [])
    ]
    return d


@mcp.tool(description="Mitglieder suchen und filtern. Gibt eine paginierte Liste zurück.")
async def mitglieder_suchen(
    name: str | None = None,
    status: str | None = None,
    abteilung_id: int | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    async with get_mcp_session() as session:
        svc = MitgliederService(session)
        filters = MitgliedFilter(
            name=name,
            status=MitgliedStatus(status) if status else None,
            abteilung_id=abteilung_id,
            page=page,
            page_size=page_size,
        )
        members, total = await svc.search_members(filters)
        await session.commit()
        return {
            "items": [_mitglied_to_dict(m) for m in members],
            "total": total,
            "page": page,
            "page_size": page_size,
        }


@mcp.tool(description="Details eines Mitglieds abrufen, inklusive Abteilungszugehörigkeiten.")
async def mitglied_details(member_id: int) -> dict:
    async with get_mcp_session() as session:
        svc = MitgliederService(session)
        member = await svc.get_member(member_id)
        if member is None:
            return {"error": f"Mitglied mit ID {member_id} nicht gefunden."}
        await session.commit()
        return _mitglied_to_dict_with_abteilungen(member)


@mcp.tool(description="Neues Mitglied anlegen. Gibt das erstellte Mitglied zurück.")
async def mitglied_anlegen(
    vorname: str,
    nachname: str,
    email: str,
    geburtsdatum: str,
    telefon: str | None = None,
    strasse: str | None = None,
    plz: str | None = None,
    ort: str | None = None,
    eintrittsdatum: str | None = None,
    status: str = "aktiv",
    beitragskategorie: str = "erwachsene",
    notizen: str | None = None,
) -> dict:
    async with get_mcp_session() as session:
        svc = MitgliederService(session)
        data = MitgliedCreate(
            vorname=vorname,
            nachname=nachname,
            email=email,
            geburtsdatum=date.fromisoformat(geburtsdatum),
            telefon=telefon,
            strasse=strasse,
            plz=plz,
            ort=ort,
            eintrittsdatum=date.fromisoformat(eintrittsdatum) if eintrittsdatum else None,
            status=MitgliedStatus(status),
            beitragskategorie=BeitragKategorie(beitragskategorie),
            notizen=notizen,
        )
        member = await svc.create_member(data)
        await session.commit()
        return _mitglied_to_dict(member)


@mcp.tool(description="Mitgliedsdaten aktualisieren. Nur übergebene Felder werden geändert.")
async def mitglied_aktualisieren(
    member_id: int,
    vorname: str | None = None,
    nachname: str | None = None,
    email: str | None = None,
    telefon: str | None = None,
    geburtsdatum: str | None = None,
    strasse: str | None = None,
    plz: str | None = None,
    ort: str | None = None,
    status: str | None = None,
    beitragskategorie: str | None = None,
    notizen: str | None = None,
) -> dict:
    async with get_mcp_session() as session:
        svc = MitgliederService(session)
        update_fields: dict[str, Any] = {}
        if vorname is not None:
            update_fields["vorname"] = vorname
        if nachname is not None:
            update_fields["nachname"] = nachname
        if email is not None:
            update_fields["email"] = email
        if telefon is not None:
            update_fields["telefon"] = telefon
        if geburtsdatum is not None:
            update_fields["geburtsdatum"] = date.fromisoformat(geburtsdatum)
        if strasse is not None:
            update_fields["strasse"] = strasse
        if plz is not None:
            update_fields["plz"] = plz
        if ort is not None:
            update_fields["ort"] = ort
        if status is not None:
            update_fields["status"] = status
        if beitragskategorie is not None:
            update_fields["beitragskategorie"] = beitragskategorie
        if notizen is not None:
            update_fields["notizen"] = notizen

        data = MitgliedUpdate(**update_fields)
        member = await svc.update_member(member_id, data)
        await session.commit()
        return _mitglied_to_dict(member)


@mcp.tool(description="Mitgliedschaft kündigen. Setzt den Status auf 'gekuendigt'.")
async def mitglied_kuendigen(
    member_id: int,
    austrittsdatum: str | None = None,
) -> dict:
    async with get_mcp_session() as session:
        svc = MitgliederService(session)
        dt = date.fromisoformat(austrittsdatum) if austrittsdatum else None
        member = await svc.cancel_member(member_id, austrittsdatum=dt)
        await session.commit()
        return _mitglied_to_dict(member)


@mcp.tool(description="Mitglied einer Abteilung zuordnen.")
async def mitglied_abteilung_zuordnen(
    member_id: int,
    abteilung_id: int,
) -> dict:
    async with get_mcp_session() as session:
        svc = MitgliederService(session)
        assoc = await svc.assign_department(member_id, abteilung_id)
        await session.commit()
        return {
            "mitglied_id": assoc.mitglied_id,
            "abteilung_id": assoc.abteilung_id,
            "beitrittsdatum": assoc.beitrittsdatum.isoformat() if assoc.beitrittsdatum else None,
            "message": "Abteilung erfolgreich zugeordnet.",
        }


@mcp.tool(description="Mitglied aus einer Abteilung entfernen.")
async def mitglied_abteilung_entfernen(
    member_id: int,
    abteilung_id: int,
) -> dict:
    async with get_mcp_session() as session:
        svc = MitgliederService(session)
        removed = await svc.remove_department(member_id, abteilung_id)
        await session.commit()
        if not removed:
            return {"error": "Zuordnung nicht gefunden."}
        return {
            "mitglied_id": member_id,
            "abteilung_id": abteilung_id,
            "message": "Abteilung erfolgreich entfernt.",
        }


@mcp.tool(description="Datenschutz-Einwilligung eines Mitglieds setzen (E-Mail, Foto).")
async def datenschutz_einwilligung_setzen(
    member_id: int,
    einwilligung: bool,
) -> dict:
    async with get_mcp_session() as session:
        svc = DatenschutzService(session)
        try:
            member = await svc.set_consent(member_id, einwilligung)
        except ValueError as exc:
            return {"error": str(exc)}
        await session.commit()
        return {
            "mitglied_id": member.id,
            "dsgvo_einwilligung": member.dsgvo_einwilligung,
            "einwilligung_datum": member.einwilligung_datum.isoformat()
            if member.einwilligung_datum
            else None,
            "message": "Einwilligung erfolgreich aktualisiert.",
        }


@mcp.tool(
    description="DSGVO-Auskunft: Alle gespeicherten Daten eines Mitglieds exportieren (Art. 15 DSGVO)."
)
async def datenschutz_auskunft(member_id: int) -> dict:
    async with get_mcp_session() as session:
        svc = DatenschutzService(session)
        try:
            data = await svc.generate_auskunft(member_id)
        except ValueError as exc:
            return {"error": str(exc)}
        await session.commit()
        return data


@mcp.tool(description="DSGVO-Loeschfrist fuer ein Mitglied planen (Aufbewahrungsfrist in Tagen).")
async def datenschutz_loeschfrist_planen(
    member_id: int,
    retention_days: int = 3650,
) -> dict:
    """Schedule member data deletion after retention period."""
    async with get_mcp_session() as session:
        svc = DatenschutzService(session)
        try:
            member = await svc.schedule_deletion(member_id, retention_days)
        except ValueError as exc:
            return {"error": str(exc)}
        await session.commit()
        return {
            "mitglied_id": member.id,
            "loesch_datum": member.loesch_datum.isoformat() if member.loesch_datum else None,
            "message": f"Loeschfrist gesetzt auf {member.loesch_datum}.",
        }


@mcp.tool(
    description="DSGVO: Personenbezogene Daten eines Mitglieds anonymisieren (Art. 17 DSGVO Recht auf Loeschung)."
)
async def datenschutz_mitglied_loeschen(member_id: int) -> dict:
    """Anonymize a member's personal data for DSGVO compliance."""
    async with get_mcp_session() as session:
        svc = DatenschutzService(session)
        try:
            member = await svc.delete_member_data(member_id)
        except ValueError as exc:
            return {"error": str(exc)}
        await session.commit()
        return {
            "mitglied_id": member.id,
            "geloescht_am": member.geloescht_am.isoformat() if member.geloescht_am else None,
            "message": "Personenbezogene Daten wurden DSGVO-konform anonymisiert.",
        }


@mcp.tool(
    description="DSGVO: Ausstehende Datenlöschungen anzeigen (Mitglieder mit abgelaufener Loeschfrist)."
)
async def datenschutz_ausstehende_loeschungen() -> dict:
    """List members pending data deletion."""
    async with get_mcp_session() as session:
        svc = DatenschutzService(session)
        members = await svc.get_pending_deletions()
        await session.commit()
        return {
            "ausstehend": [
                {
                    "mitglied_id": m.id,
                    "name": f"{m.vorname} {m.nachname}",
                    "loesch_datum": m.loesch_datum.isoformat() if m.loesch_datum else None,
                    "status": m.status.value if m.status else None,
                }
                for m in members
            ],
            "count": len(members),
        }
