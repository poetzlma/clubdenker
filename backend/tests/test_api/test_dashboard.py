"""Tests for the dashboard router."""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.asyncio


async def test_stats(client):
    resp = await client.get("/api/dashboard/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_active" in data
    assert "total_passive" in data
    assert "new_this_month" in data
    assert "by_department" in data
    assert isinstance(data["by_department"], dict)


async def test_stats_with_members(client):
    # Create a member first so counts are non-zero check
    await client.post(
        "/api/mitglieder",
        json={
            "vorname": "Stats",
            "nachname": "Test",
            "email": "stats@example.de",
            "geburtsdatum": "1985-03-10",
        },
    )
    resp = await client.get("/api/dashboard/stats")
    data = resp.json()
    assert data["total_active"] >= 1


async def test_recent_activity(client):
    # Create a member to generate audit log entry
    await client.post(
        "/api/mitglieder",
        json={
            "vorname": "Activity",
            "nachname": "Test",
            "email": "activity@example.de",
            "geburtsdatum": "1985-03-10",
        },
    )
    resp = await client.get("/api/dashboard/recent-activity")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert isinstance(data["items"], list)
    assert len(data["items"]) >= 1


# ---------------------------------------------------------------------------
# Role-based dashboards
# ---------------------------------------------------------------------------


async def test_vorstand_dashboard(client):
    resp = await client.get("/api/dashboard/vorstand")
    assert resp.status_code == 200
    data = resp.json()
    assert "kpis" in data
    assert "member_trend" in data
    assert "cashflow" in data
    assert "open_actions" in data


async def test_vorstand_dashboard_with_data(client):
    await client.post(
        "/api/mitglieder",
        json={
            "vorname": "Vorstand",
            "nachname": "Test",
            "email": "vorstand@example.de",
            "geburtsdatum": "1990-05-01",
        },
    )
    resp = await client.get("/api/dashboard/vorstand")
    data = resp.json()
    assert isinstance(data["kpis"], dict)
    assert data["kpis"]["active_members"] >= 1


async def test_schatzmeister_dashboard(client):
    resp = await client.get("/api/dashboard/schatzmeister")
    assert resp.status_code == 200
    data = resp.json()
    assert "sepa_hero" in data
    assert "kpis" in data
    assert "open_items" in data
    assert "budget_burn" in data
    assert "liquidity" in data


async def test_spartenleiter_dashboard_not_found(client):
    resp = await client.get("/api/dashboard/spartenleiter/NichtExistent")
    assert resp.status_code == 404


async def test_spartenleiter_dashboard_with_department(client, session):
    from sportverein.models.mitglied import Abteilung

    dept = Abteilung(name="TestAbt", beschreibung="Test")
    session.add(dept)
    await session.flush()

    resp = await client.get("/api/dashboard/spartenleiter/TestAbt")
    assert resp.status_code == 200
    data = resp.json()
    assert "kpis" in data
    assert "attendance_heatmap" in data
    assert "training_schedule" in data
