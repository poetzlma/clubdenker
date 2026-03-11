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
