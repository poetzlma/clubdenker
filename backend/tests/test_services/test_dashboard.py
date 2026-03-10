"""Tests for the DashboardService."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

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
    Mitglied,
    MitgliedAbteilung,
    MitgliedStatus,
)
from sportverein.services.dashboard import DashboardService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _seed_data(session: AsyncSession) -> dict:
    """Create a basic dataset with members, departments, invoices, bookings."""
    # Departments
    fussball = Abteilung(name="Fussball")
    tennis = Abteilung(name="Tennis")
    session.add_all([fussball, tennis])
    await session.flush()

    # Members
    m1 = Mitglied(
        mitgliedsnummer="M-0001",
        vorname="Max",
        nachname="Mustermann",
        email="max@example.com",
        geburtsdatum=date(1990, 1, 1),
        eintrittsdatum=date(2024, 1, 1),
        status=MitgliedStatus.aktiv,
    )
    m2 = Mitglied(
        mitgliedsnummer="M-0002",
        vorname="Anna",
        nachname="Schmidt",
        email="anna@example.com",
        geburtsdatum=date(1985, 6, 15),
        eintrittsdatum=date(2024, 3, 1),
        status=MitgliedStatus.aktiv,
    )
    session.add_all([m1, m2])
    await session.flush()

    # Department assignments
    ma1 = MitgliedAbteilung(mitglied_id=m1.id, abteilung_id=fussball.id)
    ma2 = MitgliedAbteilung(mitglied_id=m2.id, abteilung_id=tennis.id)
    session.add_all([ma1, ma2])
    await session.flush()

    # SEPA mandate for m1
    mandat = SepaMandat(
        mitglied_id=m1.id,
        mandatsreferenz="SEPA-001",
        iban="DE89370400440532013000",
        bic="COBADEFFXXX",
        kontoinhaber="Max Mustermann",
        unterschriftsdatum=date(2024, 1, 1),
        gueltig_ab=date(2024, 1, 1),
        aktiv=True,
    )
    session.add(mandat)
    await session.flush()

    # Bookings
    b1 = Buchung(
        buchungsdatum=date(2025, 1, 15),
        betrag=Decimal("500.00"),
        beschreibung="Beitrag",
        konto="4000",
        gegenkonto="1200",
        sphare=Sphare.ideell,
    )
    b2 = Buchung(
        buchungsdatum=date(2025, 2, 10),
        betrag=Decimal("-100.00"),
        beschreibung="Miete",
        konto="6000",
        gegenkonto="1200",
        sphare=Sphare.zweckbetrieb,
    )
    session.add_all([b1, b2])
    await session.flush()

    # Open invoice (overdue)
    r1 = Rechnung(
        rechnungsnummer="R-0001",
        mitglied_id=m2.id,
        betrag=Decimal("240.00"),
        beschreibung="Jahresbeitrag 2025",
        rechnungsdatum=date(2025, 1, 1),
        faelligkeitsdatum=date(2025, 1, 31),
        status=RechnungStatus.offen,
    )
    session.add(r1)
    await session.flush()

    # Kostenstelle for Fussball
    ks = Kostenstelle(
        name="Fussball Betrieb",
        abteilung_id=fussball.id,
        budget=Decimal("5000.00"),
    )
    session.add(ks)
    await session.flush()

    return {
        "fussball": fussball,
        "tennis": tennis,
        "m1": m1,
        "m2": m2,
        "rechnung": r1,
        "kostenstelle": ks,
    }


# ---------------------------------------------------------------------------
# Tests: Vorstand Dashboard
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.asyncio


async def test_vorstand_dashboard_structure(session: AsyncSession):
    await _seed_data(session)
    svc = DashboardService(session)
    result = await svc.get_vorstand_dashboard()

    assert "kpis" in result
    assert "member_trend" in result
    assert "cashflow" in result
    assert "open_actions" in result

    kpis = result["kpis"]
    assert kpis["active_members"] == 2
    assert kpis["total_balance"] == 400.0  # 500 - 100
    assert kpis["open_fees_count"] == 1
    assert kpis["open_fees_amount"] == 240.0
    assert kpis["compliance_score"] == 50.0  # 1 mandate / 2 active


async def test_vorstand_member_trend(session: AsyncSession):
    await _seed_data(session)
    svc = DashboardService(session)
    result = await svc.get_vorstand_dashboard()

    trend = result["member_trend"]
    assert len(trend) == 12
    for point in trend:
        assert "month" in point
        assert "total" in point
        assert "by_department" in point


async def test_vorstand_cashflow(session: AsyncSession):
    await _seed_data(session)
    svc = DashboardService(session)
    result = await svc.get_vorstand_dashboard()

    cashflow = result["cashflow"]
    assert len(cashflow) == 6
    for point in cashflow:
        assert "month" in point
        assert "income" in point
        assert "expenses" in point


async def test_vorstand_open_actions(session: AsyncSession):
    await _seed_data(session)
    svc = DashboardService(session)
    result = await svc.get_vorstand_dashboard()

    # Should have at least overdue fees action
    actions = result["open_actions"]
    assert len(actions) >= 1
    types = [a["type"] for a in actions]
    assert "overdue_fees" in types


async def test_vorstand_dashboard_empty_db(session: AsyncSession):
    svc = DashboardService(session)
    result = await svc.get_vorstand_dashboard()

    assert result["kpis"]["active_members"] == 0
    assert result["kpis"]["total_balance"] == 0.0
    assert len(result["member_trend"]) == 12
    assert len(result["cashflow"]) == 6


# ---------------------------------------------------------------------------
# Tests: Schatzmeister Dashboard
# ---------------------------------------------------------------------------


async def test_schatzmeister_dashboard_structure(session: AsyncSession):
    await _seed_data(session)
    svc = DashboardService(session)
    result = await svc.get_schatzmeister_dashboard()

    assert "sepa_hero" in result
    assert "kpis" in result
    assert "open_items" in result
    assert "budget_burn" in result
    assert "liquidity" in result

    sepa = result["sepa_hero"]
    assert sepa["total_count"] == 1
    assert sepa["total_amount"] == 240.0

    kpis = result["kpis"]
    assert kpis["balance_ideell"] == 500.0
    assert kpis["balance_zweckbetrieb"] == -100.0
    assert kpis["open_receivables"] == 240.0


async def test_schatzmeister_open_items(session: AsyncSession):
    await _seed_data(session)
    svc = DashboardService(session)
    result = await svc.get_schatzmeister_dashboard()

    items = result["open_items"]
    assert len(items) >= 1
    item = items[0]
    assert "member_name" in item
    assert "department" in item
    assert "amount" in item
    assert "days_overdue" in item
    assert "dunning_level" in item


async def test_schatzmeister_budget_burn(session: AsyncSession):
    await _seed_data(session)
    svc = DashboardService(session)
    result = await svc.get_schatzmeister_dashboard()

    burn = result["budget_burn"]
    assert len(burn) >= 1
    for b in burn:
        assert "name" in b
        assert "budget" in b
        assert "spent" in b
        assert "percentage" in b
        assert "department_color" in b


# ---------------------------------------------------------------------------
# Tests: Spartenleiter Dashboard
# ---------------------------------------------------------------------------


async def test_spartenleiter_dashboard_structure(session: AsyncSession):
    await _seed_data(session)
    svc = DashboardService(session)
    result = await svc.get_spartenleiter_dashboard("Fussball")

    assert "kpis" in result
    assert "attendance_heatmap" in result
    assert "training_schedule" in result
    assert "risk_members" in result
    assert "budget_donut" in result

    kpis = result["kpis"]
    assert kpis["member_count"] == 1
    assert 0.0 <= kpis["avg_attendance_pct"] <= 100.0


async def test_spartenleiter_heatmap(session: AsyncSession):
    await _seed_data(session)
    svc = DashboardService(session)
    result = await svc.get_spartenleiter_dashboard("Fussball")

    heatmap = result["attendance_heatmap"]
    assert len(heatmap) == 7  # 7 days
    for row in heatmap:
        assert "day" in row
        assert "cells" in row
        assert len(row["cells"]) == 12  # 12 weeks
        for cell in row["cells"]:
            assert 0 <= cell <= 3


async def test_spartenleiter_training_schedule(session: AsyncSession):
    await _seed_data(session)
    svc = DashboardService(session)
    result = await svc.get_spartenleiter_dashboard("Tennis")

    schedule = result["training_schedule"]
    assert len(schedule) >= 3
    for item in schedule:
        assert "group" in item
        assert "trainer" in item
        assert "registered" in item
        assert "max_participants" in item


async def test_spartenleiter_budget_donut(session: AsyncSession):
    await _seed_data(session)
    svc = DashboardService(session)
    result = await svc.get_spartenleiter_dashboard("Fussball")

    donut = result["budget_donut"]
    assert "used" in donut
    assert "committed" in donut
    assert "free" in donut
    total = donut["used"] + donut["committed"] + donut["free"]
    assert total >= 0


async def test_spartenleiter_invalid_department(session: AsyncSession):
    svc = DashboardService(session)
    with pytest.raises(ValueError, match="nicht gefunden"):
        await svc.get_spartenleiter_dashboard("Nonexistent")
