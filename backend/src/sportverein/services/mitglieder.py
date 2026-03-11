"""Member management service for Sportverein."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel
from sqlalchemy import func, select, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sportverein.models.mitglied import (
    Abteilung,
    BeitragKategorie,
    Mitglied,
    MitgliedAbteilung,
    MitgliedStatus,
)


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class MitgliedCreate(BaseModel):
    vorname: str
    nachname: str
    email: str
    telefon: str | None = None
    geburtsdatum: date
    strasse: str | None = None
    plz: str | None = None
    ort: str | None = None
    eintrittsdatum: date | None = None
    status: MitgliedStatus = MitgliedStatus.aktiv
    beitragskategorie: BeitragKategorie = BeitragKategorie.erwachsene
    notizen: str | None = None


class MitgliedUpdate(BaseModel):
    vorname: str | None = None
    nachname: str | None = None
    email: str | None = None
    telefon: str | None = None
    geburtsdatum: date | None = None
    strasse: str | None = None
    plz: str | None = None
    ort: str | None = None
    status: MitgliedStatus | None = None
    beitragskategorie: BeitragKategorie | None = None
    notizen: str | None = None


class MitgliedFilter(BaseModel):
    name: str | None = None
    abteilung_id: int | None = None
    status: MitgliedStatus | None = None
    beitragskategorie: BeitragKategorie | None = None
    page: int = 1
    page_size: int = 20
    sort_by: str = "nachname"
    sort_order: Literal["asc", "desc"] = "asc"


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class MitgliederService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # -- helpers -------------------------------------------------------------

    async def _next_mitgliedsnummer(self) -> str:
        # Find the max existing number to avoid collisions
        result = await self.session.execute(
            select(Mitglied.mitgliedsnummer)
            .where(Mitglied.mitgliedsnummer.like("M-%"))
            .order_by(Mitglied.mitgliedsnummer.desc())
            .limit(1)
        )
        last: str | None = result.scalar_one_or_none()
        if last is not None:
            try:
                num = int(last.split("-")[1])
                return f"M-{num + 1:04d}"
            except (ValueError, IndexError):
                pass
        return "M-0001"

    # -- CRUD ----------------------------------------------------------------

    async def create_member(self, data: MitgliedCreate) -> Mitglied:
        nummer = await self._next_mitgliedsnummer()
        values = data.model_dump(exclude_none=False)
        # Remove None eintrittsdatum so server_default kicks in
        if values.get("eintrittsdatum") is None:
            values.pop("eintrittsdatum", None)
        member = Mitglied(mitgliedsnummer=nummer, **values)
        self.session.add(member)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ValueError(f"Duplicate entry: {exc}") from exc
        await self.session.refresh(member)
        return member

    async def get_member(self, member_id: int) -> Mitglied | None:
        result = await self.session.execute(
            select(Mitglied)
            .where(Mitglied.id == member_id)
            .options(selectinload(Mitglied.abteilungen).selectinload(MitgliedAbteilung.abteilung))
        )
        return result.scalar_one_or_none()

    async def get_member_by_number(self, nummer: str) -> Mitglied | None:
        result = await self.session.execute(
            select(Mitglied).where(Mitglied.mitgliedsnummer == nummer)
        )
        return result.scalar_one_or_none()

    async def update_member(self, member_id: int, data: MitgliedUpdate) -> Mitglied:
        member = await self.get_member(member_id)
        if member is None:
            raise ValueError(f"Member {member_id} not found")
        updates = data.model_dump(exclude_unset=True)
        for key, value in updates.items():
            setattr(member, key, value)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ValueError(f"Duplicate entry: {exc}") from exc
        await self.session.refresh(member)
        return member

    async def cancel_member(self, member_id: int, austrittsdatum: date | None = None) -> Mitglied:
        member = await self.get_member(member_id)
        if member is None:
            raise ValueError(f"Member {member_id} not found")
        member.status = MitgliedStatus.gekuendigt
        member.austrittsdatum = austrittsdatum or date.today()
        await self.session.flush()
        await self.session.refresh(member)
        return member

    # -- search --------------------------------------------------------------

    async def search_members(self, filters: MitgliedFilter) -> tuple[list[Mitglied], int]:
        query = select(Mitglied)
        count_query = select(func.count()).select_from(Mitglied)

        conditions = []

        if filters.name:
            pattern = f"%{filters.name}%"
            name_cond = or_(
                Mitglied.vorname.ilike(pattern),
                Mitglied.nachname.ilike(pattern),
            )
            conditions.append(name_cond)

        if filters.status is not None:
            conditions.append(Mitglied.status == filters.status)

        if filters.beitragskategorie is not None:
            conditions.append(Mitglied.beitragskategorie == filters.beitragskategorie)

        if filters.abteilung_id is not None:
            query = query.join(MitgliedAbteilung)
            count_query = count_query.join(MitgliedAbteilung)
            conditions.append(MitgliedAbteilung.abteilung_id == filters.abteilung_id)

        if conditions:
            query = query.where(*conditions)
            count_query = count_query.where(*conditions)

        # Total count
        total_result = await self.session.execute(count_query)
        total = total_result.scalar_one()

        # Sorting (allowlist to prevent accessing non-column attributes)
        _ALLOWED_SORT = {"nachname", "vorname", "email", "mitgliedsnummer", "eintrittsdatum", "status", "beitragskategorie"}
        sort_field = filters.sort_by if filters.sort_by in _ALLOWED_SORT else "nachname"
        sort_col = getattr(Mitglied, sort_field, Mitglied.nachname)
        if filters.sort_order == "desc":
            sort_col = sort_col.desc()
        else:
            sort_col = sort_col.asc()
        query = query.order_by(sort_col)

        # Pagination
        offset = (filters.page - 1) * filters.page_size
        query = query.offset(offset).limit(filters.page_size)

        result = await self.session.execute(query)
        members = list(result.scalars().all())
        return members, total

    # -- departments ---------------------------------------------------------

    async def assign_department(self, member_id: int, abteilung_id: int) -> MitgliedAbteilung:
        assoc = MitgliedAbteilung(
            mitglied_id=member_id,
            abteilung_id=abteilung_id,
        )
        self.session.add(assoc)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ValueError(f"Assignment already exists: {exc}") from exc
        await self.session.refresh(assoc)
        return assoc

    async def remove_department(self, member_id: int, abteilung_id: int) -> bool:
        result = await self.session.execute(
            select(MitgliedAbteilung).where(
                MitgliedAbteilung.mitglied_id == member_id,
                MitgliedAbteilung.abteilung_id == abteilung_id,
            )
        )
        assoc = result.scalar_one_or_none()
        if assoc is None:
            return False
        await self.session.delete(assoc)
        await self.session.flush()
        return True

    async def get_departments(self) -> list[Abteilung]:
        result = await self.session.execute(select(Abteilung).order_by(Abteilung.name))
        return list(result.scalars().all())

    async def create_department(self, name: str, beschreibung: str | None = None) -> Abteilung:
        """Create a new department."""
        dept = Abteilung(name=name, beschreibung=beschreibung)
        self.session.add(dept)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ValueError(f"Abteilung mit Name '{name}' existiert bereits.") from exc
        await self.session.refresh(dept)
        return dept

    async def update_department(
        self,
        department_id: int,
        name: str | None = None,
        beschreibung: str | None = ...,  # type: ignore[assignment]
    ) -> Abteilung:
        """Update an existing department."""
        result = await self.session.execute(select(Abteilung).where(Abteilung.id == department_id))
        dept = result.scalar_one_or_none()
        if dept is None:
            raise ValueError(f"Abteilung mit ID {department_id} nicht gefunden.")
        if name is not None:
            dept.name = name
        if beschreibung is not ...:
            dept.beschreibung = beschreibung
        try:
            await self.session.flush()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ValueError(f"Abteilung mit Name '{name}' existiert bereits.") from exc
        await self.session.refresh(dept)
        return dept

    async def delete_department(self, department_id: int) -> None:
        """Delete a department. Raises if members are still assigned."""
        result = await self.session.execute(select(Abteilung).where(Abteilung.id == department_id))
        dept = result.scalar_one_or_none()
        if dept is None:
            raise ValueError(f"Abteilung mit ID {department_id} nicht gefunden.")

        count_result = await self.session.execute(
            select(func.count())
            .select_from(MitgliedAbteilung)
            .where(MitgliedAbteilung.abteilung_id == department_id)
        )
        count = count_result.scalar_one()
        if count > 0:
            raise ValueError(
                f"Abteilung '{dept.name}' kann nicht gelöscht werden, "
                f"da noch {count} Mitglied(er) zugeordnet sind."
            )
        await self.session.delete(dept)
        await self.session.flush()

    # -- stats ---------------------------------------------------------------

    async def get_member_stats(self) -> dict:
        # Active / passive counts
        active_result = await self.session.execute(
            select(func.count())
            .select_from(Mitglied)
            .where(Mitglied.status == MitgliedStatus.aktiv)
        )
        total_active = active_result.scalar_one()

        passive_result = await self.session.execute(
            select(func.count())
            .select_from(Mitglied)
            .where(Mitglied.status == MitgliedStatus.passiv)
        )
        total_passive = passive_result.scalar_one()

        # New this month
        today = date.today()
        first_of_month = today.replace(day=1)
        new_result = await self.session.execute(
            select(func.count())
            .select_from(Mitglied)
            .where(Mitglied.eintrittsdatum >= first_of_month)
        )
        new_this_month = new_result.scalar_one()

        # By department
        dept_result = await self.session.execute(
            select(Abteilung.name, func.count(MitgliedAbteilung.id))
            .join(MitgliedAbteilung, Abteilung.id == MitgliedAbteilung.abteilung_id, isouter=True)
            .group_by(Abteilung.id, Abteilung.name)
        )
        by_department = {row[0]: row[1] for row in dept_result.all()}

        return {
            "total_active": total_active,
            "total_passive": total_passive,
            "new_this_month": new_this_month,
            "by_department": by_department,
        }
