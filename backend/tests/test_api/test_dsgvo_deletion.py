"""Tests for the DSGVO deletion API endpoint."""

from __future__ import annotations

from datetime import date

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


async def _create_member_via_api(client: AsyncClient) -> dict:
    """Helper to create a member via API."""
    resp = await client.post(
        "/api/mitglieder",
        json={
            "vorname": "Max",
            "nachname": "Mustermann",
            "email": "max@example.com",
            "geburtsdatum": "1990-05-15",
            "telefon": "0171-1234567",
            "strasse": "Musterstr. 1",
            "plz": "12345",
            "ort": "Musterstadt",
        },
    )
    assert resp.status_code == 201
    return resp.json()


async def test_dsgvo_delete_member(client: AsyncClient):
    member = await _create_member_via_api(client)

    resp = await client.delete(f"/api/mitglieder/{member['id']}/dsgvo-loeschen")
    assert resp.status_code == 200

    data = resp.json()
    assert data["mitglied_id"] == member["id"]
    assert data["geloescht_am"] is not None
    assert "anonymisiert" in data["message"]


async def test_dsgvo_delete_member_anonymizes_data(client: AsyncClient):
    member = await _create_member_via_api(client)

    await client.delete(f"/api/mitglieder/{member['id']}/dsgvo-loeschen")

    # Fetch the member and verify anonymization
    resp = await client.get(f"/api/mitglieder/{member['id']}")
    assert resp.status_code == 200

    data = resp.json()
    assert data["vorname"] == "Geloescht"
    assert data["nachname"] == "Geloescht"
    assert data["telefon"] is None
    assert data["strasse"] is None
    assert data["plz"] is None
    assert data["ort"] is None


async def test_dsgvo_delete_member_not_found(client: AsyncClient):
    resp = await client.delete("/api/mitglieder/9999/dsgvo-loeschen")
    assert resp.status_code == 404


async def test_dsgvo_delete_member_already_deleted(client: AsyncClient):
    member = await _create_member_via_api(client)

    # First deletion
    resp = await client.delete(f"/api/mitglieder/{member['id']}/dsgvo-loeschen")
    assert resp.status_code == 200

    # Second deletion should fail
    resp = await client.delete(f"/api/mitglieder/{member['id']}/dsgvo-loeschen")
    assert resp.status_code == 404
    assert "anonymisiert" in resp.json()["detail"]
