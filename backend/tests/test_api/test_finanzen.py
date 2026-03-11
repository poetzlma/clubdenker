"""Tests for the finanzen (finance) router."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from sportverein.models.finanzen import Rechnung, RechnungStatus
from sportverein.models.mitglied import Mitglied, MitgliedStatus, BeitragKategorie
from sportverein.models.vereinsstammdaten import Vereinsstammdaten


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
    await client.post(
        "/api/finanzen/buchungen",
        json={
            **BOOKING_DATA,
            "mitglied_id": member.id,
            "sphare": "ideell",
            "betrag": 100.0,
        },
    )
    await client.post(
        "/api/finanzen/buchungen",
        json={
            **BOOKING_DATA,
            "mitglied_id": member.id,
            "sphare": "zweckbetrieb",
            "betrag": 200.0,
        },
    )

    resp2 = await client.get("/api/finanzen/kassenstand")
    body2 = resp2.json()
    assert body2["total"] == 300.0
    assert len(body2["by_sphere"]) == 2


async def test_create_invoice(client, session: AsyncSession):
    member = await _create_member(session)
    resp = await client.post(
        "/api/finanzen/rechnungen",
        json={
            "mitglied_id": member.id,
            "betrag": 240.00,
            "beschreibung": "Jahresbeitrag 2025",
            "faelligkeitsdatum": "2025-03-31",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    # New format: {YYYY}-{SPHARE_CODE}-{NR:04d}
    assert body["rechnungsnummer"].endswith("-0001")
    assert body["betrag"] == 240.00
    assert body["status"] == "entwurf"
    assert body["mitglied_id"] == member.id


async def test_record_payment(client, session: AsyncSession):
    member = await _create_member(session)
    # Create invoice
    inv_resp = await client.post(
        "/api/finanzen/rechnungen",
        json={
            "mitglied_id": member.id,
            "betrag": 240.00,
            "beschreibung": "Jahresbeitrag 2025",
            "faelligkeitsdatum": "2025-03-31",
        },
    )
    rechnung_id = inv_resp.json()["id"]

    # Record payment
    resp = await client.post(
        f"/api/finanzen/rechnungen/{rechnung_id}/zahlungen",
        json={
            "betrag": 240.00,
            "zahlungsart": "ueberweisung",
            "referenz": "TX-12345",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["betrag"] == 240.00
    assert body["zahlungsart"] == "ueberweisung"
    assert body["referenz"] == "TX-12345"


async def test_sepa_generation(client, session: AsyncSession):
    member = await _create_member(session)
    # Create invoice
    inv_resp = await client.post(
        "/api/finanzen/rechnungen",
        json={
            "mitglied_id": member.id,
            "betrag": 240.00,
            "beschreibung": "Jahresbeitrag 2025",
            "faelligkeitsdatum": "2025-03-31",
        },
    )
    rechnung_id = inv_resp.json()["id"]

    resp = await client.post(
        "/api/finanzen/sepa",
        json={
            "rechnungen_ids": [rechnung_id],
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 1
    assert "<?xml" in body["xml"]
    assert "CstmrDrctDbtInitn" in body["xml"]


async def test_fee_run(client, session: AsyncSession):
    member = await _create_member(session)
    resp = await client.post(
        "/api/finanzen/beitragslaeufe",
        json={
            "billing_year": 2025,
        },
    )
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
        summe_netto=Decimal("100.00"),
        summe_steuer=Decimal("0"),
        bezahlt_betrag=Decimal("0"),
        offener_betrag=Decimal("100.00"),
        beschreibung="Overdue test",
        rechnungsdatum=date(2024, 1, 1),
        faelligkeitsdatum=date(2024, 6, 1),  # well in the past
        status=RechnungStatus.entwurf,
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


async def test_stelle_rechnung(client, session: AsyncSession):
    """Test the stellen endpoint: ENTWURF -> GESTELLT."""
    member = await _create_member(session)
    inv_resp = await client.post(
        "/api/finanzen/rechnungen",
        json={
            "mitglied_id": member.id,
            "betrag": 100.00,
            "beschreibung": "Test invoice",
            "faelligkeitsdatum": "2026-12-31",
        },
    )
    rechnung_id = inv_resp.json()["id"]

    resp = await client.post(f"/api/finanzen/rechnungen/{rechnung_id}/stellen")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "gestellt"
    assert body["gestellt_am"] is not None


async def test_storniere_rechnung(client, session: AsyncSession):
    """Test the stornieren endpoint: creates a Stornorechnung."""
    member = await _create_member(session)
    inv_resp = await client.post(
        "/api/finanzen/rechnungen",
        json={
            "mitglied_id": member.id,
            "betrag": 200.00,
            "beschreibung": "To be cancelled",
            "faelligkeitsdatum": "2026-12-31",
        },
    )
    rechnung_id = inv_resp.json()["id"]

    resp = await client.post(
        f"/api/finanzen/rechnungen/{rechnung_id}/stornieren",
        json={"grund": "Fehlerhafte Rechnung"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["betrag"] == -200.00
    assert body["rechnungstyp"] == "storno"
    assert body["storno_von_id"] == rechnung_id


# -- Vereinsstammdaten tests -----------------------------------------------


async def test_get_vereinsstammdaten_empty(client):
    """GET vereinsstammdaten returns null when no data exists."""
    resp = await client.get("/api/finanzen/vereinsstammdaten")
    assert resp.status_code == 200
    assert resp.json() is None


async def test_put_vereinsstammdaten_creates_and_updates(client, session: AsyncSession):
    """PUT vereinsstammdaten creates on first call, updates on second."""
    data = {
        "name": "TSV Musterstadt 1900 e.V.",
        "strasse": "Sportplatzweg 1",
        "plz": "80331",
        "ort": "Muenchen",
        "iban": "DE89370400440532013000",
        "bic": "COBADEFFXXX",
        "steuernummer": "143/216/12345",
    }
    resp = await client.put("/api/finanzen/vereinsstammdaten", json=data)
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "TSV Musterstadt 1900 e.V."
    assert body["iban"] == "DE89370400440532013000"
    assert body["id"] is not None

    # Update existing
    resp2 = await client.put(
        "/api/finanzen/vereinsstammdaten",
        json={"name": "TSV Musterstadt 2000 e.V."},
    )
    assert resp2.status_code == 200
    body2 = resp2.json()
    assert body2["name"] == "TSV Musterstadt 2000 e.V."
    # Other fields should remain unchanged
    assert body2["iban"] == "DE89370400440532013000"


async def test_get_vereinsstammdaten_after_creation(client, session: AsyncSession):
    """GET vereinsstammdaten returns data after PUT creates it."""
    stamm = Vereinsstammdaten(
        name="SV Test",
        strasse="Teststr. 1",
        plz="12345",
        ort="Teststadt",
        iban="DE89370400440532013000",
    )
    session.add(stamm)
    await session.flush()

    resp = await client.get("/api/finanzen/vereinsstammdaten")
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "SV Test"
    assert body["iban"] == "DE89370400440532013000"


# -- Delete invoice tests --------------------------------------------------


async def test_delete_draft_invoice(client, session: AsyncSession):
    """DELETE a draft invoice should succeed with 204."""
    member = await _create_member(session)
    inv_resp = await client.post(
        "/api/finanzen/rechnungen",
        json={
            "mitglied_id": member.id,
            "betrag": 50.00,
            "beschreibung": "Draft to delete",
            "faelligkeitsdatum": "2026-12-31",
        },
    )
    rechnung_id = inv_resp.json()["id"]

    resp = await client.delete(f"/api/finanzen/rechnungen/{rechnung_id}")
    assert resp.status_code == 204

    # Verify it's gone
    list_resp = await client.get("/api/finanzen/rechnungen")
    ids = [r["id"] for r in list_resp.json()["items"]]
    assert rechnung_id not in ids


async def test_delete_gestellt_invoice_forbidden(client, session: AsyncSession):
    """DELETE a gestellt invoice should be forbidden (must stornieren instead)."""
    member = await _create_member(session)
    inv_resp = await client.post(
        "/api/finanzen/rechnungen",
        json={
            "mitglied_id": member.id,
            "betrag": 75.00,
            "beschreibung": "Gestellt invoice",
            "faelligkeitsdatum": "2026-12-31",
        },
    )
    rechnung_id = inv_resp.json()["id"]

    # First, stelle the invoice
    await client.post(f"/api/finanzen/rechnungen/{rechnung_id}/stellen")

    # Try to delete -- should fail
    resp = await client.delete(f"/api/finanzen/rechnungen/{rechnung_id}")
    assert resp.status_code == 403


async def test_delete_nonexistent_invoice(client):
    """DELETE a non-existent invoice should return 404."""
    resp = await client.delete("/api/finanzen/rechnungen/99999")
    assert resp.status_code == 404


# -- Skonto info tests -----------------------------------------------------


async def test_skonto_info_no_skonto(client, session: AsyncSession):
    """GET skonto for invoice without skonto returns zero discount."""
    member = await _create_member(session)
    inv_resp = await client.post(
        "/api/finanzen/rechnungen",
        json={
            "mitglied_id": member.id,
            "betrag": 100.00,
            "beschreibung": "No skonto invoice",
            "faelligkeitsdatum": "2026-12-31",
        },
    )
    rechnung_id = inv_resp.json()["id"]

    resp = await client.get(f"/api/finanzen/rechnungen/{rechnung_id}/skonto")
    assert resp.status_code == 200
    body = resp.json()
    assert body["skonto_verfuegbar"] is False
    assert body["skonto_betrag"] == 0.0
    assert body["skonto_prozent"] == 0.0


async def test_skonto_info_with_skonto(client, session: AsyncSession):
    """GET skonto for invoice with skonto returns discount details."""
    member = await _create_member(session)
    inv_resp = await client.post(
        "/api/finanzen/rechnungen",
        json={
            "mitglied_id": member.id,
            "betrag": 1000.00,
            "beschreibung": "Skonto invoice",
            "faelligkeitsdatum": "2026-12-31",
            "skonto_prozent": 2.0,
            "skonto_frist_tage": 14,
        },
    )
    rechnung_id = inv_resp.json()["id"]

    resp = await client.get(f"/api/finanzen/rechnungen/{rechnung_id}/skonto")
    assert resp.status_code == 200
    body = resp.json()
    assert body["skonto_prozent"] == 2.0
    assert body["skonto_betrag"] == 20.0
    assert body["zahlbetrag"] == 980.0
    assert body["skonto_frist_bis"] is not None


async def test_skonto_info_nonexistent_invoice(client):
    """GET skonto for non-existent invoice returns 404."""
    resp = await client.get("/api/finanzen/rechnungen/99999/skonto")
    assert resp.status_code == 404


# -- EUeR report tests -----------------------------------------------------


async def test_euer_report_empty(client):
    """GET euer report for a year with no bookings returns zeros."""
    resp = await client.get("/api/finanzen/euer", params={"jahr": 2025})
    assert resp.status_code == 200
    body = resp.json()
    assert body["jahr"] == 2025
    assert body["gesamt"]["einnahmen"] == 0.0
    assert body["gesamt"]["ausgaben"] == 0.0


async def test_euer_report_with_bookings(client, session: AsyncSession):
    """GET euer report aggregates bookings correctly."""
    member = await _create_member(session)
    # Income
    await client.post(
        "/api/finanzen/buchungen",
        json={
            **BOOKING_DATA,
            "mitglied_id": member.id,
            "betrag": 500.0,
            "sphare": "ideell",
            "buchungsdatum": "2025-06-01",
        },
    )
    # Expense
    await client.post(
        "/api/finanzen/buchungen",
        json={
            **BOOKING_DATA,
            "mitglied_id": member.id,
            "betrag": -200.0,
            "sphare": "ideell",
            "buchungsdatum": "2025-07-01",
        },
    )

    resp = await client.get("/api/finanzen/euer", params={"jahr": 2025})
    assert resp.status_code == 200
    body = resp.json()
    assert body["jahr"] == 2025
    assert body["gesamt"]["einnahmen"] == 500.0
    assert body["gesamt"]["ausgaben"] == 200.0
    assert body["gesamt"]["ergebnis"] == 300.0


async def test_euer_report_filter_by_sphare(client, session: AsyncSession):
    """GET euer report can be filtered by sphare."""
    member = await _create_member(session)
    await client.post(
        "/api/finanzen/buchungen",
        json={
            **BOOKING_DATA,
            "mitglied_id": member.id,
            "betrag": 300.0,
            "sphare": "ideell",
            "buchungsdatum": "2025-03-01",
        },
    )
    await client.post(
        "/api/finanzen/buchungen",
        json={
            **BOOKING_DATA,
            "mitglied_id": member.id,
            "betrag": 400.0,
            "sphare": "zweckbetrieb",
            "buchungsdatum": "2025-03-01",
        },
    )

    resp = await client.get(
        "/api/finanzen/euer", params={"jahr": 2025, "sphare": "ideell"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["gesamt"]["einnahmen"] == 300.0


# -- SEPA mandate CRUD tests -----------------------------------------------


MANDAT_DATA = {
    "iban": "DE89370400440532013000",
    "bic": "COBADEFFXXX",
    "kontoinhaber": "Max Mustermann",
    "mandatsreferenz": "MAND-2025-001",
    "unterschriftsdatum": "2025-01-01",
    "gueltig_ab": "2025-01-01",
}


async def test_list_mandate_empty(client):
    """GET mandate returns empty list when none exist."""
    resp = await client.get("/api/finanzen/mandate")
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["total"] == 0


async def test_create_mandat(client, session: AsyncSession):
    """POST mandate creates a new SEPA mandate."""
    member = await _create_member(session)
    data = {**MANDAT_DATA, "mitglied_id": member.id}
    resp = await client.post("/api/finanzen/mandate", json=data)
    assert resp.status_code == 201
    body = resp.json()
    assert body["iban"] == "DE89370400440532013000"
    assert body["kontoinhaber"] == "Max Mustermann"
    assert body["mandatsreferenz"] == "MAND-2025-001"
    assert body["aktiv"] is True
    assert body["mitglied_id"] == member.id
    assert body["id"] is not None


async def test_list_mandate_after_creation(client, session: AsyncSession):
    """GET mandate returns created mandates."""
    member = await _create_member(session)
    data = {**MANDAT_DATA, "mitglied_id": member.id}
    await client.post("/api/finanzen/mandate", json=data)

    resp = await client.get("/api/finanzen/mandate")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["mandatsreferenz"] == "MAND-2025-001"


async def test_update_mandat(client, session: AsyncSession):
    """PUT mandate/{id} updates an existing mandate."""
    member = await _create_member(session)
    data = {**MANDAT_DATA, "mitglied_id": member.id}
    create_resp = await client.post("/api/finanzen/mandate", json=data)
    mandat_id = create_resp.json()["id"]

    resp = await client.put(
        f"/api/finanzen/mandate/{mandat_id}",
        json={"kontoinhaber": "Erika Mustermann", "bic": "DEUTDEDBFRA"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["kontoinhaber"] == "Erika Mustermann"
    assert body["bic"] == "DEUTDEDBFRA"
    # Unchanged fields remain
    assert body["iban"] == "DE89370400440532013000"


async def test_update_mandat_not_found(client):
    """PUT mandate/{id} for non-existent mandate returns 404."""
    resp = await client.put(
        "/api/finanzen/mandate/99999",
        json={"kontoinhaber": "Nobody"},
    )
    assert resp.status_code == 404


async def test_deactivate_mandat(client, session: AsyncSession):
    """DELETE mandate/{id} deactivates (soft-deletes) a mandate."""
    member = await _create_member(session)
    data = {**MANDAT_DATA, "mitglied_id": member.id}
    create_resp = await client.post("/api/finanzen/mandate", json=data)
    mandat_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/finanzen/mandate/{mandat_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["aktiv"] is False
    assert body["id"] == mandat_id


async def test_deactivate_mandat_not_found(client):
    """DELETE mandate/{id} for non-existent mandate returns 404."""
    resp = await client.delete("/api/finanzen/mandate/99999")
    assert resp.status_code == 404


async def test_list_mandate_filter_aktiv(client, session: AsyncSession):
    """GET mandate with aktiv filter returns only matching mandates."""
    member = await _create_member(session)
    data = {**MANDAT_DATA, "mitglied_id": member.id}
    create_resp = await client.post("/api/finanzen/mandate", json=data)
    mandat_id = create_resp.json()["id"]

    # Deactivate it
    await client.delete(f"/api/finanzen/mandate/{mandat_id}")

    # Filter for active only -- should be empty
    resp = await client.get("/api/finanzen/mandate", params={"aktiv": True})
    assert resp.status_code == 200
    assert resp.json()["total"] == 0

    # Filter for inactive -- should have one
    resp2 = await client.get("/api/finanzen/mandate", params={"aktiv": False})
    assert resp2.status_code == 200
    assert resp2.json()["total"] == 1


# ---------------------------------------------------------------------------
# Rechnungsvorlagen (invoice templates)
# ---------------------------------------------------------------------------


async def test_list_templates(client):
    """GET /rechnungen/vorlagen returns all templates."""
    resp = await client.get("/api/finanzen/rechnungen/vorlagen")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) == 8
    ids = {t["id"] for t in body}
    assert "quartalsbeitrag" in ids
    assert "sponsoring" in ids


async def test_get_template_by_id(client):
    """GET /rechnungen/vorlagen/{id} returns single template."""
    resp = await client.get("/api/finanzen/rechnungen/vorlagen/hallenmiete")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == "hallenmiete"
    assert body["sphaere"] == "vermoegensverwaltung"
    assert body["zahlungsziel_tage"] == 30
    assert len(body["positionen"]) == 1
    assert body["positionen"][0]["steuersatz"] == 19


async def test_get_template_not_found(client):
    """GET /rechnungen/vorlagen/{id} returns 404 for unknown template."""
    resp = await client.get("/api/finanzen/rechnungen/vorlagen/unknown_template")
    assert resp.status_code == 404
    assert "nicht gefunden" in resp.json()["detail"]


async def test_templates_require_auth(unauthed_client):
    """Template endpoints require auth."""
    resp = await unauthed_client.get("/api/finanzen/rechnungen/vorlagen")
    assert resp.status_code in (401, 422)

    resp2 = await unauthed_client.get("/api/finanzen/rechnungen/vorlagen/quartalsbeitrag")
    assert resp2.status_code in (401, 422)


async def test_list_bookings_invalid_sphere(client, session: AsyncSession):
    """GET /buchungen?sphare=invalid returns 400."""
    resp = await client.get("/api/finanzen/buchungen", params={"sphare": "invalid"})
    assert resp.status_code == 400


async def test_list_bookings_inverted_dates(client, session: AsyncSession):
    """GET /buchungen with date_from > date_to should return 200 with empty results."""
    member = await _create_member(session)
    # Create a booking in June 2025
    await client.post(
        "/api/finanzen/buchungen",
        json={
            **BOOKING_DATA,
            "mitglied_id": member.id,
            "buchungsdatum": "2025-06-15",
        },
    )
    # Query with inverted date range
    resp = await client.get(
        "/api/finanzen/buchungen",
        params={"date_from": "2025-12-01", "date_to": "2025-01-01"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["total"] == 0


async def test_stelle_rechnung_double_call(client, session: AsyncSession):
    """Create invoice, stelle, stelle again should get error."""
    member = await _create_member(session)
    inv_resp = await client.post(
        "/api/finanzen/rechnungen",
        json={
            "mitglied_id": member.id,
            "betrag": 150.00,
            "beschreibung": "Double stelle test",
            "faelligkeitsdatum": "2026-12-31",
        },
    )
    rechnung_id = inv_resp.json()["id"]

    # First stelle succeeds
    resp1 = await client.post(f"/api/finanzen/rechnungen/{rechnung_id}/stellen")
    assert resp1.status_code == 200
    assert resp1.json()["status"] == "gestellt"

    # Second stelle should fail
    resp2 = await client.post(f"/api/finanzen/rechnungen/{rechnung_id}/stellen")
    assert resp2.status_code == 400


async def test_storniere_rechnung_without_body(client, session: AsyncSession):
    """POST stornieren without body should work (grund is optional)."""
    member = await _create_member(session)
    inv_resp = await client.post(
        "/api/finanzen/rechnungen",
        json={
            "mitglied_id": member.id,
            "betrag": 80.00,
            "beschreibung": "Storno no body test",
            "faelligkeitsdatum": "2026-12-31",
        },
    )
    rechnung_id = inv_resp.json()["id"]

    # Stornieren without a JSON body
    resp = await client.post(f"/api/finanzen/rechnungen/{rechnung_id}/stornieren")
    assert resp.status_code == 200
    body = resp.json()
    assert body["betrag"] == -80.00
    assert body["rechnungstyp"] == "storno"


# -- Ehrenamt (volunteer compensation) tests --------------------------------


async def test_list_ehrenamt_empty(client):
    """GET /ehrenamt returns empty list when no data exists."""
    resp = await client.get("/api/finanzen/ehrenamt", params={"year": 2025})
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["total"] == 0


async def test_create_ehrenamt(client, session: AsyncSession):
    """POST /ehrenamt creates a new volunteer compensation entry."""
    member = await _create_member(session)
    resp = await client.post(
        "/api/finanzen/ehrenamt",
        json={
            "mitglied_id": member.id,
            "betrag": 500.0,
            "datum": "2025-06-15",
            "typ": "uebungsleiter",
            "beschreibung": "Trainerstunden Juni",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["mitglied_id"] == member.id
    assert body["betrag"] == 500.0
    assert body["typ"] == "uebungsleiter"
    assert body["beschreibung"] == "Trainerstunden Juni"
    assert body["id"] is not None


async def test_get_freibetrag_summary(client, session: AsyncSession):
    """GET /ehrenamt/freibetrag returns summary for a given year."""
    resp = await client.get("/api/finanzen/ehrenamt/freibetrag", params={"year": 2025})
    assert resp.status_code == 200
    body = resp.json()
    assert body["year"] == 2025
    assert isinstance(body["items"], list)


# -- Versand (dispatch) tests -----------------------------------------------


async def test_versende_rechnung(client, session: AsyncSession):
    """POST /rechnungen/{id}/versenden records dispatch for a gestellt invoice."""
    member = await _create_member(session)
    inv_resp = await client.post(
        "/api/finanzen/rechnungen",
        json={
            "mitglied_id": member.id,
            "betrag": 120.00,
            "beschreibung": "Versand test",
            "faelligkeitsdatum": "2026-12-31",
        },
    )
    rechnung_id = inv_resp.json()["id"]

    # Stelle the invoice first
    stelle_resp = await client.post(f"/api/finanzen/rechnungen/{rechnung_id}/stellen")
    assert stelle_resp.status_code == 200

    # Now versenden
    resp = await client.post(
        f"/api/finanzen/rechnungen/{rechnung_id}/versenden",
        json={"kanal": "email_pdf", "empfaenger": "max@example.de"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == rechnung_id
    assert body["versand_kanal"] == "email_pdf"
    assert body["versendet_an"] == "max@example.de"
    assert body["versendet_am"] is not None


async def test_versende_rechnung_not_gestellt(client, session: AsyncSession):
    """POST /rechnungen/{id}/versenden fails for an invoice still in entwurf."""
    member = await _create_member(session)
    inv_resp = await client.post(
        "/api/finanzen/rechnungen",
        json={
            "mitglied_id": member.id,
            "betrag": 90.00,
            "beschreibung": "Draft versand test",
            "faelligkeitsdatum": "2026-12-31",
        },
    )
    rechnung_id = inv_resp.json()["id"]

    # Try to versenden without stellen first -- should fail
    resp = await client.post(
        f"/api/finanzen/rechnungen/{rechnung_id}/versenden",
        json={"kanal": "email_pdf", "empfaenger": "max@example.de"},
    )
    assert resp.status_code == 400


# -- PDF / XML / SEPA export tests ------------------------------------------


async def test_generate_invoice_pdf(client, session: AsyncSession):
    """GET /rechnungen/{id}/pdf returns a PDF for a gestellt invoice with positionen."""
    member = await _create_member(session)
    inv_resp = await client.post(
        "/api/finanzen/rechnungen",
        json={
            "mitglied_id": member.id,
            "betrag": 119.00,
            "beschreibung": "Test invoice",
            "faelligkeitsdatum": "2026-12-31",
            "positionen": [
                {
                    "beschreibung": "Item 1",
                    "menge": 1,
                    "einzelpreis_netto": 100.0,
                    "steuersatz": 19,
                }
            ],
        },
    )
    assert inv_resp.status_code == 201
    rechnung_id = inv_resp.json()["id"]

    # Stelle the invoice
    stelle_resp = await client.post(f"/api/finanzen/rechnungen/{rechnung_id}/stellen")
    assert stelle_resp.status_code == 200

    # Generate PDF
    resp = await client.get(f"/api/finanzen/rechnungen/{rechnung_id}/pdf")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert len(resp.content) > 0


async def test_generate_invoice_pdf_not_found(client):
    """GET /rechnungen/{id}/pdf returns 404 for non-existent invoice."""
    resp = await client.get("/api/finanzen/rechnungen/99999/pdf")
    assert resp.status_code == 404


async def test_generate_zugferd_xml(client, session: AsyncSession):
    """GET /rechnungen/{id}/xml returns ZUGFeRD XML for a gestellt invoice."""
    member = await _create_member(session)
    inv_resp = await client.post(
        "/api/finanzen/rechnungen",
        json={
            "mitglied_id": member.id,
            "betrag": 119.00,
            "beschreibung": "ZUGFeRD test invoice",
            "faelligkeitsdatum": "2026-12-31",
            "positionen": [
                {
                    "beschreibung": "Item 1",
                    "menge": 1,
                    "einzelpreis_netto": 100.0,
                    "steuersatz": 19,
                }
            ],
        },
    )
    assert inv_resp.status_code == 201
    rechnung_id = inv_resp.json()["id"]

    # Stelle the invoice
    stelle_resp = await client.post(f"/api/finanzen/rechnungen/{rechnung_id}/stellen")
    assert stelle_resp.status_code == 200

    # Generate ZUGFeRD XML
    resp = await client.get(f"/api/finanzen/rechnungen/{rechnung_id}/xml")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/xml"
    content = resp.content.decode("utf-8")
    assert "<?xml" in content
    assert "CrossIndustryInvoice" in content


async def test_sepa_xml_generation(client, session: AsyncSession):
    """POST /sepa with mandated member and gestellt invoice returns SEPA XML."""
    member = await _create_member(session)

    # Create SEPA mandate for the member
    mandat_resp = await client.post(
        "/api/finanzen/mandate",
        json={**MANDAT_DATA, "mitglied_id": member.id},
    )
    assert mandat_resp.status_code == 201

    # Create invoice and stelle it
    inv_resp = await client.post(
        "/api/finanzen/rechnungen",
        json={
            "mitglied_id": member.id,
            "betrag": 119.00,
            "beschreibung": "SEPA test invoice",
            "faelligkeitsdatum": "2026-12-31",
            "positionen": [
                {
                    "beschreibung": "Item 1",
                    "menge": 1,
                    "einzelpreis_netto": 100.0,
                    "steuersatz": 19,
                }
            ],
        },
    )
    assert inv_resp.status_code == 201
    rechnung_id = inv_resp.json()["id"]

    stelle_resp = await client.post(f"/api/finanzen/rechnungen/{rechnung_id}/stellen")
    assert stelle_resp.status_code == 200

    # Generate SEPA XML
    resp = await client.post(
        "/api/finanzen/sepa",
        json={"rechnungen_ids": [rechnung_id]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 1
    assert "<?xml" in body["xml"]
    assert "CstmrDrctDbtInitn" in body["xml"]


async def test_sepa_xml_no_invoices(client):
    """POST /sepa with empty rechnungen_ids returns 400."""
    resp = await client.post(
        "/api/finanzen/sepa",
        json={"rechnungen_ids": []},
    )
    assert resp.status_code == 400


# -- Pagination edge-case tests ---------------------------------------------


async def test_list_bookings_page_zero(client):
    """GET /buchungen?page=0 should return 422 (validation) or default to page 1."""
    resp = await client.get("/api/finanzen/buchungen", params={"page": 0})
    # page=0 causes offset=(0-1)*20=-20 which is invalid;
    # acceptable responses: 422 validation error, 400, or graceful fallback to page 1
    assert resp.status_code in (200, 400, 422)
    if resp.status_code == 200:
        body = resp.json()
        # If the API silently handles it, items should be empty or valid
        assert isinstance(body["items"], list)


async def test_list_bookings_negative_page_size(client):
    """GET /buchungen?page_size=-1 should return 422 or handle gracefully."""
    resp = await client.get("/api/finanzen/buchungen", params={"page_size": -1})
    # negative page_size causes LIMIT -1 which is invalid in most DBs;
    # acceptable: 422 validation error, 400, or graceful fallback
    assert resp.status_code in (200, 400, 422)
    if resp.status_code == 200:
        body = resp.json()
        assert isinstance(body["items"], list)


async def test_list_bookings_large_page(client, session: AsyncSession):
    """GET /buchungen?page=9999 should return empty items when no data at that offset."""
    member = await _create_member(session)
    await client.post(
        "/api/finanzen/buchungen",
        json={**BOOKING_DATA, "mitglied_id": member.id},
    )

    resp = await client.get("/api/finanzen/buchungen", params={"page": 9999})
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["total"] == 1  # total reflects all records, not just this page


async def test_list_rechnungen_pagination(client, session: AsyncSession):
    """Create 3 invoices, GET with page_size=2, verify total=3 and items=2."""
    member = await _create_member(session)
    for i in range(3):
        resp = await client.post(
            "/api/finanzen/rechnungen",
            json={
                "mitglied_id": member.id,
                "betrag": 100.00 + i,
                "beschreibung": f"Invoice {i}",
                "faelligkeitsdatum": "2026-12-31",
            },
        )
        assert resp.status_code == 201

    resp = await client.get(
        "/api/finanzen/rechnungen", params={"page": 1, "page_size": 2}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2
    assert body["page"] == 1
    assert body["page_size"] == 2

    # Page 2 should have the remaining 1 item
    resp2 = await client.get(
        "/api/finanzen/rechnungen", params={"page": 2, "page_size": 2}
    )
    assert resp2.status_code == 200
    body2 = resp2.json()
    assert body2["total"] == 3
    assert len(body2["items"]) == 1


# -- GET /rechnungen/{id} single invoice tests --------------------------------


async def test_get_invoice_by_id(client, session: AsyncSession):
    """GET /rechnungen/{id} returns the invoice details."""
    member = await _create_member(session)
    inv_resp = await client.post(
        "/api/finanzen/rechnungen",
        json={
            "mitglied_id": member.id,
            "betrag": 350.00,
            "beschreibung": "Single invoice test",
            "faelligkeitsdatum": "2026-12-31",
        },
    )
    assert inv_resp.status_code == 201
    rechnung_id = inv_resp.json()["id"]

    resp = await client.get(f"/api/finanzen/rechnungen/{rechnung_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == rechnung_id
    assert body["betrag"] == 350.00
    assert body["beschreibung"] == "Single invoice test"
    assert body["status"] == "entwurf"


async def test_get_invoice_not_found(client):
    """GET /rechnungen/{id} returns 404 for non-existent invoice."""
    resp = await client.get("/api/finanzen/rechnungen/99999")
    assert resp.status_code == 404


async def test_get_invoice_requires_auth(unauthed_client):
    """GET /rechnungen/{id} requires authentication."""
    resp = await unauthed_client.get("/api/finanzen/rechnungen/1")
    assert resp.status_code in (401, 422)


# -- DELETE /kostenstellen/{id} tests -----------------------------------------


async def test_delete_kostenstelle(client, session: AsyncSession):
    """DELETE /kostenstellen/{id} removes the cost center."""
    # Create a cost center
    resp = await client.post(
        "/api/finanzen/kostenstellen",
        json={"name": "Temp KS", "budget": 1000.00},
    )
    ks_id = resp.json()["id"]

    # Delete it
    del_resp = await client.delete(f"/api/finanzen/kostenstellen/{ks_id}")
    assert del_resp.status_code == 204

    # Verify it's gone
    list_resp = await client.get("/api/finanzen/kostenstellen")
    ids = [k["id"] for k in list_resp.json()]
    assert ks_id not in ids


async def test_delete_kostenstelle_not_found(client):
    """DELETE /kostenstellen/{id} returns 404 for non-existent cost center."""
    resp = await client.delete("/api/finanzen/kostenstellen/99999")
    assert resp.status_code == 404


async def test_delete_kostenstelle_with_bookings(client, session: AsyncSession):
    """DELETE /kostenstellen/{id} fails when bookings reference it."""
    from sportverein.models.finanzen import Buchung, Sphare

    member = await _create_member(session)

    # Create cost center via API
    ks_resp = await client.post(
        "/api/finanzen/kostenstellen",
        json={"name": "Linked KS", "budget": 5000.00},
    )
    ks_id = ks_resp.json()["id"]

    # Create a booking linked to the cost center directly in DB
    # (BuchungCreate schema doesn't expose kostenstelle_id)
    buchung = Buchung(
        buchungsdatum=date(2025, 1, 15),
        betrag=100,
        beschreibung="Linked booking",
        konto="4000",
        gegenkonto="1200",
        sphare=Sphare.ideell,
        mitglied_id=member.id,
        kostenstelle_id=ks_id,
    )
    session.add(buchung)
    await session.flush()

    # Attempt delete should fail
    del_resp = await client.delete(f"/api/finanzen/kostenstellen/{ks_id}")
    assert del_resp.status_code in (400, 404)


# -- GET /rechnungen/export tests --------------------------------------------


async def test_export_rechnungen_empty_year(client):
    """GET /rechnungen/export for a year with no invoices returns 404."""
    resp = await client.get(
        "/api/finanzen/rechnungen/export", params={"jahr": 1999}
    )
    assert resp.status_code == 404


async def test_export_rechnungen_requires_auth(unauthed_client):
    """GET /rechnungen/export requires authentication."""
    resp = await unauthed_client.get(
        "/api/finanzen/rechnungen/export", params={"jahr": 2025}
    )
    assert resp.status_code in (401, 422)


# -- FK validation tests ------------------------------------------------------


async def test_create_booking_invalid_mitglied(client):
    """POST /buchungen with invalid mitglied_id returns 400."""
    resp = await client.post(
        "/api/finanzen/buchungen",
        json={**BOOKING_DATA, "mitglied_id": 99999},
    )
    assert resp.status_code == 400


async def test_create_invoice_invalid_mitglied(client):
    """POST /rechnungen with invalid mitglied_id returns 400."""
    resp = await client.post(
        "/api/finanzen/rechnungen",
        json={
            "mitglied_id": 99999,
            "betrag": 100.00,
            "beschreibung": "Test",
            "faelligkeitsdatum": "2026-12-31",
        },
    )
    assert resp.status_code == 400


async def test_create_mandat_invalid_mitglied(client):
    """POST /mandate with invalid mitglied_id returns 400."""
    resp = await client.post(
        "/api/finanzen/mandate",
        json={**MANDAT_DATA, "mitglied_id": 99999},
    )
    assert resp.status_code == 400


async def test_create_ehrenamt_invalid_mitglied(client):
    """POST /ehrenamt with invalid mitglied_id returns 400."""
    resp = await client.post(
        "/api/finanzen/ehrenamt",
        json={
            "mitglied_id": 99999,
            "betrag": 500.0,
            "datum": "2025-06-15",
            "typ": "uebungsleiter",
            "beschreibung": "Test",
        },
    )
    assert resp.status_code == 400
