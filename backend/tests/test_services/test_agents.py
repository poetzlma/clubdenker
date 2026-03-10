"""Tests for agent workflow services."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sportverein.models.beitrag import SepaMandat
from sportverein.models.finanzen import Rechnung, RechnungStatus
from sportverein.models.mitglied import BeitragKategorie, Mitglied, MitgliedStatus
from sportverein.models.ehrenamt import Aufwandsentschaedigung, AufwandTyp
from sportverein.services.agents import (
    AufwandMonitorAgent,
    BeitragseinzugAgent,
    MahnwesenAgent,
)


def _make_member(
    *,
    vorname: str = "Max",
    nachname: str = "Mustermann",
    email: str = "max@example.com",
    mitgliedsnummer: str = "M-0001",
    geburtsdatum: date = date(1990, 1, 1),
    eintrittsdatum: date = date(2020, 1, 1),
) -> Mitglied:
    return Mitglied(
        vorname=vorname,
        nachname=nachname,
        email=email,
        mitgliedsnummer=mitgliedsnummer,
        geburtsdatum=geburtsdatum,
        eintrittsdatum=eintrittsdatum,
        status=MitgliedStatus.aktiv,
        beitragskategorie=BeitragKategorie.erwachsene,
    )


class TestBeitragseinzugAgent:
    async def test_run_basic(self, session):
        """Test basic fee collection run."""
        member = _make_member()
        session.add(member)
        await session.flush()

        agent = BeitragseinzugAgent(session)
        result = await agent.run(2025, 3)

        assert result["year"] == 2025
        assert result["month"] == 3
        assert result["fees_calculated"] >= 1
        assert result["invoices_created"] >= 1
        # No SEPA mandate, so all should be missing_mandate
        assert result["sepa_ready"] == 0
        assert len(result["missing_mandate"]) >= 1
        assert result["sepa_xml"] is None

    async def test_run_with_sepa_mandate(self, session):
        """Test fee collection with SEPA mandate generates XML."""
        member = _make_member()
        session.add(member)
        await session.flush()

        mandat = SepaMandat(
            mitglied_id=member.id,
            mandatsreferenz="MREF-001",
            iban="DE89370400440532013000",
            bic="COBADEFFXXX",
            kontoinhaber="Max Mustermann",
            unterschriftsdatum=date(2023, 1, 1),
            gueltig_ab=date(2023, 1, 1),
            aktiv=True,
        )
        session.add(mandat)
        await session.flush()

        agent = BeitragseinzugAgent(session)
        result = await agent.run(2025, 3)

        assert result["sepa_ready"] >= 1
        assert len(result["missing_mandate"]) == 0
        assert result["sepa_xml"] is not None
        assert "<?xml" in result["sepa_xml"]


class TestMahnwesenAgent:
    async def test_run_no_overdue(self, session):
        """Test dunning with no overdue invoices."""
        agent = MahnwesenAgent(session)
        result = await agent.run()
        assert result["total_overdue"] == 0
        assert result["report"] == []

    async def test_run_with_overdue(self, session):
        """Test dunning categorizes invoices by level."""
        member = _make_member()
        session.add(member)
        await session.flush()

        # 35 days overdue -> level 1 (30d)
        r1 = Rechnung(
            rechnungsnummer="R-0001",
            mitglied_id=member.id,
            betrag=Decimal("100.00"),
            beschreibung="Test 1",
            rechnungsdatum=date(2024, 1, 1),
            faelligkeitsdatum=date(2024, 1, 1),  # Very old -> level 3
            status=RechnungStatus.offen,
        )
        session.add(r1)
        await session.flush()

        agent = MahnwesenAgent(session)
        result = await agent.run()

        assert result["total_overdue"] >= 1
        assert len(result["report"]) >= 1
        # Old invoice should be level 3
        level3 = [r for r in result["report"] if r["mahnstufe"] == 3]
        assert len(level3) >= 1


class TestAufwandMonitorAgent:
    async def test_run_no_warnings(self, session):
        """Test monitor with no compensation entries."""
        agent = AufwandMonitorAgent(session)
        result = await agent.run()
        assert result["count"] == 0
        assert result["warnings"] == []

    async def test_run_with_warning(self, session):
        """Test monitor detects members approaching limits."""
        member = _make_member()
        session.add(member)
        await session.flush()

        # Add compensation near limit (>80% of 840 = 672)
        entry = Aufwandsentschaedigung(
            mitglied_id=member.id,
            betrag=Decimal("700.00"),
            datum=date.today(),
            typ=AufwandTyp.ehrenamt,
            beschreibung="Test compensation",
        )
        session.add(entry)
        await session.flush()

        agent = AufwandMonitorAgent(session)
        result = await agent.run()

        assert result["count"] >= 1
        assert len(result["warnings"]) >= 1
        w = result["warnings"][0]
        assert w["member_id"] == member.id
        assert w["typ"] == "ehrenamt"
        assert "projected_year_end" in w
