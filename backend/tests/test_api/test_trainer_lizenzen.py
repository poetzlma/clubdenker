"""Tests for trainer license API endpoints."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from sportverein.models.mitglied import Mitglied

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_mitglied(session: AsyncSession, nr: int = 1) -> Mitglied:
    m = Mitglied(
        mitgliedsnummer=f"M-{nr:04d}",
        vorname=f"Trainer{nr}",
        nachname=f"Test{nr}",
        email=f"trainer{nr}@example.de",
        geburtsdatum=date(1985, 6, 15),
    )
    session.add(m)
    await session.flush()
    await session.refresh(m)
    return m


LIZENZ_DATA = {
    "lizenztyp": "trainerlizenz_c",
    "bezeichnung": "DOSB Trainerlizenz C Breitensport",
    "ausstellungsdatum": "2024-01-15",
    "ablaufdatum": "2028-01-15",
    "lizenznummer": "TC-2024-001",
    "ausstellende_stelle": "DOSB",
}


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


async def test_create_lizenz(client, session):
    m = await _create_mitglied(session)
    resp = await client.post(
        "/api/training/lizenzen",
        json={**LIZENZ_DATA, "mitglied_id": m.id},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["mitglied_id"] == m.id
    assert data["lizenztyp"] == "trainerlizenz_c"
    assert data["bezeichnung"] == "DOSB Trainerlizenz C Breitensport"
    assert data["lizenznummer"] == "TC-2024-001"
    assert data["ausstellende_stelle"] == "DOSB"


async def test_list_lizenzen(client, session):
    m = await _create_mitglied(session)
    await client.post(
        "/api/training/lizenzen",
        json={**LIZENZ_DATA, "mitglied_id": m.id},
    )
    await client.post(
        "/api/training/lizenzen",
        json={
            **LIZENZ_DATA,
            "mitglied_id": m.id,
            "lizenztyp": "erste_hilfe",
            "bezeichnung": "Erste Hilfe",
        },
    )

    resp = await client.get("/api/training/lizenzen")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2


async def test_list_lizenzen_filter_mitglied(client, session):
    m1 = await _create_mitglied(session, 1)
    m2 = await _create_mitglied(session, 2)
    await client.post(
        "/api/training/lizenzen",
        json={**LIZENZ_DATA, "mitglied_id": m1.id},
    )
    await client.post(
        "/api/training/lizenzen",
        json={**LIZENZ_DATA, "mitglied_id": m2.id, "bezeichnung": "Andere"},
    )

    resp = await client.get("/api/training/lizenzen", params={"mitglied_id": m1.id})
    data = resp.json()
    assert len(data) == 1
    assert data[0]["mitglied_id"] == m1.id


async def test_list_lizenzen_filter_expired(client, session):
    m = await _create_mitglied(session)
    # Expired
    await client.post(
        "/api/training/lizenzen",
        json={
            "mitglied_id": m.id,
            "lizenztyp": "erste_hilfe",
            "bezeichnung": "Abgelaufen",
            "ausstellungsdatum": "2020-01-01",
            "ablaufdatum": "2022-01-01",
        },
    )
    # Valid
    await client.post(
        "/api/training/lizenzen",
        json={
            "mitglied_id": m.id,
            "lizenztyp": "trainerlizenz_b",
            "bezeichnung": "Gueltig",
            "ausstellungsdatum": "2024-01-01",
            "ablaufdatum": (date.today() + timedelta(days=365)).isoformat(),
        },
    )

    resp_expired = await client.get("/api/training/lizenzen", params={"expired": True})
    assert len(resp_expired.json()) == 1
    assert resp_expired.json()[0]["bezeichnung"] == "Abgelaufen"

    resp_valid = await client.get("/api/training/lizenzen", params={"expired": False})
    assert len(resp_valid.json()) == 1
    assert resp_valid.json()[0]["bezeichnung"] == "Gueltig"


async def test_get_expiring_lizenzen(client, session):
    m = await _create_mitglied(session)
    # Expiring in 30 days
    await client.post(
        "/api/training/lizenzen",
        json={
            "mitglied_id": m.id,
            "lizenztyp": "trainerlizenz_c",
            "bezeichnung": "Bald ablaufend",
            "ausstellungsdatum": "2022-01-01",
            "ablaufdatum": (date.today() + timedelta(days=30)).isoformat(),
        },
    )
    # Far future
    await client.post(
        "/api/training/lizenzen",
        json={
            "mitglied_id": m.id,
            "lizenztyp": "trainerlizenz_b",
            "bezeichnung": "Noch lange",
            "ausstellungsdatum": "2024-01-01",
            "ablaufdatum": (date.today() + timedelta(days=365)).isoformat(),
        },
    )

    resp = await client.get("/api/training/lizenzen/expiring", params={"days": 90})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["bezeichnung"] == "Bald ablaufend"


async def test_delete_lizenz(client, session):
    m = await _create_mitglied(session)
    create_resp = await client.post(
        "/api/training/lizenzen",
        json={**LIZENZ_DATA, "mitglied_id": m.id},
    )
    lizenz_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/training/lizenzen/{lizenz_id}")
    assert resp.status_code == 204

    # Verify it's gone
    list_resp = await client.get("/api/training/lizenzen")
    assert len(list_resp.json()) == 0


async def test_delete_lizenz_not_found(client):
    resp = await client.delete("/api/training/lizenzen/999")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Auth required
# ---------------------------------------------------------------------------


async def test_lizenzen_requires_auth(unauthed_client):
    resp = await unauthed_client.get("/api/training/lizenzen")
    assert resp.status_code in (401, 422)


async def test_lizenzen_expiring_requires_auth(unauthed_client):
    resp = await unauthed_client.get("/api/training/lizenzen/expiring")
    assert resp.status_code in (401, 422)
