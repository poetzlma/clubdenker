"""Chat endpoint that routes user questions to services.

In production, this would be connected to an LLM via MCP.
For now, it pattern-matches common queries and returns real data.
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from sportverein.auth.dependencies import get_current_token, get_db_session
from sportverein.services.beitraege import BeitraegeService
from sportverein.services.finanzen import FinanzenService
from sportverein.services.mitglieder import MitgliedFilter, MitgliederService

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    context: str | None = None


class ChatResponse(BaseModel):
    response: str
    data: Any | None = None
    tool_used: str | None = None


def _decimal_to_str(obj: Any) -> Any:
    """Recursively convert Decimal values to strings for JSON serialisation."""
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, dict):
        return {k: _decimal_to_str(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_decimal_to_str(i) for i in obj]
    return obj


@router.post("", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    token: Any = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> ChatResponse:
    """Simple chat endpoint that routes questions to services."""
    msg = body.message.lower().strip()

    # --- Mitglieder stats ---
    if re.search(r"wie\s*viele\s*mitglieder|mitglieder.?statistik|mitglieder.?zahl", msg):
        svc = MitgliederService(session)
        stats = await svc.get_member_stats()
        text = (
            f"Aktuell hat der Verein {stats['total_active']} aktive "
            f"und {stats['total_passive']} passive Mitglieder. "
            f"Diesen Monat sind {stats['new_this_month']} neue Mitglieder beigetreten."
        )
        if stats.get("by_department"):
            parts = [f"{name}: {count}" for name, count in stats["by_department"].items()]
            text += "\n\nNach Abteilung:\n" + "\n".join(parts)
        return ChatResponse(
            response=text,
            data=_decimal_to_str(stats),
            tool_used="MitgliederService.get_member_stats",
        )

    # --- Mitglied search ---
    if re.search(r"suche\s*mitglied|mitglied\s*suchen|finde\s*mitglied", msg):
        # Extract search term after the keyword
        match = re.search(
            r"(?:suche\s*mitglied|mitglied\s*suchen|finde\s*mitglied)\s*(.+)",
            msg,
        )
        search_name = match.group(1).strip() if match else ""
        if not search_name:
            return ChatResponse(
                response="Bitte gib einen Namen an, z.B. 'Suche Mitglied Müller'.",
            )

        svc = MitgliederService(session)
        members, total = await svc.search_members(MitgliedFilter(name=search_name, page_size=5))
        if not members:
            return ChatResponse(
                response=f"Kein Mitglied mit '{search_name}' gefunden.",
                tool_used="MitgliederService.search_members",
            )

        lines = [f"- {m.vorname} {m.nachname} ({m.mitgliedsnummer})" for m in members]
        suffix = f" (und {total - 5} weitere)" if total > 5 else ""
        return ChatResponse(
            response=f"{total} Ergebnis(se) für '{search_name}':{suffix}\n\n" + "\n".join(lines),
            data={"total": total, "shown": len(members)},
            tool_used="MitgliederService.search_members",
        )

    # --- Finanzen / Kassenstand ---
    if re.search(r"kassenstand|finanzen|kontostand|salden|bilanz", msg):
        svc = FinanzenService(session)
        balance = await svc.get_balance_by_sphere()
        total = await svc.get_total_balance()
        parts = [f"- {sphere}: {amount} €" for sphere, amount in balance.items()]
        text = "Kassenstand nach Sphäre:\n\n" + "\n".join(parts) + f"\n\nGesamt: {total} €"
        return ChatResponse(
            response=text,
            data=_decimal_to_str({"by_sphere": balance, "total": total}),
            tool_used="FinanzenService.get_balance_by_sphere",
        )

    # --- Beiträge berechnen ---
    if re.search(r"beitr[äa]ge\s*berechnen|beitrag.?lauf|fee\s*calc", msg):
        year = date.today().year
        # Try to extract a year from the message
        year_match = re.search(r"20\d{2}", msg)
        if year_match:
            year = int(year_match.group())

        svc = BeitraegeService(session)
        fees = await svc.calculate_all_fees(year)
        if not fees:
            return ChatResponse(
                response=f"Keine aktiven Mitglieder für die Beitragsberechnung {year} gefunden.",
                tool_used="BeitraegeService.calculate_all_fees",
            )

        total_sum = sum(f["prorata_betrag"] for f in fees)
        text = (
            f"Beitragsberechnung {year}: {len(fees)} aktive Mitglieder.\n"
            f"Gesamtsumme: {total_sum} €\n\n"
        )
        for f in fees[:10]:
            text += f"- {f['name']}: {f['prorata_betrag']} € ({f['kategorie'].value if hasattr(f['kategorie'], 'value') else f['kategorie']})\n"
        if len(fees) > 10:
            text += f"\n... und {len(fees) - 10} weitere."

        return ChatResponse(
            response=text,
            data=_decimal_to_str({"count": len(fees), "total": total_sum}),
            tool_used="BeitraegeService.calculate_all_fees",
        )

    # --- Fallback: list available commands ---
    return ChatResponse(
        response=(
            "Ich kann dir bei folgenden Themen helfen:\n\n"
            "- **Mitgliederstatistik**: 'Wie viele Mitglieder hat der Verein?'\n"
            "- **Mitglied suchen**: 'Suche Mitglied Müller'\n"
            "- **Kassenstand**: 'Wie ist der Kassenstand?'\n"
            "- **Beiträge berechnen**: 'Beiträge berechnen 2026'\n\n"
            "Stelle einfach eine Frage!"
        ),
    )
