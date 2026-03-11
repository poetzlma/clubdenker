"""MCP tools for training and attendance management."""

from __future__ import annotations

from datetime import date
from typing import Any

from sportverein.mcp.server import mcp
from sportverein.mcp.session import get_mcp_session
from sportverein.models.training import Wochentag
from sportverein.services.training import TrainingService


def _gruppe_to_dict(g: Any) -> dict:
    """Convert a Trainingsgruppe ORM object to a plain dict."""
    return {
        "id": g.id,
        "name": g.name,
        "abteilung_id": g.abteilung_id,
        "trainer": g.trainer,
        "wochentag": g.wochentag.value if g.wochentag else None,
        "uhrzeit": g.uhrzeit,
        "dauer_minuten": g.dauer_minuten,
        "max_teilnehmer": g.max_teilnehmer,
        "ort": g.ort,
        "aktiv": g.aktiv,
    }


def _anwesenheit_to_dict(a: Any) -> dict:
    """Convert an Anwesenheit ORM object to a plain dict."""
    return {
        "id": a.id,
        "trainingsgruppe_id": a.trainingsgruppe_id,
        "mitglied_id": a.mitglied_id,
        "datum": a.datum.isoformat() if a.datum else None,
        "anwesend": a.anwesend,
        "notiz": a.notiz,
    }


@mcp.tool(
    description=("Trainingsgruppen verwalten: auflisten, erstellen, aktualisieren, loeschen.")
)
async def training_verwalten(
    action: str,
    gruppe_id: int | None = None,
    name: str | None = None,
    abteilung_id: int | None = None,
    wochentag: str | None = None,
    uhrzeit: str | None = None,
    trainer: str | None = None,
    dauer_minuten: int | None = None,
    max_teilnehmer: int | None = None,
    ort: str | None = None,
    aktiv: bool | None = None,
) -> dict:
    """Manage training groups.

    action: "list", "create", "update", "delete"
    """
    async with get_mcp_session() as session:
        svc = TrainingService(session)

        if action == "list":
            gruppen = await svc.list_trainingsgruppen(abteilung_id=abteilung_id, aktiv=aktiv)
            await session.commit()
            return {"items": [_gruppe_to_dict(g) for g in gruppen]}

        if action == "create":
            if not name or abteilung_id is None or not wochentag or not uhrzeit:
                return {
                    "error": "Felder name, abteilung_id, wochentag und uhrzeit sind erforderlich."
                }
            kwargs: dict[str, Any] = {}
            if trainer is not None:
                kwargs["trainer"] = trainer
            if dauer_minuten is not None:
                kwargs["dauer_minuten"] = dauer_minuten
            if max_teilnehmer is not None:
                kwargs["max_teilnehmer"] = max_teilnehmer
            if ort is not None:
                kwargs["ort"] = ort
            try:
                parsed_wochentag = Wochentag(wochentag)
            except ValueError:
                return {"error": f"Ungültiger Wochentag: {wochentag}. Erlaubt: {', '.join(w.value for w in Wochentag)}"}
            gruppe = await svc.create_trainingsgruppe(
                name=name,
                abteilung_id=abteilung_id,
                wochentag=parsed_wochentag,
                uhrzeit=uhrzeit,
                **kwargs,
            )
            await session.commit()
            return _gruppe_to_dict(gruppe)

        if action == "update":
            if gruppe_id is None:
                return {"error": "gruppe_id ist erforderlich fuer 'update'."}
            updates: dict[str, Any] = {}
            if name is not None:
                updates["name"] = name
            if abteilung_id is not None:
                updates["abteilung_id"] = abteilung_id
            if wochentag is not None:
                try:
                    updates["wochentag"] = Wochentag(wochentag)
                except ValueError:
                    return {"error": f"Ungültiger Wochentag: {wochentag}. Erlaubt: {', '.join(w.value for w in Wochentag)}"}
            if uhrzeit is not None:
                updates["uhrzeit"] = uhrzeit
            if trainer is not None:
                updates["trainer"] = trainer
            if dauer_minuten is not None:
                updates["dauer_minuten"] = dauer_minuten
            if max_teilnehmer is not None:
                updates["max_teilnehmer"] = max_teilnehmer
            if ort is not None:
                updates["ort"] = ort
            if aktiv is not None:
                updates["aktiv"] = aktiv
            try:
                gruppe = await svc.update_trainingsgruppe(gruppe_id, **updates)
            except ValueError as exc:
                return {"error": str(exc)}
            await session.commit()
            return _gruppe_to_dict(gruppe)

        if action == "delete":
            if gruppe_id is None:
                return {"error": "gruppe_id ist erforderlich fuer 'delete'."}
            try:
                await svc.delete_trainingsgruppe(gruppe_id)
            except ValueError as exc:
                return {"error": str(exc)}
            await session.commit()
            return {"message": "Trainingsgruppe erfolgreich geloescht."}

        return {"error": f"Unbekannte Aktion: {action}. Erlaubt: list, create, update, delete."}


