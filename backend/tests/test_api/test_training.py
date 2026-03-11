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
# Trainingsgruppen -- additional edge cases
# ---------------------------------------------------------------------------


async def test_list_trainingsgruppen_filter_aktiv(client, session):
    """Default listing filters by aktiv=true; inactive groups are excluded."""
    abt = await _create_abteilung(session)
    create_resp = await client.post(
        "/api/training/gruppen",
        json={**GRUPPE_DATA, "abteilung_id": abt.id},
    )
    gruppe_id = create_resp.json()["id"]

    # Deactivate the group
    await client.put(f"/api/training/gruppen/{gruppe_id}", json={"aktiv": False})

    # Default listing (aktiv=true) should return 0
    resp = await client.get("/api/training/gruppen")
    assert resp.status_code == 200
    assert len(resp.json()) == 0

    # Listing with aktiv=false should return the inactive group
    resp = await client.get("/api/training/gruppen", params={"aktiv": "false"})
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["aktiv"] is False


async def test_update_trainingsgruppe_wochentag(client, session):
    """Update only the wochentag field."""
    abt = await _create_abteilung(session)
    create_resp = await client.post(
        "/api/training/gruppen",
        json={**GRUPPE_DATA, "abteilung_id": abt.id},
    )
    gruppe_id = create_resp.json()["id"]

    resp = await client.put(
        f"/api/training/gruppen/{gruppe_id}",
        json={"wochentag": "freitag"},
    )
    assert resp.status_code == 200
    assert resp.json()["wochentag"] == "freitag"


async def test_update_trainingsgruppe_deactivate(client, session):
    """Deactivate a training group via update."""
    abt = await _create_abteilung(session)
    create_resp = await client.post(
        "/api/training/gruppen",
        json={**GRUPPE_DATA, "abteilung_id": abt.id},
    )
    gruppe_id = create_resp.json()["id"]

    resp = await client.put(
        f"/api/training/gruppen/{gruppe_id}",
        json={"aktiv": False},
    )
    assert resp.status_code == 200
    assert resp.json()["aktiv"] is False


async def test_delete_trainingsgruppe_not_found(client):
    """Deleting a non-existent group returns 400 (service raises ValueError)."""
    resp = await client.delete("/api/training/gruppen/99999")
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Anwesenheit -- additional edge cases
# ---------------------------------------------------------------------------


async def test_anwesenheit_upsert(client, session):
    """Recording attendance for the same member+group+date updates the existing record."""
    abt = await _create_abteilung(session)
    m = await _create_mitglied(session)
    create_resp = await client.post(
        "/api/training/gruppen",
        json={**GRUPPE_DATA, "abteilung_id": abt.id},
    )
    gruppe_id = create_resp.json()["id"]
    datum = (date.today() - timedelta(days=2)).isoformat()

    # First record: present
    resp1 = await client.post(
        "/api/training/anwesenheit",
        json={
            "trainingsgruppe_id": gruppe_id,
            "datum": datum,
            "teilnehmer": [{"mitglied_id": m.id, "anwesend": True}],
        },
    )
    assert resp1.status_code == 201

    # Second record: same date, now absent with note
    resp2 = await client.post(
        "/api/training/anwesenheit",
        json={
            "trainingsgruppe_id": gruppe_id,
            "datum": datum,
            "teilnehmer": [{"mitglied_id": m.id, "anwesend": False, "notiz": "Verletzt"}],
        },
    )
    assert resp2.status_code == 201
    data = resp2.json()
    assert len(data) == 1
    assert data[0]["anwesend"] is False
    assert data[0]["notiz"] == "Verletzt"

    # Should still only be one record total
    get_resp = await client.get(
        "/api/training/anwesenheit",
        params={"gruppe_id": gruppe_id},
    )
    assert len(get_resp.json()) == 1


