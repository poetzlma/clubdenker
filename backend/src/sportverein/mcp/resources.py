"""MCP resources for Sportverein."""

from __future__ import annotations

from sportverein.mcp.server import mcp
from sportverein.mcp.session import get_mcp_session
from sportverein.services.mitglieder import MitgliederService


@mcp.resource(
    "sportverein://abteilungen",
    name="abteilungen",
    description="Liste aller Abteilungen des Sportvereins.",
)
async def abteilungen_resource() -> list[dict]:
    async with get_mcp_session() as session:
        svc = MitgliederService(session)
        departments = await svc.get_departments()
        await session.commit()
        return [
            {
                "id": dept.id,
                "name": dept.name,
                "beschreibung": dept.beschreibung,
            }
            for dept in departments
        ]


@mcp.resource(
    "sportverein://satzung",
    name="satzung",
    description="Vereinssatzung des Sportvereins (Auszug).",
    mime_type="text/plain",
)
async def satzung_resource() -> str:
    return (
        "Satzung des Sportvereins e.V.\n"
        "=============================\n\n"
        "§1 Name und Sitz\n"
        "Der Verein führt den Namen Sportverein e.V. und hat seinen Sitz in Musterstadt.\n\n"
        "§2 Zweck\n"
        "Zweck des Vereins ist die Förderung des Sports und der Jugendpflege.\n\n"
        "§3 Mitgliedschaft\n"
        "Mitglied kann jede natürliche Person werden. Die Aufnahme erfolgt auf schriftlichen Antrag.\n\n"
        "§4 Beiträge\n"
        "Die Mitglieder zahlen Beiträge nach Maßgabe der Beitragsordnung.\n\n"
        "§5 Kündigung\n"
        "Der Austritt ist nur zum Quartalsende möglich und muss schriftlich erklärt werden.\n"
    )


@mcp.resource(
    "sportverein://beitragsordnung",
    name="beitragsordnung",
    description="Aktuelle Beitragsordnung mit Gebührensätzen.",
    mime_type="text/plain",
)
async def beitragsordnung_resource() -> str:
    return (
        "Beitragsordnung des Sportvereins e.V.\n"
        "======================================\n\n"
        "Gültig ab 01.01.2025\n\n"
        "Beitragskategorien und Jahresbeiträge:\n"
        "  - Erwachsene:    240,00 €/Jahr (20,00 €/Monat)\n"
        "  - Jugend:        120,00 €/Jahr (10,00 €/Monat)\n"
        "  - Familie:       360,00 €/Jahr (30,00 €/Monat)\n"
        "  - Passiv:         60,00 €/Jahr ( 5,00 €/Monat)\n"
        "  - Ehrenmitglied:   0,00 €/Jahr (beitragsfrei)\n\n"
        "Hinweise:\n"
        "  - Bei unterjährigem Eintritt wird der Beitrag anteilig berechnet.\n"
        "  - Die Zahlung erfolgt per SEPA-Lastschrift.\n"
        "  - Änderungen der Beitragsordnung bedürfen der Zustimmung der Mitgliederversammlung.\n"
    )
