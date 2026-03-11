"""Tests for agent workflow services."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sportverein.models.beitrag import SepaMandat
from sportverein.models.finanzen import Buchung, Rechnung, RechnungStatus, Sphare
from sportverein.models.mitglied import BeitragKategorie, Mitglied, MitgliedStatus
from sportverein.models.ehrenamt import Aufwandsentschaedigung, AufwandTyp
from sportverein.models.vereinsstammdaten import Vereinsstammdaten
from sportverein.services.agents import (
    AufwandMonitorAgent,
    BeitragseinzugAgent,
    ComplianceMonitorAgent,
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


class TestComplianceMonitorAgent:
    async def test_run_no_issues(self, session):
        """Test compliance check with no data returns only Stammdaten warning."""
        agent = ComplianceMonitorAgent(session)
        result = await agent.run()
        # Should at least warn about missing Vereinsstammdaten
        assert result["total"] >= 1
        gemeinnuetzigkeit = [f for f in result["findings"] if f["category"] == "gemeinnuetzigkeit"]
        assert len(gemeinnuetzigkeit) == 1
        assert gemeinnuetzigkeit[0]["severity"] == "warning"

    async def test_expired_freistellungsbescheid(self, session):
        """Test critical finding for expired Freistellungsbescheid."""
        stammdaten = Vereinsstammdaten(
            name="TSV Test",
            strasse="Teststr. 1",
            plz="12345",
            ort="Teststadt",
            iban="DE89370400440532013000",
            # Set to ~4 years ago so the 3-year validity is expired
            freistellungsbescheid_datum=date.today() - timedelta(days=4 * 365),
        )
        session.add(stammdaten)
        await session.flush()

        agent = ComplianceMonitorAgent(session)
        result = await agent.run()

        gemeinnuetzigkeit = [f for f in result["findings"] if f["category"] == "gemeinnuetzigkeit"]
        assert len(gemeinnuetzigkeit) == 1
        assert gemeinnuetzigkeit[0]["severity"] == "critical"
        assert result["critical_count"] >= 1

    async def test_freistellungsbescheid_expiring_soon(self, session):
        """Test warning for Freistellungsbescheid expiring within 90 days."""
        # Set so that expiry (datum + 3 years) is 60 days from now
        target_expiry = date.today() + timedelta(days=60)
        bescheid_datum = target_expiry - timedelta(days=3 * 365)
        stammdaten = Vereinsstammdaten(
            name="TSV Test",
            strasse="Teststr. 1",
            plz="12345",
            ort="Teststadt",
            iban="DE89370400440532013000",
            freistellungsbescheid_datum=bescheid_datum,
        )
        session.add(stammdaten)
        await session.flush()

        agent = ComplianceMonitorAgent(session)
        result = await agent.run()

        gemeinnuetzigkeit = [f for f in result["findings"] if f["category"] == "gemeinnuetzigkeit"]
        assert len(gemeinnuetzigkeit) == 1
        assert gemeinnuetzigkeit[0]["severity"] == "warning"

    async def test_zweckbetrieb_over_40k_warning(self, session):
        """Test warning when Zweckbetrieb turnover exceeds 40,000 EUR."""
        buchung = Buchung(
            buchungsdatum=date.today(),
            betrag=Decimal("42000.00"),
            beschreibung="Kursgebuehren",
            konto="4400",
            gegenkonto="1200",
            sphare=Sphare.zweckbetrieb,
        )
        session.add(buchung)
        await session.flush()

        agent = ComplianceMonitorAgent(session)
        result = await agent.run()

        zweckbetrieb = [f for f in result["findings"] if f["category"] == "zweckbetrieb"]
        assert len(zweckbetrieb) == 1
        assert zweckbetrieb[0]["severity"] == "warning"

    async def test_zweckbetrieb_over_45k_critical(self, session):
        """Test critical when Zweckbetrieb turnover exceeds 45,000 EUR."""
        buchung = Buchung(
            buchungsdatum=date.today(),
            betrag=Decimal("46000.00"),
            beschreibung="Kursgebuehren",
            konto="4400",
            gegenkonto="1200",
            sphare=Sphare.zweckbetrieb,
        )
        session.add(buchung)
        await session.flush()

        agent = ComplianceMonitorAgent(session)
        result = await agent.run()

        zweckbetrieb = [f for f in result["findings"] if f["category"] == "zweckbetrieb"]
        assert len(zweckbetrieb) == 1
        assert zweckbetrieb[0]["severity"] == "critical"

    async def test_dsgvo_pending_deletions(self, session):
        """Test finding for members past their deletion date."""
        member = _make_member()
        member.loesch_datum = date.today() - timedelta(days=10)
        member.geloescht_am = None
        session.add(member)
        await session.flush()

        agent = ComplianceMonitorAgent(session)
        result = await agent.run()

        dsgvo = [f for f in result["findings"] if f["category"] == "dsgvo"]
        assert len(dsgvo) == 1
        assert dsgvo[0]["severity"] == "warning"
        assert dsgvo[0]["affected_count"] == 1

    async def test_missing_sepa_mandate(self, session):
        """Test finding for active members with open invoices but no mandate."""
        member = _make_member()
        session.add(member)
        await session.flush()

        rechnung = Rechnung(
            rechnungsnummer="R-COMP-001",
            mitglied_id=member.id,
            betrag=Decimal("120.00"),
            beschreibung="Beitrag",
            rechnungsdatum=date.today(),
            faelligkeitsdatum=date.today() + timedelta(days=14),
            status=RechnungStatus.gestellt,
        )
        session.add(rechnung)
        await session.flush()

        agent = ComplianceMonitorAgent(session)
        result = await agent.run()

        sepa = [f for f in result["findings"] if f["category"] == "sepa_mandate"]
        assert len(sepa) == 1
        assert sepa[0]["affected_count"] == 1
