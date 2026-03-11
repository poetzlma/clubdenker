"""Tests for the engagement analytics endpoint and service method."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from sportverein.models.mitglied import (
    Abteilung,
    Mitglied,
    MitgliedStatus,
)
from sportverein.models.training import Anwesenheit, Trainingsgruppe, Wochentag
from sportverein.services.dashboard import DashboardService


pytestmark = pytest.mark.asyncio


async def _seed_engagement_data(session: AsyncSession) -> dict:
    """Create data suitable for engagement analytics testing."""
    today = date.today()

    dept = Abteilung(name="Handball")
    session.add(dept)
    await session.flush()

    # Active member with recent attendance
    m1 = Mitglied(
        mitgliedsnummer="M-0001",
        vorname="Anna",
        nachname="Aktiv",
        email="anna@example.com",
        geburtsdatum=date(1990, 1, 1),
        eintrittsdatum=today - timedelta(days=365),
        status=MitgliedStatus.aktiv,
    )
    # Active member with old attendance only (at-risk)
    m2 = Mitglied(
        mitgliedsnummer="M-0002",
        vorname="Bob",
        nachname="Risiko",
        email="bob@example.com",
        geburtsdatum=date(1985, 6, 15),
        eintrittsdatum=today - timedelta(days=730),
        status=MitgliedStatus.aktiv,
    )
    # Cancelled member (left 3 months ago)
    m3 = Mitglied(
        mitgliedsnummer="M-0003",
        vorname="Clara",
        nachname="Weg",
        email="clara@example.com",
        geburtsdatum=date(1992, 3, 10),
        eintrittsdatum=today - timedelta(days=500),
        austrittsdatum=today - timedelta(days=90),
        status=MitgliedStatus.gekuendigt,
    )
    # Active member with no attendance at all
    m4 = Mitglied(
        mitgliedsnummer="M-0004",
        vorname="Diana",
        nachname="Neu",
        email="diana@example.com",
        geburtsdatum=date(2000, 12, 1),
        eintrittsdatum=today - timedelta(days=30),
        status=MitgliedStatus.aktiv,
    )
    session.add_all([m1, m2, m3, m4])
    await session.flush()

    # Training group
    tg = Trainingsgruppe(
        name="Training A",
        abteilung_id=dept.id,
        wochentag=Wochentag.montag,
        uhrzeit="18:00",
    )
    session.add(tg)
    await session.flush()

    # Recent attendance for m1 (within last 60 days)
    a1 = Anwesenheit(
        trainingsgruppe_id=tg.id,
        mitglied_id=m1.id,
        datum=today - timedelta(days=10),
        anwesend=True,
    )
    a2 = Anwesenheit(
        trainingsgruppe_id=tg.id,
        mitglied_id=m1.id,
        datum=today - timedelta(days=20),
        anwesend=True,
    )
    # Old attendance for m2 (more than 60 days ago)
    a3 = Anwesenheit(
        trainingsgruppe_id=tg.id,
        mitglied_id=m2.id,
        datum=today - timedelta(days=100),
        anwesend=True,
    )
    a4 = Anwesenheit(
        trainingsgruppe_id=tg.id,
        mitglied_id=m2.id,
        datum=today - timedelta(days=120),
        anwesend=False,
    )
    session.add_all([a1, a2, a3, a4])
    await session.flush()

    return {"m1": m1, "m2": m2, "m3": m3, "m4": m4, "dept": dept, "tg": tg}


# ---------------------------------------------------------------------------
# Service-level tests
# ---------------------------------------------------------------------------


async def test_engagement_analytics_service(session):
    data = await _seed_engagement_data(session)
    svc = DashboardService(session)
    result = await svc.get_engagement_analytics()

    # 3 active members, 1 left -> churn = 1/(3+1)*100 = 25%
    assert result["churn_rate"] == 25.0
    assert result["retention_rate"] == 75.0

    # m2 is at-risk (attended before but not in last 60 days)
    at_risk_ids = [m["member_id"] for m in result["at_risk_members"]]
    assert data["m2"].id in at_risk_ids
    # m1 attended recently -> not at risk
    assert data["m1"].id not in at_risk_ids
    # m4 never attended -> not at risk (never had attendance)
    assert data["m4"].id not in at_risk_ids

    # engagement_score: from recent 3 months, m1 has 2 present records,
    # m2 has 0 in range (100 days ago is outside 90 day window for one, inside for none)
    # Actually a3 is 100 days ago which is outside 90 days, a4 is 120 days ago also outside
    # So only a1 and a2 count (both present) -> 2/2 = 100%
    assert result["engagement_score"] == 100.0

    # monthly_churn has 12 entries
    assert len(result["monthly_churn"]) == 12
    for point in result["monthly_churn"]:
        assert "month" in point
        assert "joined" in point
        assert "left" in point

    # average_membership_duration_months > 0
    assert result["average_membership_duration_months"] > 0


async def test_engagement_analytics_empty_db(session):
    svc = DashboardService(session)
    result = await svc.get_engagement_analytics()

    assert result["churn_rate"] == 0.0
    assert result["retention_rate"] == 100.0
    assert result["at_risk_members"] == []
    assert result["engagement_score"] == 0.0
    assert len(result["monthly_churn"]) == 12
    assert result["average_membership_duration_months"] == 0.0


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


async def test_engagement_endpoint(client, session):
    await _seed_engagement_data(session)
    resp = await client.get("/api/dashboard/engagement")
    assert resp.status_code == 200
    data = resp.json()
    assert "churn_rate" in data
    assert "retention_rate" in data
    assert "at_risk_members" in data
    assert "engagement_score" in data
    assert "monthly_churn" in data
    assert "average_membership_duration_months" in data
    assert isinstance(data["at_risk_members"], list)
    assert isinstance(data["monthly_churn"], list)
    assert len(data["monthly_churn"]) == 12


async def test_engagement_endpoint_empty_db(client):
    resp = await client.get("/api/dashboard/engagement")
    assert resp.status_code == 200
    data = resp.json()
    assert data["churn_rate"] == 0.0
    assert data["retention_rate"] == 100.0
    assert data["engagement_score"] == 0.0
    assert data["at_risk_members"] == []
