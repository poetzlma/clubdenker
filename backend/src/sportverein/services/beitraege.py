from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sportverein.models.beitrag import BeitragsKategorie
from sportverein.models.finanzen import Rechnung, RechnungStatus
from sportverein.models.mitglied import BeitragKategorie, Mitglied, MitgliedStatus


# Default annual rates per category (used when no DB row exists)
_DEFAULT_RATES: dict[BeitragKategorie, Decimal] = {
    BeitragKategorie.erwachsene: Decimal("240.00"),
    BeitragKategorie.jugend: Decimal("120.00"),
    BeitragKategorie.familie: Decimal("360.00"),
    BeitragKategorie.passiv: Decimal("60.00"),
    BeitragKategorie.ehrenmitglied: Decimal("0.00"),
}


class BeitraegeService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_categories(self) -> list[BeitragsKategorie]:
        """List all fee categories."""
        result = await self.session.execute(select(BeitragsKategorie))
        return list(result.scalars().all())

    async def get_category_rate(self, kategorie: BeitragKategorie) -> Decimal:
        """Get annual rate for a category.

        Looks up the BeitragsKategorie table first; falls back to defaults.
        """
        result = await self.session.execute(
            select(BeitragsKategorie).where(BeitragsKategorie.name == kategorie.value)
        )
        row = result.scalar_one_or_none()
        if row is not None:
            return row.jahresbeitrag
        return _DEFAULT_RATES.get(kategorie, Decimal("0.00"))

    def calculate_prorata(
        self,
        jahresbeitrag: Decimal,
        eintrittsdatum: date,
        billing_year: int,
    ) -> Decimal:
        """Pro-rata calculation.

        If the member joined before the billing year, full amount is due.
        If they joined during the billing year, remaining months from the
        join month are charged: jahresbeitrag * remaining_months / 12.
        """
        if eintrittsdatum.year < billing_year:
            return jahresbeitrag

        if eintrittsdatum.year > billing_year:
            return Decimal("0.00")

        # Joined during the billing year
        remaining_months = 12 - eintrittsdatum.month + 1
        return (jahresbeitrag * Decimal(remaining_months) / Decimal(12)).quantize(
            Decimal("0.01")
        )

    async def calculate_member_fee(
        self, member_id: int, billing_year: int
    ) -> dict:
        """Calculate fee for a single member for a given year."""
        result = await self.session.execute(
            select(Mitglied).where(Mitglied.id == member_id)
        )
        member = result.scalar_one()

        jahresbeitrag = await self.get_category_rate(member.beitragskategorie)
        prorata = self.calculate_prorata(jahresbeitrag, member.eintrittsdatum, billing_year)

        return {
            "member_id": member.id,
            "name": f"{member.vorname} {member.nachname}",
            "kategorie": member.beitragskategorie,
            "jahresbeitrag": jahresbeitrag,
            "prorata_betrag": prorata,
            "billing_year": billing_year,
        }

    async def calculate_all_fees(self, billing_year: int) -> list[dict]:
        """Calculate fees for all active members."""
        result = await self.session.execute(
            select(Mitglied).where(Mitglied.status == MitgliedStatus.aktiv)
        )
        members = result.scalars().all()

        fees = []
        for member in members:
            jahresbeitrag = await self.get_category_rate(member.beitragskategorie)
            prorata = self.calculate_prorata(
                jahresbeitrag, member.eintrittsdatum, billing_year
            )
            fees.append(
                {
                    "member_id": member.id,
                    "name": f"{member.vorname} {member.nachname}",
                    "kategorie": member.beitragskategorie,
                    "jahresbeitrag": jahresbeitrag,
                    "prorata_betrag": prorata,
                    "billing_year": billing_year,
                }
            )
        return fees

    # -- Fee run & dunning ---------------------------------------------------

    async def _next_rechnungsnummer(self) -> str:
        result = await self.session.execute(
            select(Rechnung.rechnungsnummer)
            .order_by(Rechnung.rechnungsnummer.desc())
            .limit(1)
        )
        last = result.scalar_one_or_none()
        if last is not None:
            num = int(last.split("-")[1])
            return f"R-{num + 1:04d}"
        return "R-0001"

    async def generate_fee_run(self, billing_year: int) -> list[Rechnung]:
        """Calculate fees for all active members and create invoices."""
        result = await self.session.execute(
            select(Mitglied).where(Mitglied.status == MitgliedStatus.aktiv)
        )
        members = list(result.scalars().all())

        invoices: list[Rechnung] = []
        for member in members:
            jahresbeitrag = await self.get_category_rate(member.beitragskategorie)
            prorata = self.calculate_prorata(
                jahresbeitrag, member.eintrittsdatum, billing_year
            )
            if prorata <= Decimal("0.00"):
                continue

            nummer = await self._next_rechnungsnummer()
            rechnung = Rechnung(
                rechnungsnummer=nummer,
                mitglied_id=member.id,
                betrag=prorata,
                beschreibung=f"Mitgliedsbeitrag {billing_year}",
                rechnungsdatum=date(billing_year, 1, 1),
                faelligkeitsdatum=date(billing_year, 1, 31),
                status=RechnungStatus.offen,
            )
            self.session.add(rechnung)
            await self.session.flush()
            await self.session.refresh(rechnung)
            invoices.append(rechnung)

        return invoices

    async def get_dunning_candidates(self) -> list[dict]:
        """Members with overdue invoices, grouped by dunning level.

        Level 1: 14+ days overdue
        Level 2: 28+ days overdue
        Level 3: 42+ days overdue
        """
        today = date.today()
        result = await self.session.execute(
            select(Rechnung).where(
                Rechnung.status == RechnungStatus.offen,
                Rechnung.faelligkeitsdatum < today,
            )
        )
        overdue = list(result.scalars().all())

        candidates: list[dict] = []
        for rechnung in overdue:
            days_overdue = (today - rechnung.faelligkeitsdatum).days
            if days_overdue >= 42:
                level = 3
            elif days_overdue >= 28:
                level = 2
            elif days_overdue >= 14:
                level = 1
            else:
                continue

            candidates.append({
                "rechnung_id": rechnung.id,
                "mitglied_id": rechnung.mitglied_id,
                "rechnungsnummer": rechnung.rechnungsnummer,
                "betrag": rechnung.betrag,
                "faelligkeitsdatum": rechnung.faelligkeitsdatum,
                "days_overdue": days_overdue,
                "mahnstufe": level,
            })

        return candidates
