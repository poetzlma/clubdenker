"""Tests for the setup router — BeitragsKategorien and Abteilungen CRUD."""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from sportverein.models.mitglied import (
    Abteilung,
    BeitragKategorie,
    Mitglied,
    MitgliedAbteilung,
    MitgliedStatus,
)

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_member(session: AsyncSession) -> Mitglied:
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
    session.add(member)
    await session.flush()
    await session.refresh(member)
    return member


async def _create_department(session: AsyncSession, name: str = "Fußball") -> Abteilung:
    dept = Abteilung(name=name, beschreibung=f"Abteilung {name}")
    session.add(dept)
    await session.flush()
    await session.refresh(dept)
    return dept


# ---------------------------------------------------------------------------
# BeitragsKategorien tests
# ---------------------------------------------------------------------------


async def test_list_categories_empty(client):
    resp = await client.get("/api/setup/beitragskategorien")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_create_category(client):
    resp = await client.post("/api/setup/beitragskategorien", json={
        "name": "erwachsene",
        "jahresbeitrag": 240.00,
        "beschreibung": "Erwachsene ab 18",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "erwachsene"
    assert body["jahresbeitrag"] == 240.00
    assert body["beschreibung"] == "Erwachsene ab 18"
    assert body["id"] is not None


async def test_list_categories_after_create(client):
    await client.post("/api/setup/beitragskategorien", json={
        "name": "jugend",
        "jahresbeitrag": 120.00,
    })
    resp = await client.get("/api/setup/beitragskategorien")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["name"] == "jugend"


async def test_create_category_duplicate_name(client):
    await client.post("/api/setup/beitragskategorien", json={
        "name": "passiv",
        "jahresbeitrag": 60.00,
    })
    resp = await client.post("/api/setup/beitragskategorien", json={
        "name": "passiv",
        "jahresbeitrag": 80.00,
    })
    assert resp.status_code == 400
    assert "existiert bereits" in resp.json()["detail"]


async def test_update_category(client):
    resp = await client.post("/api/setup/beitragskategorien", json={
        "name": "familie",
        "jahresbeitrag": 360.00,
    })
    cat_id = resp.json()["id"]

    resp2 = await client.put(f"/api/setup/beitragskategorien/{cat_id}", json={
        "jahresbeitrag": 400.00,
        "beschreibung": "Familienbeitrag",
    })
    assert resp2.status_code == 200
    body = resp2.json()
    assert body["jahresbeitrag"] == 400.00
    assert body["beschreibung"] == "Familienbeitrag"
    assert body["name"] == "familie"


async def test_update_category_not_found(client):
    resp = await client.put("/api/setup/beitragskategorien/9999", json={
        "jahresbeitrag": 100.00,
    })
    assert resp.status_code == 404


async def test_delete_category(client):
    resp = await client.post("/api/setup/beitragskategorien", json={
        "name": "ehrenmitglied",
        "jahresbeitrag": 0.00,
    })
    cat_id = resp.json()["id"]

    resp2 = await client.delete(f"/api/setup/beitragskategorien/{cat_id}")
    assert resp2.status_code == 204

    # Verify deleted
    resp3 = await client.get("/api/setup/beitragskategorien")
    assert len(resp3.json()) == 0


async def test_delete_category_not_found(client):
    resp = await client.delete("/api/setup/beitragskategorien/9999")
    assert resp.status_code == 404


async def test_delete_category_in_use(client, session: AsyncSession):
    """Cannot delete a category that matches a member's beitragskategorie enum value."""
    # Create a member with beitragskategorie=erwachsene
    await _create_member(session)

    # Create a BeitragsKategorie row with name matching the enum value
    resp = await client.post("/api/setup/beitragskategorien", json={
        "name": "erwachsene",
        "jahresbeitrag": 240.00,
    })
    cat_id = resp.json()["id"]

    resp2 = await client.delete(f"/api/setup/beitragskategorien/{cat_id}")
    assert resp2.status_code == 409
    assert "kann nicht gelöscht werden" in resp2.json()["detail"]


async def test_create_category_missing_name(client):
    resp = await client.post("/api/setup/beitragskategorien", json={
        "jahresbeitrag": 100.00,
    })
    assert resp.status_code == 422


async def test_create_category_missing_jahresbeitrag(client):
    resp = await client.post("/api/setup/beitragskategorien", json={
        "name": "test",
    })
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Abteilungen tests
# ---------------------------------------------------------------------------


async def test_list_departments_empty(client):
    resp = await client.get("/api/setup/abteilungen")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_create_department(client):
    resp = await client.post("/api/setup/abteilungen", json={
        "name": "Fußball",
        "beschreibung": "Fußballabteilung",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Fußball"
    assert body["beschreibung"] == "Fußballabteilung"
    assert body["id"] is not None


async def test_list_departments_after_create(client):
    await client.post("/api/setup/abteilungen", json={"name": "Tennis"})
    resp = await client.get("/api/setup/abteilungen")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["name"] == "Tennis"


async def test_create_department_duplicate_name(client):
    await client.post("/api/setup/abteilungen", json={"name": "Schwimmen"})
    resp = await client.post("/api/setup/abteilungen", json={"name": "Schwimmen"})
    assert resp.status_code == 400
    assert "existiert bereits" in resp.json()["detail"]


async def test_update_department(client):
    resp = await client.post("/api/setup/abteilungen", json={"name": "Handball"})
    dept_id = resp.json()["id"]

    resp2 = await client.put(f"/api/setup/abteilungen/{dept_id}", json={
        "name": "Handball Herren",
        "beschreibung": "Herrenmannschaft",
    })
    assert resp2.status_code == 200
    body = resp2.json()
    assert body["name"] == "Handball Herren"
    assert body["beschreibung"] == "Herrenmannschaft"


async def test_update_department_not_found(client):
    resp = await client.put("/api/setup/abteilungen/9999", json={"name": "Test"})
    assert resp.status_code == 404


async def test_delete_department(client):
    resp = await client.post("/api/setup/abteilungen", json={"name": "Volleyball"})
    dept_id = resp.json()["id"]

    resp2 = await client.delete(f"/api/setup/abteilungen/{dept_id}")
    assert resp2.status_code == 204

    # Verify deleted
    resp3 = await client.get("/api/setup/abteilungen")
    assert len(resp3.json()) == 0


async def test_delete_department_not_found(client):
    resp = await client.delete("/api/setup/abteilungen/9999")
    assert resp.status_code == 404


async def test_delete_department_in_use(client, session: AsyncSession):
    """Cannot delete a department that has members assigned."""
    member = await _create_member(session)
    dept = await _create_department(session, name="Leichtathletik")

    # Assign member to department
    assoc = MitgliedAbteilung(
        mitglied_id=member.id,
        abteilung_id=dept.id,
    )
    session.add(assoc)
    await session.flush()

    resp = await client.delete(f"/api/setup/abteilungen/{dept.id}")
    assert resp.status_code == 409
    assert "kann nicht gelöscht werden" in resp.json()["detail"]


async def test_create_department_missing_name(client):
    resp = await client.post("/api/setup/abteilungen", json={})
    assert resp.status_code == 422
