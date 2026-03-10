"""Tests for the dashboard view API endpoints."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from sportverein.models.beitrag import SepaMandat
from sportverein.models.finanzen import (
    Buchung,
    Sphare,
)
from sportverein.models.mitglied import (
    Abteilung,
    Mitglied,
    MitgliedAbteilung,
    MitgliedStatus,
)


pytestmark = pytest.mark.asyncio


async def _seed(session: AsyncSession) -> None:
    """Create minimal data for dashboard tests."""
    dept = Abteilung(name="Fussball")
    session.add(dept)
    await session.flush()

    m = Mitglied(
        mitgliedsnummer="M-0001",
        vorname="Test",
        nachname="User",
        email="test@example.com",
        geburtsdatum=date(1990, 1, 1),
        eintrittsdatum=date(2024, 1, 1),
        status=MitgliedStatus.aktiv,
    )
    session.add(m)
    await session.flush()

    ma = MitgliedAbteilung(mitglied_id=m.id, abteilung_id=dept.id)
    session.add(ma)

    mandat = SepaMandat(
        mitglied_id=m.id,
        mandatsreferenz="SEPA-001",
        iban="DE89370400440532013000",
        kontoinhaber="Test User",
        unterschriftsdatum=date(2024, 1, 1),
        gueltig_ab=date(2024, 1, 1),
        aktiv=True,
    )
    session.add(mandat)

    b = Buchung(
        buchungsdatum=date(2025, 1, 15),
        betrag=Decimal("100.00"),
        beschreibung="Test",
        konto="4000",
        gegenkonto="1200",
        sphare=Sphare.ideell,
    )
    session.add(b)
    await session.flush()


async def test_vorstand_endpoint(client, session):
    await _seed(session)
    resp = await client.get("/api/dashboard/vorstand")
    assert resp.status_code == 200
    data = resp.json()
    assert "kpis" in data
    assert "member_trend" in data
    assert "cashflow" in data
    assert "open_actions" in data
    assert data["kpis"]["active_members"] >= 1


async def test_schatzmeister_endpoint(client, session):
    await _seed(session)
    resp = await client.get("/api/dashboard/schatzmeister")
    assert resp.status_code == 200
    data = resp.json()
    assert "sepa_hero" in data
    assert "kpis" in data
    assert "open_items" in data
    assert "budget_burn" in data
    assert "liquidity" in data


async def test_spartenleiter_endpoint(client, session):
    await _seed(session)
    resp = await client.get("/api/dashboard/spartenleiter/Fussball")
    assert resp.status_code == 200
    data = resp.json()
    assert "kpis" in data
    assert "attendance_heatmap" in data
    assert "training_schedule" in data
    assert "risk_members" in data
    assert "budget_donut" in data
    assert data["kpis"]["member_count"] >= 1


async def test_spartenleiter_invalid_department(client, session):
    resp = await client.get("/api/dashboard/spartenleiter/Nonexistent")
    assert resp.status_code == 404


async def test_vorstand_empty_db(client):
    resp = await client.get("/api/dashboard/vorstand")
    assert resp.status_code == 200
    data = resp.json()
    assert data["kpis"]["active_members"] == 0


async def test_schatzmeister_empty_db(client):
    resp = await client.get("/api/dashboard/schatzmeister")
    assert resp.status_code == 200
    data = resp.json()
    assert data["sepa_hero"]["total_count"] == 0
