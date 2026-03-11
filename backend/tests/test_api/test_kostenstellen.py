"""Tests for Kostenstellen and Leistungsverrechnung API endpoints."""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from sportverein.models.mitglied import BeitragKategorie, Mitglied, MitgliedStatus


pytestmark = pytest.mark.asyncio


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


async def test_create_kostenstelle(client, session: AsyncSession):
    resp = await client.post(
        "/api/finanzen/kostenstellen",
        json={
            "name": "Fußball",
            "beschreibung": "Fußballabteilung",
            "budget": 10000.00,
            "freigabelimit": 500.00,
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Fußball"
    assert body["beschreibung"] == "Fußballabteilung"
    assert body["budget"] == 10000.00
    assert body["freigabelimit"] == 500.00
    assert body["id"] is not None


async def test_list_kostenstellen(client, session: AsyncSession):
    # Empty list first
    resp = await client.get("/api/finanzen/kostenstellen")
    assert resp.status_code == 200
    assert resp.json() == []

    # Create one
    await client.post(
        "/api/finanzen/kostenstellen",
        json={
            "name": "Tennis",
            "budget": 5000.00,
        },
    )

    resp2 = await client.get("/api/finanzen/kostenstellen")
    assert resp2.status_code == 200
    body = resp2.json()
    assert len(body) == 1
    assert body[0]["name"] == "Tennis"
    assert body[0]["budget"] == 5000.00
    assert body[0]["spent"] == 0.0
    assert body[0]["remaining"] == 5000.00


async def test_update_kostenstelle(client, session: AsyncSession):
    # Create
    resp = await client.post(
        "/api/finanzen/kostenstellen",
        json={
            "name": "Schwimmen",
            "budget": 3000.00,
        },
    )
    ks_id = resp.json()["id"]

    # Update budget and freigabelimit
    resp2 = await client.put(
        f"/api/finanzen/kostenstellen/{ks_id}",
        json={
            "budget": 5000.00,
            "freigabelimit": 200.00,
        },
    )
    assert resp2.status_code == 200
    body = resp2.json()
    assert body["budget"] == 5000.00
    assert body["freigabelimit"] == 200.00
    assert body["name"] == "Schwimmen"


async def test_update_kostenstelle_not_found(client):
    resp = await client.put(
        "/api/finanzen/kostenstellen/9999",
        json={
            "budget": 1000.00,
        },
    )
    assert resp.status_code == 404


async def test_leistungsverrechnung(client, session: AsyncSession):
    # Create two cost centers
    resp1 = await client.post(
        "/api/finanzen/kostenstellen",
        json={
            "name": "Fußball",
            "budget": 10000.00,
        },
    )
    ks1_id = resp1.json()["id"]

    resp2 = await client.post(
        "/api/finanzen/kostenstellen",
        json={
            "name": "Tennis",
            "budget": 5000.00,
        },
    )
    ks2_id = resp2.json()["id"]

    # Create a booking
    member = await _create_member(session)
    booking_resp = await client.post(
        "/api/finanzen/buchungen",
        json={
            "buchungsdatum": "2025-01-15",
            "betrag": 1000.00,
            "beschreibung": "Hallenbelegung",
            "konto": "4000",
            "gegenkonto": "1200",
            "sphare": "ideell",
            "mitglied_id": member.id,
        },
    )
    buchung_id = booking_resp.json()["id"]

    # Allocate shared costs: 60% Fußball, 40% Tennis
    resp = await client.post(
        "/api/finanzen/leistungsverrechnung",
        json={
            "buchung_id": buchung_id,
            "allocations": [
                {"kostenstelle_id": ks1_id, "anteil": 0.6},
                {"kostenstelle_id": ks2_id, "anteil": 0.4},
            ],
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["parent_buchung_id"] == buchung_id
    assert len(body["children"]) == 2

    # Check amounts
    amounts = sorted([c["betrag"] for c in body["children"]])
    assert amounts[0] == pytest.approx(400.00, abs=0.01)
    assert amounts[1] == pytest.approx(600.00, abs=0.01)


async def test_leistungsverrechnung_invalid_sum(client, session: AsyncSession):
    """Allocations must sum to 1.0."""
    await _create_member(session)

    # Create a booking and a cost center
    booking_resp = await client.post(
        "/api/finanzen/buchungen",
        json={
            "buchungsdatum": "2025-01-15",
            "betrag": 1000.00,
            "beschreibung": "Test",
            "konto": "4000",
            "gegenkonto": "1200",
            "sphare": "ideell",
        },
    )
    buchung_id = booking_resp.json()["id"]

    ks_resp = await client.post(
        "/api/finanzen/kostenstellen",
        json={
            "name": "Test KS",
            "budget": 5000.00,
        },
    )
    ks_id = ks_resp.json()["id"]

    resp = await client.post(
        "/api/finanzen/leistungsverrechnung",
        json={
            "buchung_id": buchung_id,
            "allocations": [
                {"kostenstelle_id": ks_id, "anteil": 0.5},
            ],
        },
    )
    assert resp.status_code == 400
