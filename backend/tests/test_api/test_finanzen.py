"""Tests for the finanzen (finance) router."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from sportverein.models.finanzen import Buchung, Rechnung, RechnungStatus, Sphare
from sportverein.models.mitglied import Mitglied, MitgliedStatus, BeitragKategorie


pytestmark = pytest.mark.asyncio

MEMBER_DATA = {
    "vorname": "Max",
    "nachname": "Mustermann",
    "email": "max@example.de",
    "geburtsdatum": "1990-05-15",
    "telefon": "0151-12345",
    "strasse": "Hauptstr. 1",
    "plz": "80331",
    "ort": "Muenchen",
}

BOOKING_DATA = {
    "buchungsdatum": "2025-01-15",
    "betrag": 100.00,
    "beschreibung": "Mitgliedsbeitrag",
    "konto": "1200",
    "gegenkonto": "4000",
    "sphare": "ideell",
}


async def _create_member(session: AsyncSession) -> Mitglied:
    """Helper to create a member directly in the DB."""
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


async def test_create_booking(client, session: AsyncSession):
    member = await _create_member(session)
    data = {**BOOKING_DATA, "mitglied_id": member.id}
    resp = await client.post("/api/finanzen/buchungen", json=data)
    assert resp.status_code == 201
    body = resp.json()
    assert body["betrag"] == 100.00
    assert body["sphare"] == "ideell"
    assert body["konto"] == "1200"
    assert body["id"] is not None


async def test_list_bookings(client, session: AsyncSession):
    resp = await client.get("/api/finanzen/buchungen")
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["total"] == 0
    assert body["page"] == 1

    # Create a booking and verify it shows up
    member = await _create_member(session)
    data = {**BOOKING_DATA, "mitglied_id": member.id}
    await client.post("/api/finanzen/buchungen", json=data)

    resp2 = await client.get("/api/finanzen/buchungen")
    body2 = resp2.json()
    assert body2["total"] == 1
    assert len(body2["items"]) == 1


async def test_get_balance(client, session: AsyncSession):
    # Empty balance
    resp = await client.get("/api/finanzen/kassenstand")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0.0

    # Create bookings in different spheres
    member = await _create_member(session)
    await client.post("/api/finanzen/buchungen", json={
        **BOOKING_DATA, "mitglied_id": member.id, "sphare": "ideell", "betrag": 100.0,
    })
    await client.post("/api/finanzen/buchungen", json={
        **BOOKING_DATA, "mitglied_id": member.id, "sphare": "zweckbetrieb", "betrag": 200.0,
    })

    resp2 = await client.get("/api/finanzen/kassenstand")
    body2 = resp2.json()
    assert body2["total"] == 300.0
    assert len(body2["by_sphere"]) == 2


async def test_create_invoice(client, session: AsyncSession):
    member = await _create_member(session)
    resp = await client.post("/api/finanzen/rechnungen", json={
        "mitglied_id": member.id,
        "betrag": 240.00,
        "beschreibung": "Jahresbeitrag 2025",
        "faelligkeitsdatum": "2025-03-31",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["rechnungsnummer"] == "R-0001"
    assert body["betrag"] == 240.00
    assert body["status"] == "offen"
    assert body["mitglied_id"] == member.id


async def test_record_payment(client, session: AsyncSession):
    member = await _create_member(session)
    # Create invoice
    inv_resp = await client.post("/api/finanzen/rechnungen", json={
        "mitglied_id": member.id,
        "betrag": 240.00,
        "beschreibung": "Jahresbeitrag 2025",
        "faelligkeitsdatum": "2025-03-31",
    })
    rechnung_id = inv_resp.json()["id"]

    # Record payment
    resp = await client.post(f"/api/finanzen/rechnungen/{rechnung_id}/zahlungen", json={
        "betrag": 240.00,
        "zahlungsart": "ueberweisung",
        "referenz": "TX-12345",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["betrag"] == 240.00
    assert body["zahlungsart"] == "ueberweisung"
    assert body["referenz"] == "TX-12345"


async def test_sepa_generation(client, session: AsyncSession):
    member = await _create_member(session)
    # Create invoice
    inv_resp = await client.post("/api/finanzen/rechnungen", json={
        "mitglied_id": member.id,
        "betrag": 240.00,
        "beschreibung": "Jahresbeitrag 2025",
        "faelligkeitsdatum": "2025-03-31",
    })
    rechnung_id = inv_resp.json()["id"]

    resp = await client.post("/api/finanzen/sepa", json={
        "rechnungen_ids": [rechnung_id],
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 1
    assert "<?xml" in body["xml"]
    assert "CstmrDrctDbtInitn" in body["xml"]


async def test_fee_run(client, session: AsyncSession):
    member = await _create_member(session)
    resp = await client.post("/api/finanzen/beitragslaeufe", json={
        "billing_year": 2025,
    })
    assert resp.status_code == 201
    body = resp.json()
    assert len(body) >= 1
    assert body[0]["beschreibung"] == "Mitgliedsbeitrag 2025"
    assert body[0]["mitglied_id"] == member.id


async def test_dunning_candidates(client, session: AsyncSession):
    member = await _create_member(session)
    # Create an overdue invoice directly in the DB
    rechnung = Rechnung(
        rechnungsnummer="R-9999",
        mitglied_id=member.id,
        betrag=Decimal("100.00"),
        beschreibung="Overdue test",
        rechnungsdatum=date(2024, 1, 1),
        faelligkeitsdatum=date(2024, 6, 1),  # well in the past
        status=RechnungStatus.offen,
    )
    session.add(rechnung)
    await session.flush()

    resp = await client.get("/api/finanzen/mahnungen")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) >= 1
    assert any(r["rechnungsnummer"] == "R-9999" for r in body)


async def test_401_without_auth(unauthed_client):
    resp = await unauthed_client.get("/api/finanzen/buchungen")
    assert resp.status_code in (401, 422)

    resp2 = await unauthed_client.get("/api/finanzen/kassenstand")
    assert resp2.status_code in (401, 422)

    resp3 = await unauthed_client.get("/api/finanzen/rechnungen")
    assert resp3.status_code in (401, 422)