@mcp.tool(description="Anwesenheit fuer ein Training erfassen.")
async def anwesenheit_erfassen(
    trainingsgruppe_id: int,
    datum: str,
    teilnehmer: list[dict],
) -> dict:
    """Record attendance for a training session.

    teilnehmer: list of {"mitglied_id": int, "anwesend": bool, "notiz": str|None}
    """
    async with get_mcp_session() as session:
        svc = TrainingService(session)
        try:
            parsed_datum = date.fromisoformat(datum)
        except ValueError:
            return {"error": f"Ungültiges Datum: {datum}. Format: YYYY-MM-DD"}
        try:
            records = await svc.record_anwesenheit(
                trainingsgruppe_id=trainingsgruppe_id,
                datum=parsed_datum,
                teilnehmer=teilnehmer,
            )
        except ValueError as exc:
            return {"error": str(exc)}
        await session.commit()
        return {
            "message": f"Anwesenheit fuer {len(records)} Teilnehmer erfasst.",
            "items": [_anwesenheit_to_dict(r) for r in records],
        }


@mcp.tool(description="Anwesenheitsstatistik einer Abteilung abrufen.")
async def anwesenheit_statistik(
    abteilung_id: int,
    wochen: int = 12,
) -> dict:
    """Get attendance statistics for a department."""
    async with get_mcp_session() as session:
        svc = TrainingService(session)
        stats = await svc.get_anwesenheit_statistik(abteilung_id, wochen=wochen)
        await session.commit()
        return stats


@mcp.tool(description="Anwesenheitseinträge abfragen und filtern.")
async def anwesenheit_abrufen(
    trainingsgruppe_id: int | None = None,
    mitglied_id: int | None = None,
    datum_von: str | None = None,
    datum_bis: str | None = None,
) -> dict:
    """Query attendance records with optional filters."""
    async with get_mcp_session() as session:
        svc = TrainingService(session)
        try:
            parsed_von = date.fromisoformat(datum_von) if datum_von else None
            parsed_bis = date.fromisoformat(datum_bis) if datum_bis else None
        except ValueError:
            return {"error": "Ungültiges Datum. Format: YYYY-MM-DD"}
        records = await svc.get_anwesenheit(
            trainingsgruppe_id=trainingsgruppe_id,
            mitglied_id=mitglied_id,
            datum_von=parsed_von,
            datum_bis=parsed_bis,
        )
        await session.commit()
        return {"items": [_anwesenheit_to_dict(r) for r in records]}


@mcp.tool(description="Anwesenheitsstatistik für ein einzelnes Mitglied abrufen.")
async def anwesenheit_mitglied_statistik(
    mitglied_id: int,
    wochen: int = 12,
) -> dict:
    """Get attendance rate for a single member."""
    async with get_mcp_session() as session:
        svc = TrainingService(session)
        stats = await svc.get_mitglied_anwesenheit(mitglied_id, wochen=wochen)
        await session.commit()
        return stats
