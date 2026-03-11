"""Training group, attendance, and trainer license management service."""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from sportverein.models.training import (
    Anwesenheit,
    Lizenztyp,
    TrainerLizenz,
    Trainingsgruppe,
    Wochentag,
)


class TrainingService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # -- Trainingsgruppen CRUD -----------------------------------------------

    async def list_trainingsgruppen(
        self,
        abteilung_id: int | None = None,
        aktiv: bool | None = True,
    ) -> list[Trainingsgruppe]:
        """List training groups, optionally filtered by department and active status."""
        query = select(Trainingsgruppe).order_by(Trainingsgruppe.name)
        if abteilung_id is not None:
            query = query.where(Trainingsgruppe.abteilung_id == abteilung_id)
        if aktiv is not None:
            query = query.where(Trainingsgruppe.aktiv == aktiv)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_trainingsgruppe(self, gruppe_id: int) -> Trainingsgruppe | None:
        """Get a single training group by ID."""
        result = await self.session.execute(
            select(Trainingsgruppe).where(Trainingsgruppe.id == gruppe_id)
        )
        return result.scalar_one_or_none()

    async def create_trainingsgruppe(
        self,
        name: str,
        abteilung_id: int,
        wochentag: Wochentag,
        uhrzeit: str,
        *,
        trainer: str | None = None,
        dauer_minuten: int = 90,
        max_teilnehmer: int | None = None,
        ort: str | None = None,
        aktiv: bool = True,
    ) -> Trainingsgruppe:
        """Create a new training group."""
        gruppe = Trainingsgruppe(
            name=name,
            abteilung_id=abteilung_id,
            wochentag=wochentag,
            uhrzeit=uhrzeit,
            trainer=trainer,
            dauer_minuten=dauer_minuten,
            max_teilnehmer=max_teilnehmer,
            ort=ort,
            aktiv=aktiv,
        )
        self.session.add(gruppe)
        await self.session.flush()
        await self.session.refresh(gruppe)
        return gruppe

    async def update_trainingsgruppe(self, gruppe_id: int, **kwargs: object) -> Trainingsgruppe:
        """Update a training group. Only provided kwargs are changed."""
        gruppe = await self.get_trainingsgruppe(gruppe_id)
        if gruppe is None:
            raise ValueError(f"Trainingsgruppe mit ID {gruppe_id} nicht gefunden.")
        for key, value in kwargs.items():
            if hasattr(gruppe, key):
                setattr(gruppe, key, value)
        await self.session.flush()
        await self.session.refresh(gruppe)
        return gruppe

    async def delete_trainingsgruppe(self, gruppe_id: int) -> None:
        """Delete a training group. Raises if attendance records exist."""
        gruppe = await self.get_trainingsgruppe(gruppe_id)
        if gruppe is None:
            raise ValueError(f"Trainingsgruppe mit ID {gruppe_id} nicht gefunden.")

        count_result = await self.session.execute(
            select(func.count())
            .select_from(Anwesenheit)
            .where(Anwesenheit.trainingsgruppe_id == gruppe_id)
        )
        count = count_result.scalar_one()
        if count > 0:
            raise ValueError(
                f"Trainingsgruppe '{gruppe.name}' kann nicht geloescht werden, "
                f"da noch {count} Anwesenheitseintraege vorhanden sind."
            )
        await self.session.delete(gruppe)
        await self.session.flush()

    # -- Anwesenheit ---------------------------------------------------------

    async def record_anwesenheit(
        self,
        trainingsgruppe_id: int,
        datum: date,
        teilnehmer: list[dict],
    ) -> list[Anwesenheit]:
        """Record attendance for a training session.

        teilnehmer is a list of dicts: [{"mitglied_id": int, "anwesend": bool, "notiz": str|None}]
        Uses upsert semantics: existing records for the same (gruppe, member, date) are updated.
        """
        results: list[Anwesenheit] = []
        for t in teilnehmer:
            mitglied_id = t["mitglied_id"]
            anwesend = t.get("anwesend", True)
            notiz = t.get("notiz")

            # Check for existing record
            existing_result = await self.session.execute(
                select(Anwesenheit).where(
                    Anwesenheit.trainingsgruppe_id == trainingsgruppe_id,
                    Anwesenheit.mitglied_id == mitglied_id,
                    Anwesenheit.datum == datum,
                )
            )
            existing = existing_result.scalar_one_or_none()

            if existing is not None:
                existing.anwesend = anwesend
                existing.notiz = notiz
                results.append(existing)
            else:
                record = Anwesenheit(
                    trainingsgruppe_id=trainingsgruppe_id,
                    mitglied_id=mitglied_id,
                    datum=datum,
                    anwesend=anwesend,
                    notiz=notiz,
                )
                self.session.add(record)
                results.append(record)

        try:
            await self.session.flush()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ValueError(f"Fehler beim Erfassen der Anwesenheit: {exc}") from exc

        for r in results:
            await self.session.refresh(r)
        return results

    async def get_anwesenheit(
        self,
        trainingsgruppe_id: int | None = None,
        mitglied_id: int | None = None,
        datum_von: date | None = None,
        datum_bis: date | None = None,
    ) -> list[Anwesenheit]:
        """Get attendance records with filters."""
        query = select(Anwesenheit).order_by(Anwesenheit.datum.desc())
        if trainingsgruppe_id is not None:
            query = query.where(Anwesenheit.trainingsgruppe_id == trainingsgruppe_id)
        if mitglied_id is not None:
            query = query.where(Anwesenheit.mitglied_id == mitglied_id)
        if datum_von is not None:
            query = query.where(Anwesenheit.datum >= datum_von)
        if datum_bis is not None:
            query = query.where(Anwesenheit.datum <= datum_bis)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_anwesenheit_statistik(self, abteilung_id: int, wochen: int = 12) -> dict:
        """Get attendance statistics for heatmap: 7 days x N weeks with intensity levels.

        Returns a dict with:
        - heatmap: list of {day: int(0-6), cells: list[int]} where cells are intensity 0-4
        - total_sessions: int
        - total_present: int
        - avg_attendance_pct: float
        """
        end_date = date.today()
        start_date = end_date - timedelta(weeks=wochen)

        # Get all attendance records for this department's training groups
        query = (
            select(Anwesenheit)
            .join(Trainingsgruppe, Anwesenheit.trainingsgruppe_id == Trainingsgruppe.id)
            .where(
                Trainingsgruppe.abteilung_id == abteilung_id,
                Anwesenheit.datum >= start_date,
                Anwesenheit.datum <= end_date,
            )
        )
        result = await self.session.execute(query)
        records = list(result.scalars().all())

        # Build a grid: 7 days x wochen weeks
        # day 0 = Monday, 6 = Sunday
        grid: dict[tuple[int, int], list[bool]] = {}
        for record in records:
            day = record.datum.weekday()  # 0=Monday
            week_offset = (end_date - record.datum).days // 7
            if week_offset < wochen:
                week_idx = wochen - 1 - week_offset
                key = (day, week_idx)
                if key not in grid:
                    grid[key] = []
                grid[key].append(record.anwesend)

        heatmap = []
        for day in range(7):
            cells = []
            for week in range(wochen):
                entries = grid.get((day, week), [])
                if not entries:
                    cells.append(0)
                else:
                    pct = sum(1 for e in entries if e) / len(entries)
                    if pct >= 0.8:
                        cells.append(4)
                    elif pct >= 0.6:
                        cells.append(3)
                    elif pct >= 0.4:
                        cells.append(2)
                    elif pct > 0:
                        cells.append(1)
                    else:
                        cells.append(0)
            heatmap.append({"day": day, "cells": cells})

        total_records = len(records)
        total_present = sum(1 for r in records if r.anwesend)
        avg_pct = (total_present / total_records * 100) if total_records > 0 else 0.0

        return {
            "heatmap": heatmap,
            "total_sessions": total_records,
            "total_present": total_present,
            "avg_attendance_pct": round(avg_pct, 1),
        }

    async def get_mitglied_anwesenheit(self, mitglied_id: int, wochen: int = 12) -> dict:
        """Get attendance rate for a single member over the last N weeks."""
        end_date = date.today()
        start_date = end_date - timedelta(weeks=wochen)

        query = select(Anwesenheit).where(
            Anwesenheit.mitglied_id == mitglied_id,
            Anwesenheit.datum >= start_date,
            Anwesenheit.datum <= end_date,
        )
        result = await self.session.execute(query)
        records = list(result.scalars().all())

        total = len(records)
        present = sum(1 for r in records if r.anwesend)
        pct = (present / total * 100) if total > 0 else 0.0

        return {
            "mitglied_id": mitglied_id,
            "wochen": wochen,
            "total_eintraege": total,
            "anwesend": present,
            "abwesend": total - present,
            "anwesenheit_pct": round(pct, 1),
        }

    # -- Trainer-Lizenzen -----------------------------------------------------

    async def list_licenses(
        self,
        mitglied_id: int | None = None,
        expired: bool | None = None,
    ) -> list[TrainerLizenz]:
        """List trainer licenses, optionally filtered by member or expired status."""
        query = select(TrainerLizenz).order_by(TrainerLizenz.ablaufdatum)
        if mitglied_id is not None:
            query = query.where(TrainerLizenz.mitglied_id == mitglied_id)
        if expired is True:
            query = query.where(TrainerLizenz.ablaufdatum < date.today())
        elif expired is False:
            query = query.where(TrainerLizenz.ablaufdatum >= date.today())
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create_license(
        self,
        mitglied_id: int,
        lizenztyp: Lizenztyp,
        bezeichnung: str,
        ausstellungsdatum: date,
        ablaufdatum: date,
        *,
        lizenznummer: str | None = None,
        ausstellende_stelle: str | None = None,
    ) -> TrainerLizenz:
        """Create a new trainer license record."""
        lizenz = TrainerLizenz(
            mitglied_id=mitglied_id,
            lizenztyp=lizenztyp,
            bezeichnung=bezeichnung,
            ausstellungsdatum=ausstellungsdatum,
            ablaufdatum=ablaufdatum,
            lizenznummer=lizenznummer,
            ausstellende_stelle=ausstellende_stelle,
        )
        self.session.add(lizenz)
        await self.session.flush()
        await self.session.refresh(lizenz)
        return lizenz

    async def get_expiring_licenses(self, days: int = 90) -> list[TrainerLizenz]:
        """Find licenses expiring within the next N days (not already expired)."""
        today = date.today()
        deadline = today + timedelta(days=days)
        query = (
            select(TrainerLizenz)
            .where(
                TrainerLizenz.ablaufdatum >= today,
                TrainerLizenz.ablaufdatum <= deadline,
            )
            .order_by(TrainerLizenz.ablaufdatum)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def delete_license(self, license_id: int) -> None:
        """Delete a trainer license by ID."""
        result = await self.session.execute(
            select(TrainerLizenz).where(TrainerLizenz.id == license_id)
        )
        lizenz = result.scalar_one_or_none()
        if lizenz is None:
            raise ValueError(f"Lizenz mit ID {license_id} nicht gefunden.")
        await self.session.delete(lizenz)
        await self.session.flush()
