"""Tests for training and attendance API endpoints."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from sportverein.models.mitglied import Abteilung, Mitglied

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_abteilung(session: AsyncSession, name: str = "Fussball") -> Abteilung:
    abt = Abteilung(name=name)
    session.add(abt)
    await session.flush()
    await session.refresh(abt)
    return abt


async def _create_mitglied(session: AsyncSession, nr: int = 1) -> Mitglied:
    m = Mitglied(
        mitgliedsnummer=f"M-{nr:04d}",
        vorname=f"Test{nr}",
        nachname=f"Member{nr}",
        email=f"test{nr}@example.de",
        geburtsdatum=date(1990, 1, 1),
    )
    session.add(m)
    await session.flush()
    await session.refresh(m)
    return m


GRUPPE_DATA = {
    "name": "Herren 1",
    "wochentag": "dienstag",
    "uhrzeit": "18:30",
    "trainer": "Max Trainer",
    "dauer_minuten": 90,
    "max_teilnehmer": 22,
    "ort": "Sportplatz A",
}


# ---------------------------------------------------------------------------
# Trainingsgruppen
# ---------------------------------------------------------------------------


async def test_create_trainingsgruppe(client, session):
    abt = await _create_abteilung(session)
    resp = await client.post(
        "/api/training/gruppen",
        json={**GRUPPE_DATA, "abteilung_id": abt.id},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Herren 1"
    assert data["wochentag"] == "dienstag"
    assert data["abteilung_id"] == abt.id
    assert data["aktiv"] is True


async def test_list_trainingsgruppen(client, session):
    abt = await _create_abteilung(session)
    await client.post(
        "/api/training/gruppen",
        json={**GRUPPE_DATA, "abteilung_id": abt.id},
    )
    await client.post(
        "/api/training/gruppen",
        json={**GRUPPE_DATA, "name": "Herren 2", "abteilung_id": abt.id},
    )

    resp = await client.get("/api/training/gruppen")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2


async def test_list_trainingsgruppen_filter_abteilung(client, session):
    abt1 = await _create_abteilung(session, "Fussball")
    abt2 = await _create_abteilung(session, "Tennis")
    await client.post(
        "/api/training/gruppen",
        json={**GRUPPE_DATA, "abteilung_id": abt1.id},
    )
    await client.post(
        "/api/training/gruppen",
        json={**GRUPPE_DATA, "name": "Damen Einzel", "abteilung_id": abt2.id},
    )

    resp = await client.get("/api/training/gruppen", params={"abteilung_id": abt1.id})
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "Herren 1"


async def test_update_trainingsgruppe(client, session):
    abt = await _create_abteilung(session)
    create_resp = await client.post(
        "/api/training/gruppen",
        json={**GRUPPE_DATA, "abteilung_id": abt.id},
    )
    gruppe_id = create_resp.json()["id"]

    resp = await client.put(
        f"/api/training/gruppen/{gruppe_id}",
        json={"name": "Updated Name", "uhrzeit": "19:00"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Updated Name"
    assert data["uhrzeit"] == "19:00"


async def test_update_trainingsgruppe_not_found(client):
    resp = await client.put(
        "/api/training/gruppen/999",
        json={"name": "X"},
    )
    assert resp.status_code == 404


async def test_delete_trainingsgruppe(client, session):
    abt = await _create_abteilung(session)
    create_resp = await client.post(
        "/api/training/gruppen",
        json={**GRUPPE_DATA, "abteilung_id": abt.id},
    )
    gruppe_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/training/gruppen/{gruppe_id}")
    assert resp.status_code == 204

    # Verify it's gone (pass aktiv as query to disable default filter)
    list_resp = await client.get("/api/training/gruppen")
    assert len(list_resp.json()) == 0


async def test_delete_trainingsgruppe_with_attendance(client, session):
    abt = await _create_abteilung(session)
    m = await _create_mitglied(session)
    create_resp = await client.post(
        "/api/training/gruppen",
        json={**GRUPPE_DATA, "abteilung_id": abt.id},
    )
    gruppe_id = create_resp.json()["id"]

    # Record attendance
    await client.post(
        "/api/training/anwesenheit",
        json={
            "trainingsgruppe_id": gruppe_id,
            "datum": (date.today() - timedelta(days=1)).isoformat(),
            "teilnehmer": [{"mitglied_id": m.id, "anwesend": True}],
        },
    )

    # Should fail
    resp = await client.delete(f"/api/training/gruppen/{gruppe_id}")
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Anwesenheit
# ---------------------------------------------------------------------------


async def test_record_anwesenheit(client, session):
    abt = await _create_abteilung(session)
    m1 = await _create_mitglied(session, 1)
    m2 = await _create_mitglied(session, 2)
    create_resp = await client.post(
        "/api/training/gruppen",
        json={**GRUPPE_DATA, "abteilung_id": abt.id},
    )
    gruppe_id = create_resp.json()["id"]

    resp = await client.post(
        "/api/training/anwesenheit",
        json={
            "trainingsgruppe_id": gruppe_id,
            "datum": (date.today() - timedelta(days=1)).isoformat(),
            "teilnehmer": [
                {"mitglied_id": m1.id, "anwesend": True},
                {"mitglied_id": m2.id, "anwesend": False, "notiz": "Krank"},
            ],
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert len(data) == 2


async def test_get_anwesenheit(client, session):
    abt = await _create_abteilung(session)
    m = await _create_mitglied(session)
    create_resp = await client.post(
        "/api/training/gruppen",
        json={**GRUPPE_DATA, "abteilung_id": abt.id},
    )
    gruppe_id = create_resp.json()["id"]

    await client.post(
        "/api/training/anwesenheit",
        json={
            "trainingsgruppe_id": gruppe_id,
            "datum": (date.today() - timedelta(days=1)).isoformat(),
            "teilnehmer": [{"mitglied_id": m.id, "anwesend": True}],
        },
    )

    resp = await client.get(
        "/api/training/anwesenheit",
        params={"gruppe_id": gruppe_id},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["anwesend"] is True


async def test_anwesenheit_statistik(client, session):
    abt = await _create_abteilung(session)
    m = await _create_mitglied(session)
    create_resp = await client.post(
        "/api/training/gruppen",
        json={**GRUPPE_DATA, "abteilung_id": abt.id},
    )
    gruppe_id = create_resp.json()["id"]

    # Add attendance records over past weeks
    for i in range(1, 4):
        await client.post(
            "/api/training/anwesenheit",
            json={
                "trainingsgruppe_id": gruppe_id,
                "datum": (date.today() - timedelta(weeks=i)).isoformat(),
                "teilnehmer": [{"mitglied_id": m.id, "anwesend": True}],
            },
        )

    resp = await client.get(f"/api/training/anwesenheit/statistik/{abt.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert "heatmap" in data
    assert len(data["heatmap"]) == 7
    assert data["total_sessions"] == 3


async def test_mitglied_anwesenheit(client, session):
    abt = await _create_abteilung(session)
    m = await _create_mitglied(session)
    create_resp = await client.post(
        "/api/training/gruppen",
        json={**GRUPPE_DATA, "abteilung_id": abt.id},
    )
    gruppe_id = create_resp.json()["id"]

    for i in range(1, 3):
        await client.post(
            "/api/training/anwesenheit",
            json={
                "trainingsgruppe_id": gruppe_id,
                "datum": (date.today() - timedelta(weeks=i)).isoformat(),
                "teilnehmer": [{"mitglied_id": m.id, "anwesend": True}],
            },
        )

    resp = await client.get(f"/api/training/anwesenheit/mitglied/{m.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["mitglied_id"] == m.id
    assert data["total_eintraege"] == 2
    assert data["anwesend"] == 2


# ---------------------------------------------------------------------------
# Auth required
# ---------------------------------------------------------------------------


async def test_gruppen_requires_auth(unauthed_client):
    resp = await unauthed_client.get("/api/training/gruppen")
    assert resp.status_code in (401, 422)


async def test_anwesenheit_requires_auth(unauthed_client):
    resp = await unauthed_client.get("/api/training/anwesenheit")
    assert resp.status_code in (401, 422)


async def test_statistik_requires_auth(unauthed_client):
    resp = await unauthed_client.get("/api/training/anwesenheit/statistik/1")
    assert resp.status_code in (401, 422)
