from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from sportverein.models.beitrag import BeitragsKategorie
from sportverein.models.mitglied import BeitragKategorie, Mitglied, MitgliedStatus
from sportverein.services.beitraege import BeitraegeService


# ── Pure calculate_prorata tests ───────────────────────────────────────


class TestCalculateProrata:
    """Tests for the synchronous pro-rata helper (no DB needed)."""

    def _svc(self):
        # session not used for calculate_prorata
        return BeitraegeService(session=None)  # type: ignore[arg-type]

    def test_full_year_before_billing(self):
        """Member joined before the billing year -> full amount."""
        result = self._svc().calculate_prorata(
            Decimal("240.00"), date(2023, 3, 15), 2024
        )
        assert result == Decimal("240.00")

    def test_january_join(self):
        """Joined in January of billing year -> 12 months remaining."""
        result = self._svc().calculate_prorata(
            Decimal("240.00"), date(2024, 1, 10), 2024
        )
        assert result == Decimal("240.00")

    def test_july_join(self):
        """Joined in July of billing year -> 6 months remaining."""
        result = self._svc().calculate_prorata(
            Decimal("240.00"), date(2024, 7, 1), 2024
        )
        assert result == Decimal("120.00")

    def test_december_join(self):
        """Joined in December of billing year -> 1 month remaining."""
        result = self._svc().calculate_prorata(
            Decimal("240.00"), date(2024, 12, 20), 2024
        )
        assert result == Decimal("20.00")

    def test_future_billing_year(self):
        """Join date is after billing year -> 0."""
        result = self._svc().calculate_prorata(
            Decimal("240.00"), date(2025, 5, 1), 2024
        )
        assert result == Decimal("0.00")


# ── DB-backed tests ───────────────────────────────────────────────────


def _make_member(
    *,
    vorname: str = "Max",
    nachname: str = "Mustermann",
    email: str = "max@example.com",
    mitgliedsnummer: str = "M001",
    geburtsdatum: date = date(1990, 1, 1),
    eintrittsdatum: date = date(2020, 1, 1),
    status: MitgliedStatus = MitgliedStatus.aktiv,
    kategorie: BeitragKategorie = BeitragKategorie.erwachsene,
) -> Mitglied:
    return Mitglied(
        vorname=vorname,
        nachname=nachname,
        email=email,
        mitgliedsnummer=mitgliedsnummer,
        geburtsdatum=geburtsdatum,
        eintrittsdatum=eintrittsdatum,
        status=status,
        beitragskategorie=kategorie,
    )


@pytest.fixture()
def _seed_categories(session):
    """Seed the BeitragsKategorie table with standard rates."""
    categories = [
        BeitragsKategorie(name="erwachsene", jahresbeitrag=Decimal("240.00")),
        BeitragsKategorie(name="jugend", jahresbeitrag=Decimal("120.00")),
        BeitragsKategorie(name="familie", jahresbeitrag=Decimal("360.00")),
        BeitragsKategorie(name="passiv", jahresbeitrag=Decimal("60.00")),
        BeitragsKategorie(name="ehrenmitglied", jahresbeitrag=Decimal("0.00")),
    ]
    session.add_all(categories)


@pytest.mark.usefixtures("_seed_categories")
class TestCalculateMemberFee:
    async def test_full_year_member(self, session):
        member = _make_member(eintrittsdatum=date(2020, 1, 1))
        session.add(member)
        await session.flush()

        svc = BeitraegeService(session)
        fee = await svc.calculate_member_fee(member.id, 2024)

        assert fee["member_id"] == member.id
        assert fee["name"] == "Max Mustermann"
        assert fee["kategorie"] == BeitragKategorie.erwachsene
        assert fee["jahresbeitrag"] == Decimal("240.00")
        assert fee["prorata_betrag"] == Decimal("240.00")
        assert fee["billing_year"] == 2024

    async def test_mid_year_join(self, session):
        member = _make_member(eintrittsdatum=date(2024, 7, 15))
        session.add(member)
        await session.flush()

        svc = BeitraegeService(session)
        fee = await svc.calculate_member_fee(member.id, 2024)

        assert fee["prorata_betrag"] == Decimal("120.00")

    async def test_ehrenmitglied_zero_fee(self, session):
        member = _make_member(
            email="ehren@example.com",
            mitgliedsnummer="M099",
            kategorie=BeitragKategorie.ehrenmitglied,
        )
        session.add(member)
        await session.flush()

        svc = BeitraegeService(session)
        fee = await svc.calculate_member_fee(member.id, 2024)

        assert fee["jahresbeitrag"] == Decimal("0.00")
        assert fee["prorata_betrag"] == Decimal("0.00")


@pytest.mark.usefixtures("_seed_categories")
class TestCalculateAllFees:
    async def test_only_active_members(self, session):
        active = _make_member(eintrittsdatum=date(2020, 1, 1))
        inactive = _make_member(
            vorname="Anna",
            email="anna@example.com",
            mitgliedsnummer="M002",
            status=MitgliedStatus.gekuendigt,
        )
        session.add_all([active, inactive])
        await session.flush()

        svc = BeitraegeService(session)
        fees = await svc.calculate_all_fees(2024)

        assert len(fees) == 1
        assert fees[0]["member_id"] == active.id

    async def test_multiple_active_members(self, session):
        m1 = _make_member()
        m2 = _make_member(
            vorname="Anna",
            email="anna@example.com",
            mitgliedsnummer="M002",
            kategorie=BeitragKategorie.jugend,
        )
        session.add_all([m1, m2])
        await session.flush()

        svc = BeitraegeService(session)
        fees = await svc.calculate_all_fees(2024)

        assert len(fees) == 2
        amounts = {f["name"]: f["jahresbeitrag"] for f in fees}
        assert amounts["Max Mustermann"] == Decimal("240.00")
        assert amounts["Anna Mustermann"] == Decimal("120.00")
