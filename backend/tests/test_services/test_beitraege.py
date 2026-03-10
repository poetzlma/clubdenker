from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from sportverein.models.beitrag import BeitragsKategorie
from sportverein.models.finanzen import RechnungStatus
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


# ── Fee run tests ─────────────────────────────────────────────────────


@pytest.mark.usefixtures("_seed_categories")
class TestGenerateFeeRun:
    async def test_creates_invoices_for_active_members(self, session):
        active1 = _make_member(eintrittsdatum=date(2020, 1, 1))
        active2 = _make_member(
            vorname="Anna",
            email="anna@example.com",
            mitgliedsnummer="M002",
            kategorie=BeitragKategorie.jugend,
        )
        inactive = _make_member(
            vorname="Bob",
            email="bob@example.com",
            mitgliedsnummer="M003",
            status=MitgliedStatus.gekuendigt,
        )
        session.add_all([active1, active2, inactive])
        await session.flush()

        svc = BeitraegeService(session)
        invoices = await svc.generate_fee_run(2024)

        assert len(invoices) == 2
        amounts = {inv.mitglied_id: inv.betrag for inv in invoices}
        assert amounts[active1.id] == Decimal("240.00")
        assert amounts[active2.id] == Decimal("120.00")

        # All invoices should be open
        for inv in invoices:
            assert inv.status == RechnungStatus.offen
            assert inv.rechnungsnummer.startswith("R-")

    async def test_fee_run_skips_zero_amount(self, session):
        """Ehrenmitglied with 0 fee should not generate an invoice."""
        member = _make_member(
            kategorie=BeitragKategorie.ehrenmitglied,
        )
        session.add(member)
        await session.flush()

        svc = BeitraegeService(session)
        invoices = await svc.generate_fee_run(2024)

        assert len(invoices) == 0


# ── Dunning candidates tests ─────────────────────────────────────────


@pytest.mark.usefixtures("_seed_categories")
class TestGetDunningCandidates:
    async def test_dunning_levels(self, session):
        member = _make_member(eintrittsdatum=date(2020, 1, 1))
        session.add(member)
        await session.flush()

        svc = BeitraegeService(session)
        today = date.today()

        from sportverein.models.finanzen import Rechnung

        # Level 1: 14+ days overdue
        r1 = Rechnung(
            rechnungsnummer="R-1001",
            mitglied_id=member.id,
            betrag=Decimal("100.00"),
            beschreibung="Level 1",
            rechnungsdatum=today - timedelta(days=30),
            faelligkeitsdatum=today - timedelta(days=15),
            status=RechnungStatus.offen,
        )
        # Level 2: 28+ days overdue
        r2 = Rechnung(
            rechnungsnummer="R-1002",
            mitglied_id=member.id,
            betrag=Decimal("200.00"),
            beschreibung="Level 2",
            rechnungsdatum=today - timedelta(days=45),
            faelligkeitsdatum=today - timedelta(days=30),
            status=RechnungStatus.offen,
        )
        # Level 3: 42+ days overdue
        r3 = Rechnung(
            rechnungsnummer="R-1003",
            mitglied_id=member.id,
            betrag=Decimal("300.00"),
            beschreibung="Level 3",
            rechnungsdatum=today - timedelta(days=60),
            faelligkeitsdatum=today - timedelta(days=45),
            status=RechnungStatus.offen,
        )
        # Not overdue enough (only 5 days)
        r4 = Rechnung(
            rechnungsnummer="R-1004",
            mitglied_id=member.id,
            betrag=Decimal("50.00"),
            beschreibung="Not dunnable",
            rechnungsdatum=today - timedelta(days=10),
            faelligkeitsdatum=today - timedelta(days=5),
            status=RechnungStatus.offen,
        )
        # Paid invoice (should be excluded)
        r5 = Rechnung(
            rechnungsnummer="R-1005",
            mitglied_id=member.id,
            betrag=Decimal("50.00"),
            beschreibung="Already paid",
            rechnungsdatum=today - timedelta(days=60),
            faelligkeitsdatum=today - timedelta(days=45),
            status=RechnungStatus.bezahlt,
        )
        session.add_all([r1, r2, r3, r4, r5])
        await session.flush()

        candidates = await svc.get_dunning_candidates()

        assert len(candidates) == 3
        levels = {c["rechnungsnummer"]: c["mahnstufe"] for c in candidates}
        assert levels["R-1001"] == 1
        assert levels["R-1002"] == 2
        assert levels["R-1003"] == 3
