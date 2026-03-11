from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sportverein.models.beitrag import BeitragsKategorie
from sportverein.models.finanzen import Rechnung, RechnungStatus
from sportverein.models.mitglied import (
    BeitragKategorie,
    Mitglied,
    MitgliedAbteilung,
    MitgliedStatus,
)


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

    async def create_category(
        self,
        name: str,
        jahresbeitrag: Decimal,
        beschreibung: str | None = None,
    ) -> BeitragsKategorie:
        """Create a new fee category."""
        category = BeitragsKategorie(
            name=name,
            jahresbeitrag=jahresbeitrag,
            beschreibung=beschreibung,
        )
        self.session.add(category)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ValueError(f"Beitragskategorie mit Name '{name}' existiert bereits.") from exc
        await self.session.refresh(category)
        return category

    async def update_category(
        self,
        category_id: int,
        jahresbeitrag: Decimal | None = None,
        beschreibung: str | None = ...,  # type: ignore[assignment]
    ) -> BeitragsKategorie:
        """Update an existing fee category."""
        result = await self.session.execute(
            select(BeitragsKategorie).where(BeitragsKategorie.id == category_id)
        )
        category = result.scalar_one_or_none()
        if category is None:
            raise ValueError(f"Beitragskategorie mit ID {category_id} nicht gefunden.")
        if jahresbeitrag is not None:
            category.jahresbeitrag = jahresbeitrag
        if beschreibung is not ...:
            category.beschreibung = beschreibung
        await self.session.flush()
        await self.session.refresh(category)
        return category

    async def delete_category(self, category_id: int) -> None:
        """Delete a fee category. Raises if members still use a matching name."""
        result = await self.session.execute(
            select(BeitragsKategorie).where(BeitragsKategorie.id == category_id)
        )
        category = result.scalar_one_or_none()
        if category is None:
            raise ValueError(f"Beitragskategorie mit ID {category_id} nicht gefunden.")

        # Check if any member uses a BeitragKategorie enum value matching this name
        count_result = await self.session.execute(
            select(func.count())
            .select_from(Mitglied)
            .where(Mitglied.beitragskategorie == category.name)
        )
        count = count_result.scalar_one()
        if count > 0:
            raise ValueError(
                f"Beitragskategorie '{category.name}' kann nicht gelöscht werden, "
                f"da sie noch von {count} Mitglied(ern) verwendet wird."
            )
        await self.session.delete(category)
        await self.session.flush()

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
        return (jahresbeitrag * Decimal(remaining_months) / Decimal(12)).quantize(Decimal("0.01"))

    async def calculate_member_fee(self, member_id: int, billing_year: int) -> dict:
        """Calculate fee for a single member for a given year."""
        result = await self.session.execute(select(Mitglied).where(Mitglied.id == member_id))
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
            prorata = self.calculate_prorata(jahresbeitrag, member.eintrittsdatum, billing_year)
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
            select(Rechnung.rechnungsnummer).order_by(Rechnung.rechnungsnummer.desc()).limit(1)
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
            prorata = self.calculate_prorata(jahresbeitrag, member.eintrittsdatum, billing_year)
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
                status=RechnungStatus.entwurf,
            )
            self.session.add(rechnung)
            await self.session.flush()
            await self.session.refresh(rechnung)
            invoices.append(rechnung)

        return invoices

    async def calculate_combined_fee(self, member_id: int, billing_year: int) -> dict:
        """Calculate combined fee with discounts.

        Formula: Grundbeitrag + Sum(Spartenbeitraege) * Rabattfaktor
        Discounts:
          - Jugend: 50% off base
          - Multi-department: 10% off each additional department beyond first
          - Familie: Members at same address get 20% off from 2nd member onwards
        """
        result = await self.session.execute(
            select(Mitglied)
            .where(Mitglied.id == member_id)
            .options(selectinload(Mitglied.abteilungen).selectinload(MitgliedAbteilung.abteilung))
        )
        member = result.scalar_one_or_none()
        if member is None:
            raise ValueError(f"Member {member_id} not found")

        base_fee = await self.get_category_rate(member.beitragskategorie)
        base_fee = self.calculate_prorata(base_fee, member.eintrittsdatum, billing_year)

        discounts: list[dict] = []
        department_fees: list[dict] = []

        # Jugend discount: 50% off base
        if member.beitragskategorie == BeitragKategorie.jugend:
            discount_amount = base_fee * Decimal("0.50")
            discounts.append(
                {
                    "type": "jugend",
                    "description": "Jugendrabatt 50%",
                    "amount": discount_amount,
                }
            )

        # Department fees and multi-department discount
        dept_count = len(member.abteilungen) if member.abteilungen else 0
        # Each department has a notional fee of 0 (included in base), but
        # multi-department discount applies to base
        for idx, ma in enumerate(member.abteilungen or []):
            dept_name = ma.abteilung.name if ma.abteilung else str(ma.abteilung_id)
            dept_fee = Decimal("0.00")  # included in base
            department_fees.append(
                {
                    "abteilung": dept_name,
                    "fee": dept_fee,
                }
            )

        if dept_count > 1:
            additional = dept_count - 1
            discount_amount = base_fee * Decimal("0.10") * Decimal(str(additional))
            discounts.append(
                {
                    "type": "multi_department",
                    "description": f"Mehrspartenrabatt ({additional} weitere Abteilungen, je 10%)",
                    "amount": discount_amount,
                }
            )

        # Familie discount: members at same address get 20% off from 2nd member
        if member.strasse and member.plz and member.ort:
            family_result = await self.session.execute(
                select(Mitglied.id)
                .where(
                    Mitglied.strasse == member.strasse,
                    Mitglied.plz == member.plz,
                    Mitglied.ort == member.ort,
                    Mitglied.status == MitgliedStatus.aktiv,
                )
                .order_by(Mitglied.eintrittsdatum.asc())
            )
            family_ids = [row[0] for row in family_result.all()]
            if len(family_ids) > 1 and member.id != family_ids[0]:
                discount_amount = base_fee * Decimal("0.20")
                discounts.append(
                    {
                        "type": "familie",
                        "description": "Familienrabatt 20% (ab 2. Mitglied gleiche Adresse)",
                        "amount": discount_amount,
                    }
                )

        total_discounts = sum(d["amount"] for d in discounts)
        total = max(base_fee - total_discounts, Decimal("0.00"))

        return {
            "member_id": member.id,
            "name": f"{member.vorname} {member.nachname}",
            "base_fee": base_fee,
            "department_fees": department_fees,
            "discounts": [{**d, "amount": float(d["amount"])} for d in discounts],
            "total": total,
        }

    async def get_dunning_candidates(self) -> list[dict]:
        """Members with overdue invoices, grouped by dunning level.

        Level 1: 14+ days overdue
        Level 2: 28+ days overdue
        Level 3: 42+ days overdue
        """
        today = date.today()
        result = await self.session.execute(
            select(Rechnung).where(
                Rechnung.status.in_(
                    [
                        RechnungStatus.entwurf,
                        RechnungStatus.gestellt,
                        RechnungStatus.faellig,
                        RechnungStatus.teilbezahlt,
                    ]
                ),
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

            candidates.append(
                {
                    "rechnung_id": rechnung.id,
                    "mitglied_id": rechnung.mitglied_id,
                    "rechnungsnummer": rechnung.rechnungsnummer,
                    "betrag": rechnung.betrag,
                    "faelligkeitsdatum": rechnung.faelligkeitsdatum,
                    "days_overdue": days_overdue,
                    "mahnstufe": level,
                }
            )

        return candidates
