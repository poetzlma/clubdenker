"""Tests for untested MCP tool scenarios.

Covers:
- compliance_monitor (tools_audit.py) -- all 4 compliance checks
- vereins_setup_abteilungen edge cases: update_missing_id, unknown_action
- vereins_setup_beitragskategorien edge cases: delete_missing_id, unknown_action, update_nonexistent
- dashboard tools with richer data (bookings, invoices, cost centers)
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from sportverein.models.base import Base

# Register all models
import sportverein.models  # noqa: F401

from sportverein.mcp.session import set_session_factory
from sportverein.mcp.tools_audit import audit_logs_abrufen, compliance_monitor
from sportverein.mcp.tools_dashboard import (
    dashboard_schatzmeister,
    dashboard_spartenleiter,
    dashboard_vorstand,
)
from sportverein.mcp.tools_setup import (
    vereins_setup_abteilungen,
    vereins_setup_beitragskategorien,
)
from sportverein.models.beitrag import SepaMandat
from sportverein.models.finanzen import (
    Buchung,
    Kostenstelle,
    Rechnung,
    RechnungStatus,
    Sphare,
)
from sportverein.models.mitglied import (
    Abteilung,
    BeitragKategorie,
    Mitglied,
    MitgliedAbteilung,
    MitgliedStatus,
)
from sportverein.models.vereinsstammdaten import Vereinsstammdaten


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture()
async def mcp_engine():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture()
async def mcp_session_factory(mcp_engine):
    factory = async_sessionmaker(mcp_engine, class_=AsyncSession, expire_on_commit=False)
    set_session_factory(factory)
    yield factory
    set_session_factory(None)


@pytest_asyncio.fixture()
async def mcp_session(mcp_session_factory):
    async with mcp_session_factory() as session:
        yield session


@pytest_asyncio.fixture()
async def sample_member(mcp_session: AsyncSession):
    member = Mitglied(
        mitgliedsnummer="M-0001",
        vorname="Max",
        nachname="Mustermann",
        email="max@example.de",
        geburtsdatum=date(1990, 5, 15),
        eintrittsdatum=date(2024, 1, 1),
        status=MitgliedStatus.aktiv,
        beitragskategorie=BeitragKategorie.erwachsene,
    )
    mcp_session.add(member)
    await mcp_session.commit()
    await mcp_session.refresh(member)
    return member


@pytest_asyncio.fixture()
async def sample_dept(mcp_session: AsyncSession):
    dept = Abteilung(name="Fussball", beschreibung="Fussballabteilung")
    mcp_session.add(dept)
    await mcp_session.commit()
    await mcp_session.refresh(dept)
    return dept


# ===================================================================
# compliance_monitor -- no tests existed
# ===================================================================


class TestComplianceMonitor:
    """Tests for the compliance_monitor MCP tool."""

    @pytest.mark.asyncio
    async def test_empty_db_returns_gemeinnuetzigkeit_warning(self, mcp_session_factory):
        """With no Vereinsstammdaten, should warn about missing Freistellungsbescheid."""
        result = await compliance_monitor()
        assert "findings" in result
        assert result["total"] >= 1
        categories = [f["category"] for f in result["findings"]]
        assert "gemeinnuetzigkeit" in categories
        # The finding about missing Freistellungsbescheid
        gn = [f for f in result["findings"] if f["category"] == "gemeinnuetzigkeit"]
        assert gn[0]["severity"] == "warning"
        assert "Freistellungsbescheid" in gn[0]["message"]

    @pytest.mark.asyncio
    async def test_expired_freistellungsbescheid(self, mcp_session_factory, mcp_session):
        """Expired Freistellungsbescheid should be critical."""
        stamm = Vereinsstammdaten(
            name="TSV Musterstadt",
            strasse="Hauptstr. 1",
            plz="12345",
            ort="Musterstadt",
            iban="DE89370400440532013000",
            # Issued 4 years ago -> expired (>3 years)
            freistellungsbescheid_datum=date.today() - timedelta(days=4 * 365),
        )
        mcp_session.add(stamm)
        await mcp_session.commit()

        result = await compliance_monitor()
        gn = [f for f in result["findings"] if f["category"] == "gemeinnuetzigkeit"]
        assert len(gn) == 1
        assert gn[0]["severity"] == "critical"
        assert "abgelaufen" in gn[0]["message"]

    @pytest.mark.asyncio
    async def test_soon_expiring_freistellungsbescheid(self, mcp_session_factory, mcp_session):
        """Freistellungsbescheid expiring within 90 days should be warning."""
        # Set date so that 3 years from issue is ~60 days from now
        days_until_3y_from_now = 60
        issue_date = date.today() - timedelta(days=3 * 365 - days_until_3y_from_now)
        stamm = Vereinsstammdaten(
            name="TSV Musterstadt",
            strasse="Hauptstr. 1",
            plz="12345",
            ort="Musterstadt",
            iban="DE89370400440532013000",
            freistellungsbescheid_datum=issue_date,
        )
        mcp_session.add(stamm)
        await mcp_session.commit()

        result = await compliance_monitor()
        gn = [f for f in result["findings"] if f["category"] == "gemeinnuetzigkeit"]
        assert len(gn) == 1
        assert gn[0]["severity"] == "warning"
        assert "laeuft" in gn[0]["message"]

    @pytest.mark.asyncio
    async def test_valid_freistellungsbescheid_no_finding(self, mcp_session_factory, mcp_session):
        """Fresh Freistellungsbescheid (issued recently) should yield no finding."""
        stamm = Vereinsstammdaten(
            name="TSV Musterstadt",
            strasse="Hauptstr. 1",
            plz="12345",
            ort="Musterstadt",
            iban="DE89370400440532013000",
            freistellungsbescheid_datum=date.today() - timedelta(days=100),
        )
        mcp_session.add(stamm)
        await mcp_session.commit()

        result = await compliance_monitor()
        gn = [f for f in result["findings"] if f["category"] == "gemeinnuetzigkeit"]
        assert len(gn) == 0

    @pytest.mark.asyncio
    async def test_zweckbetrieb_over_limit(self, mcp_session_factory, mcp_session):
        """Zweckbetrieb income >45000 should be critical."""
        # Insert Vereinsstammdaten to suppress that warning
        stamm = Vereinsstammdaten(
            name="TSV Test",
            strasse="Str. 1",
            plz="12345",
            ort="Stadt",
            iban="DE89370400440532013000",
            freistellungsbescheid_datum=date.today() - timedelta(days=100),
        )
        mcp_session.add(stamm)

        buchung = Buchung(
            buchungsdatum=date.today(),
            betrag=Decimal("46000.00"),
            beschreibung="Kursgebuehren",
            konto="8400",
            gegenkonto="1200",
            sphare=Sphare.zweckbetrieb,
        )
        mcp_session.add(buchung)
        await mcp_session.commit()

        result = await compliance_monitor()
        zw = [f for f in result["findings"] if f["category"] == "zweckbetrieb"]
        assert len(zw) == 1
        assert zw[0]["severity"] == "critical"
        assert "45.000" in zw[0]["message"]

    @pytest.mark.asyncio
    async def test_zweckbetrieb_approaching_limit(self, mcp_session_factory, mcp_session):
        """Zweckbetrieb income >40000 but <45000 should be warning."""
        stamm = Vereinsstammdaten(
            name="TSV Test",
            strasse="Str. 1",
            plz="12345",
            ort="Stadt",
            iban="DE89370400440532013000",
            freistellungsbescheid_datum=date.today() - timedelta(days=100),
        )
        mcp_session.add(stamm)

        buchung = Buchung(
            buchungsdatum=date.today(),
            betrag=Decimal("42000.00"),
            beschreibung="Kursgebuehren",
            konto="8400",
            gegenkonto="1200",
            sphare=Sphare.zweckbetrieb,
        )
        mcp_session.add(buchung)
        await mcp_session.commit()

        result = await compliance_monitor()
        zw = [f for f in result["findings"] if f["category"] == "zweckbetrieb"]
        assert len(zw) == 1
        assert zw[0]["severity"] == "warning"

    @pytest.mark.asyncio
    async def test_zweckbetrieb_under_threshold_no_finding(self, mcp_session_factory, mcp_session):
        """Zweckbetrieb income <40000 should yield no finding."""
        stamm = Vereinsstammdaten(
            name="TSV Test",
            strasse="Str. 1",
            plz="12345",
            ort="Stadt",
            iban="DE89370400440532013000",
            freistellungsbescheid_datum=date.today() - timedelta(days=100),
        )
        mcp_session.add(stamm)

        buchung = Buchung(
            buchungsdatum=date.today(),
            betrag=Decimal("30000.00"),
            beschreibung="Kursgebuehren",
            konto="8400",
            gegenkonto="1200",
            sphare=Sphare.zweckbetrieb,
        )
        mcp_session.add(buchung)
        await mcp_session.commit()

        result = await compliance_monitor()
        zw = [f for f in result["findings"] if f["category"] == "zweckbetrieb"]
        assert len(zw) == 0

    @pytest.mark.asyncio
    async def test_dsgvo_pending_deletions(self, mcp_session_factory, mcp_session):
        """Members past loesch_datum should trigger DSGVO finding."""
        stamm = Vereinsstammdaten(
            name="TSV Test",
            strasse="Str. 1",
            plz="12345",
            ort="Stadt",
            iban="DE89370400440532013000",
            freistellungsbescheid_datum=date.today() - timedelta(days=100),
        )
        mcp_session.add(stamm)

        member = Mitglied(
            mitgliedsnummer="M-0099",
            vorname="Loesch",
            nachname="Mich",
            email="loeschm@example.de",
            geburtsdatum=date(1985, 1, 1),
            eintrittsdatum=date(2020, 1, 1),
            status=MitgliedStatus.gekuendigt,
            beitragskategorie=BeitragKategorie.erwachsene,
            loesch_datum=date.today() - timedelta(days=10),
        )
        mcp_session.add(member)
        await mcp_session.commit()

        result = await compliance_monitor()
        dsgvo = [f for f in result["findings"] if f["category"] == "dsgvo"]
        assert len(dsgvo) == 1
        assert dsgvo[0]["affected_count"] == 1
        assert "anonymisiert" in dsgvo[0]["message"]

    @pytest.mark.asyncio
    async def test_dsgvo_no_pending(self, mcp_session_factory, mcp_session):
        """No members past loesch_datum -> no DSGVO finding."""
        stamm = Vereinsstammdaten(
            name="TSV Test",
            strasse="Str. 1",
            plz="12345",
            ort="Stadt",
            iban="DE89370400440532013000",
            freistellungsbescheid_datum=date.today() - timedelta(days=100),
        )
        mcp_session.add(stamm)
        await mcp_session.commit()

        result = await compliance_monitor()
        dsgvo = [f for f in result["findings"] if f["category"] == "dsgvo"]
        assert len(dsgvo) == 0

    @pytest.mark.asyncio
    async def test_missing_sepa_mandates(self, mcp_session_factory, mcp_session):
        """Active member with open invoice but no SEPA mandate -> finding."""
        stamm = Vereinsstammdaten(
            name="TSV Test",
            strasse="Str. 1",
            plz="12345",
            ort="Stadt",
            iban="DE89370400440532013000",
            freistellungsbescheid_datum=date.today() - timedelta(days=100),
        )
        mcp_session.add(stamm)

        member = Mitglied(
            mitgliedsnummer="M-0002",
            vorname="Erika",
            nachname="Muster",
            email="erika@example.de",
            geburtsdatum=date(1988, 3, 20),
            eintrittsdatum=date(2023, 6, 1),
            status=MitgliedStatus.aktiv,
            beitragskategorie=BeitragKategorie.erwachsene,
        )
        mcp_session.add(member)
        await mcp_session.flush()
        await mcp_session.refresh(member)

        rechnung = Rechnung(
            rechnungsnummer="RE-2026-0001",
            mitglied_id=member.id,
            betrag=Decimal("120.00"),
            summe_netto=Decimal("120.00"),
            beschreibung="Mitgliedsbeitrag",
            rechnungsdatum=date.today(),
            faelligkeitsdatum=date.today() + timedelta(days=14),
            status=RechnungStatus.gestellt,
        )
        mcp_session.add(rechnung)
        await mcp_session.commit()

        result = await compliance_monitor()
        sepa = [f for f in result["findings"] if f["category"] == "sepa_mandate"]
        assert len(sepa) == 1
        assert sepa[0]["affected_count"] == 1

    @pytest.mark.asyncio
    async def test_no_missing_sepa_when_mandate_exists(self, mcp_session_factory, mcp_session):
        """Active member with open invoice AND active SEPA mandate -> no finding."""
        stamm = Vereinsstammdaten(
            name="TSV Test",
            strasse="Str. 1",
            plz="12345",
            ort="Stadt",
            iban="DE89370400440532013000",
            freistellungsbescheid_datum=date.today() - timedelta(days=100),
        )
        mcp_session.add(stamm)

        member = Mitglied(
            mitgliedsnummer="M-0003",
            vorname="Hans",
            nachname="Meier",
            email="hans@example.de",
            geburtsdatum=date(1975, 7, 10),
            eintrittsdatum=date(2022, 1, 1),
            status=MitgliedStatus.aktiv,
            beitragskategorie=BeitragKategorie.erwachsene,
        )
        mcp_session.add(member)
        await mcp_session.flush()
        await mcp_session.refresh(member)

        mandat = SepaMandat(
            mitglied_id=member.id,
            mandatsreferenz="MAND-TEST-001",
            iban="DE89370400440532013000",
            kontoinhaber="Hans Meier",
            unterschriftsdatum=date(2022, 1, 1),
            gueltig_ab=date(2022, 1, 1),
            aktiv=True,
        )
        mcp_session.add(mandat)

        rechnung = Rechnung(
            rechnungsnummer="RE-2026-0002",
            mitglied_id=member.id,
            betrag=Decimal("120.00"),
            summe_netto=Decimal("120.00"),
            beschreibung="Mitgliedsbeitrag",
            rechnungsdatum=date.today(),
            faelligkeitsdatum=date.today() + timedelta(days=14),
            status=RechnungStatus.gestellt,
        )
        mcp_session.add(rechnung)
        await mcp_session.commit()

        result = await compliance_monitor()
        sepa = [f for f in result["findings"] if f["category"] == "sepa_mandate"]
        assert len(sepa) == 0

    @pytest.mark.asyncio
    async def test_result_counts(self, mcp_session_factory, mcp_session):
        """Verify critical_count, warning_count, info_count aggregation."""
        # Empty DB -> at least 1 warning (gemeinnuetzigkeit)
        result = await compliance_monitor()
        assert result["total"] == result["critical_count"] + result["warning_count"] + result["info_count"]
        assert result["warning_count"] >= 1


# ===================================================================
# vereins_setup_abteilungen -- missing edge cases
# ===================================================================


class TestSetupAbteilungenEdgeCases:
    @pytest.mark.asyncio
    async def test_update_missing_id(self, mcp_session_factory):
        result = await vereins_setup_abteilungen(action="update", name="Foo")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_update_nonexistent(self, mcp_session_factory):
        result = await vereins_setup_abteilungen(
            action="update", department_id=9999, name="Ghost"
        )
        assert "error" in result

    @pytest.mark.asyncio
    async def test_unknown_action(self, mcp_session_factory):
        result = await vereins_setup_abteilungen(action="nope")
        assert "error" in result
        assert "nope" in result["error"]

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, mcp_session_factory):
        result = await vereins_setup_abteilungen(action="delete", department_id=9999)
        assert "error" in result


# ===================================================================
# vereins_setup_beitragskategorien -- missing edge cases
# ===================================================================


class TestSetupBeitragskategorienEdgeCases:
    @pytest.mark.asyncio
    async def test_delete_missing_id(self, mcp_session_factory):
        result = await vereins_setup_beitragskategorien(action="delete")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, mcp_session_factory):
        result = await vereins_setup_beitragskategorien(action="delete", category_id=9999)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_unknown_action(self, mcp_session_factory):
        result = await vereins_setup_beitragskategorien(action="nope")
        assert "error" in result
        assert "nope" in result["error"]

    @pytest.mark.asyncio
    async def test_update_missing_id(self, mcp_session_factory):
        result = await vereins_setup_beitragskategorien(action="update", jahresbeitrag=99.0)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_update_nonexistent(self, mcp_session_factory):
        result = await vereins_setup_beitragskategorien(
            action="update", category_id=9999, jahresbeitrag=200.0
        )
        assert "error" in result


# ===================================================================
# Dashboard tools with richer data
# ===================================================================


@pytest_asyncio.fixture()
async def rich_data(mcp_session: AsyncSession):
    """Create data with department, member, cost center, bookings, and invoices."""
    dept = Abteilung(name="Tennis", beschreibung="Tennisabteilung")
    mcp_session.add(dept)
    await mcp_session.flush()
    await mcp_session.refresh(dept)

    member = Mitglied(
        mitgliedsnummer="M-0010",
        vorname="Anna",
        nachname="Schmidt",
        email="anna@example.de",
        geburtsdatum=date(1992, 8, 25),
        eintrittsdatum=date(2023, 1, 1),
        status=MitgliedStatus.aktiv,
        beitragskategorie=BeitragKategorie.erwachsene,
    )
    mcp_session.add(member)
    await mcp_session.flush()
    await mcp_session.refresh(member)

    assoc = MitgliedAbteilung(mitglied_id=member.id, abteilung_id=dept.id)
    mcp_session.add(assoc)

    ks = Kostenstelle(
        name="Tennis Budget",
        beschreibung="Budget der Tennisabteilung",
        abteilung_id=dept.id,
        budget=Decimal("5000.00"),
    )
    mcp_session.add(ks)
    await mcp_session.flush()
    await mcp_session.refresh(ks)

    # Add some bookings
    buchung1 = Buchung(
        buchungsdatum=date.today() - timedelta(days=15),
        betrag=Decimal("500.00"),
        beschreibung="Einnahme Kursgebuehren",
        konto="8400",
        gegenkonto="1200",
        sphare=Sphare.ideell,
    )
    buchung2 = Buchung(
        buchungsdatum=date.today() - timedelta(days=10),
        betrag=Decimal("-200.00"),
        beschreibung="Ausgabe Hallenmiete",
        konto="6300",
        gegenkonto="1200",
        sphare=Sphare.ideell,
        kostenstelle_id=ks.id,
    )
    mcp_session.add_all([buchung1, buchung2])

    # Add an overdue invoice
    rechnung = Rechnung(
        rechnungsnummer="RE-2026-0010",
        mitglied_id=member.id,
        betrag=Decimal("120.00"),
        summe_netto=Decimal("120.00"),
        beschreibung="Mitgliedsbeitrag 2026",
        rechnungsdatum=date.today() - timedelta(days=60),
        faelligkeitsdatum=date.today() - timedelta(days=30),
        status=RechnungStatus.gestellt,
    )
    mcp_session.add(rechnung)
    await mcp_session.commit()

    return {"department": dept, "member": member, "kostenstelle": ks, "rechnung": rechnung}


class TestDashboardVorstandRich:
    @pytest.mark.asyncio
    async def test_vorstand_with_bookings_and_invoices(self, mcp_session_factory, rich_data):
        result = await dashboard_vorstand()
        data = result["data"]
        assert data["kpis"]["active_members"] >= 1
        assert data["kpis"]["total_balance"] != 0.0
        assert data["kpis"]["open_fees_count"] >= 1
        assert data["kpis"]["open_fees_amount"] >= 120.0
        assert len(data["open_actions"]) >= 1

    @pytest.mark.asyncio
    async def test_vorstand_summary_is_string(self, mcp_session_factory, rich_data):
        result = await dashboard_vorstand()
        assert isinstance(result["summary"], str)
        assert "Vorstand Dashboard" in result["summary"]


class TestDashboardSchatzmeisterRich:
    @pytest.mark.asyncio
    async def test_schatzmeister_with_data(self, mcp_session_factory, rich_data):
        result = await dashboard_schatzmeister()
        data = result["data"]
        assert data["kpis"]["balance_ideell"] != 0.0
        assert data["kpis"]["open_receivables"] >= 120.0
        assert data["kpis"]["pending_transfers"] >= 1  # no SEPA mandate

    @pytest.mark.asyncio
    async def test_schatzmeister_budget_burn(self, mcp_session_factory, rich_data):
        result = await dashboard_schatzmeister()
        data = result["data"]
        assert len(data["budget_burn"]) >= 1
        bb = data["budget_burn"][0]
        assert "name" in bb
        assert "budget" in bb
        assert "spent" in bb
        assert "percentage" in bb

    @pytest.mark.asyncio
    async def test_schatzmeister_open_items(self, mcp_session_factory, rich_data):
        result = await dashboard_schatzmeister()
        data = result["data"]
        # The overdue invoice should appear in open_items
        assert len(data["open_items"]) >= 1
        item = data["open_items"][0]
        assert "member_name" in item
        assert "days_overdue" in item
        assert "dunning_level" in item


class TestDashboardSpartenleiterRich:
    @pytest.mark.asyncio
    async def test_spartenleiter_with_budget_and_member(self, mcp_session_factory, rich_data):
        result = await dashboard_spartenleiter(abteilung="Tennis")
        data = result["data"]
        assert data["kpis"]["member_count"] >= 1
        assert data["kpis"]["budget_utilization_pct"] > 0.0
        donut = data["budget_donut"]
        assert donut["used"] > 0.0

    @pytest.mark.asyncio
    async def test_spartenleiter_risk_members(self, mcp_session_factory, rich_data):
        result = await dashboard_spartenleiter(abteilung="Tennis")
        data = result["data"]
        # The member with overdue invoice should be a risk member
        assert data["kpis"]["risk_count"] >= 1
        assert len(data["risk_members"]) >= 1
        rm = data["risk_members"][0]
        assert "name" in rm
        assert "reason" in rm

    @pytest.mark.asyncio
    async def test_spartenleiter_summary_contains_name(self, mcp_session_factory, rich_data):
        result = await dashboard_spartenleiter(abteilung="Tennis")
        assert "Tennis" in result["summary"]


# ===================================================================
# audit_logs_abrufen -- additional edge cases
# ===================================================================


class TestAuditLogsEdgeCases:
    @pytest.mark.asyncio
    async def test_limit_zero(self, mcp_session_factory):
        """Limit of 0 should still work (returns empty or all)."""
        result = await audit_logs_abrufen(limit=0)
        assert "items" in result
        assert "total" in result

    @pytest.mark.asyncio
    async def test_nonexistent_filter(self, mcp_session_factory):
        """Filter for non-existent action should return empty."""
        result = await audit_logs_abrufen(aktion="nonexistent_action")
        assert result["items"] == []
        assert result["total"] == 0