async def test_get_anwesenheit_filter_by_mitglied(client, session):
    """Filter attendance by mitglied_id."""
    abt = await _create_abteilung(session)
    m1 = await _create_mitglied(session, 1)
    m2 = await _create_mitglied(session, 2)
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
            "teilnehmer": [
                {"mitglied_id": m1.id, "anwesend": True},
                {"mitglied_id": m2.id, "anwesend": True},
            ],
        },
    )

    resp = await client.get(
        "/api/training/anwesenheit",
        params={"mitglied_id": m1.id},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["mitglied_id"] == m1.id


async def test_get_anwesenheit_filter_by_date_range(client, session):
    """Filter attendance by date range."""
    abt = await _create_abteilung(session)
    m = await _create_mitglied(session)
    create_resp = await client.post(
        "/api/training/gruppen",
        json={**GRUPPE_DATA, "abteilung_id": abt.id},
    )
    gruppe_id = create_resp.json()["id"]

    # Record attendance on 3 different dates
    for i in [3, 7, 14]:
        await client.post(
            "/api/training/anwesenheit",
            json={
                "trainingsgruppe_id": gruppe_id,
                "datum": (date.today() - timedelta(days=i)).isoformat(),
                "teilnehmer": [{"mitglied_id": m.id, "anwesend": True}],
            },
        )

    # Filter to only the last 10 days
    resp = await client.get(
        "/api/training/anwesenheit",
        params={
            "datum_von": (date.today() - timedelta(days=10)).isoformat(),
            "datum_bis": date.today().isoformat(),
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2  # days 3 and 7


async def test_get_anwesenheit_no_filters(client, session):
    """Get all attendance records without any filters."""
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

    resp = await client.get("/api/training/anwesenheit")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


async def test_anwesenheit_statistik_empty(client, session):
    """Statistik for a department with no attendance data returns zeros."""
    abt = await _create_abteilung(session)
    resp = await client.get(f"/api/training/anwesenheit/statistik/{abt.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_sessions"] == 0
    assert data["total_present"] == 0
    assert data["avg_attendance_pct"] == 0.0


async def test_anwesenheit_statistik_custom_wochen(client, session):
    """Statistik respects the wochen query parameter."""
    abt = await _create_abteilung(session)
    resp = await client.get(
        f"/api/training/anwesenheit/statistik/{abt.id}",
        params={"wochen": 4},
    )
    assert resp.status_code == 200
    data = resp.json()
    # heatmap should have 7 rows (one per day), each with 4 cells
    assert len(data["heatmap"]) == 7
    assert len(data["heatmap"][0]["cells"]) == 4


async def test_mitglied_anwesenheit_no_records(client, session):
    """Mitglied anwesenheit for a member with no records returns zeros."""
    m = await _create_mitglied(session)
    resp = await client.get(f"/api/training/anwesenheit/mitglied/{m.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["mitglied_id"] == m.id
    assert data["total_eintraege"] == 0
    assert data["anwesend"] == 0
    assert data["abwesend"] == 0
    assert data["anwesenheit_pct"] == 0.0


async def test_mitglied_anwesenheit_custom_wochen(client, session):
    """Mitglied anwesenheit respects the wochen query parameter."""
    m = await _create_mitglied(session)
    resp = await client.get(
        f"/api/training/anwesenheit/mitglied/{m.id}",
        params={"wochen": 4},
    )
    assert resp.status_code == 200
    assert resp.json()["wochen"] == 4


# ---------------------------------------------------------------------------
# Trainer-Lizenzen
# ---------------------------------------------------------------------------

LIZENZ_DATA = {
    "lizenztyp": "trainerlizenz_c",
    "bezeichnung": "C-Lizenz Breitensport",
    "ausstellungsdatum": "2024-01-15",
    "ablaufdatum": "2027-01-15",
    "lizenznummer": "LIZ-2024-001",
    "ausstellende_stelle": "DOSB",
}


async def test_create_lizenz(client, session):
    m = await _create_mitglied(session)
    resp = await client.post(
        "/api/training/lizenzen",
        json={**LIZENZ_DATA, "mitglied_id": m.id},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["lizenztyp"] == "trainerlizenz_c"
    assert data["bezeichnung"] == "C-Lizenz Breitensport"
    assert data["mitglied_id"] == m.id
    assert data["lizenznummer"] == "LIZ-2024-001"
    assert data["ausstellende_stelle"] == "DOSB"


async def test_create_lizenz_minimal(client, session):
    """Create a license with only required fields."""
    m = await _create_mitglied(session)
    resp = await client.post(
        "/api/training/lizenzen",
        json={
            "mitglied_id": m.id,
            "lizenztyp": "erste_hilfe",
            "bezeichnung": "Erste Hilfe Kurs",
            "ausstellungsdatum": "2024-06-01",
            "ablaufdatum": "2026-06-01",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["lizenztyp"] == "erste_hilfe"
    assert data["lizenznummer"] is None
    assert data["ausstellende_stelle"] is None


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
            "lizenznummer": "EH-001",
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
        json={**LIZENZ_DATA, "mitglied_id": m2.id, "lizenznummer": "LIZ-002"},
    )

    resp = await client.get("/api/training/lizenzen", params={"mitglied_id": m1.id})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["mitglied_id"] == m1.id


async def test_list_lizenzen_filter_expired(client, session):
    m = await _create_mitglied(session)
    # Create an expired license
    await client.post(
        "/api/training/lizenzen",
        json={
            **LIZENZ_DATA,
            "mitglied_id": m.id,
            "ablaufdatum": "2020-01-01",
            "lizenznummer": "EXPIRED-001",
        },
    )
    # Create a valid license
    await client.post(
        "/api/training/lizenzen",
        json={
            **LIZENZ_DATA,
            "mitglied_id": m.id,
            "ablaufdatum": "2030-12-31",
            "lizenznummer": "VALID-001",
        },
    )

    # Only expired
    resp = await client.get("/api/training/lizenzen", params={"expired": True})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["lizenznummer"] == "EXPIRED-001"

    # Only valid
    resp = await client.get("/api/training/lizenzen", params={"expired": False})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["lizenznummer"] == "VALID-001"


async def test_get_expiring_lizenzen(client, session):
    m = await _create_mitglied(session)
    # License expiring in 30 days
    expiring_date = (date.today() + timedelta(days=30)).isoformat()
    await client.post(
        "/api/training/lizenzen",
        json={
            **LIZENZ_DATA,
            "mitglied_id": m.id,
            "ablaufdatum": expiring_date,
            "lizenznummer": "EXPIRING-001",
        },
    )
    # License expiring in 200 days (outside default 90-day window)
    far_date = (date.today() + timedelta(days=200)).isoformat()
    await client.post(
        "/api/training/lizenzen",
        json={
            **LIZENZ_DATA,
            "mitglied_id": m.id,
            "ablaufdatum": far_date,
            "lizenznummer": "FAR-001",
        },
    )

    resp = await client.get("/api/training/lizenzen/expiring")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["lizenznummer"] == "EXPIRING-001"


async def test_get_expiring_lizenzen_custom_days(client, session):
    m = await _create_mitglied(session)
    expiring_date = (date.today() + timedelta(days=30)).isoformat()
    await client.post(
        "/api/training/lizenzen",
        json={
            **LIZENZ_DATA,
            "mitglied_id": m.id,
            "ablaufdatum": expiring_date,
            "lizenznummer": "SOON-001",
        },
    )

    # With days=10, the 30-day license should not show
    resp = await client.get("/api/training/lizenzen/expiring", params={"days": 10})
    assert resp.status_code == 200
    assert len(resp.json()) == 0

    # With days=60, it should show
    resp = await client.get("/api/training/lizenzen/expiring", params={"days": 60})
    assert resp.status_code == 200
    assert len(resp.json()) == 1


async def test_get_expiring_lizenzen_excludes_already_expired(client, session):
    """Already expired licenses should not appear in the expiring list."""
    m = await _create_mitglied(session)
    await client.post(
        "/api/training/lizenzen",
        json={
            **LIZENZ_DATA,
            "mitglied_id": m.id,
            "ablaufdatum": "2020-01-01",
        },
    )

    resp = await client.get("/api/training/lizenzen/expiring")
    assert resp.status_code == 200
    assert len(resp.json()) == 0


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
    resp = await client.delete("/api/training/lizenzen/99999")
    assert resp.status_code == 404


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


async def test_lizenzen_requires_auth(unauthed_client):
    resp = await unauthed_client.get("/api/training/lizenzen")
    assert resp.status_code in (401, 422)


async def test_lizenzen_expiring_requires_auth(unauthed_client):
    resp = await unauthed_client.get("/api/training/lizenzen/expiring")
    assert resp.status_code in (401, 422)


async def test_mitglied_anwesenheit_requires_auth(unauthed_client):
    resp = await unauthed_client.get("/api/training/anwesenheit/mitglied/1")
    assert resp.status_code in (401, 422)
