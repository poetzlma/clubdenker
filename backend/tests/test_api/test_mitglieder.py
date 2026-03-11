"""Tests for the mitglieder (members) router."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from sportverein.models.mitglied import Abteilung


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


async def test_create_member(client):
    resp = await client.post("/api/mitglieder", json=MEMBER_DATA)
    assert resp.status_code == 201
    data = resp.json()
    assert data["vorname"] == "Max"
    assert data["nachname"] == "Mustermann"
    assert data["mitgliedsnummer"].startswith("M-")
    assert data["status"] == "aktiv"


async def test_list_members_empty(client):
    resp = await client.get("/api/mitglieder")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1


async def test_list_members_pagination(client):
    # Create 3 members
    for i in range(3):
        await client.post(
            "/api/mitglieder",
            json={
                **MEMBER_DATA,
                "email": f"member{i}@example.de",
                "vorname": f"Member{i}",
            },
        )

    resp = await client.get("/api/mitglieder", params={"page": 1, "page_size": 2})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 2
    assert data["total"] == 3
    assert data["page_size"] == 2

    # Second page
    resp2 = await client.get("/api/mitglieder", params={"page": 2, "page_size": 2})
    data2 = resp2.json()
    assert len(data2["items"]) == 1


async def test_list_members_filter_by_name(client):
    await client.post(
        "/api/mitglieder", json={**MEMBER_DATA, "email": "search1@example.de", "vorname": "Alice"}
    )
    await client.post(
        "/api/mitglieder", json={**MEMBER_DATA, "email": "search2@example.de", "vorname": "Bob"}
    )

    resp = await client.get("/api/mitglieder", params={"name": "Alice"})
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["vorname"] == "Alice"


async def test_get_member(client):
    create_resp = await client.post("/api/mitglieder", json=MEMBER_DATA)
    member_id = create_resp.json()["id"]

    resp = await client.get(f"/api/mitglieder/{member_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == member_id
    assert data["vorname"] == "Max"


async def test_get_member_not_found(client):
    resp = await client.get("/api/mitglieder/99999")
    assert resp.status_code == 404


async def test_update_member(client):
    create_resp = await client.post("/api/mitglieder", json=MEMBER_DATA)
    member_id = create_resp.json()["id"]

    resp = await client.put(f"/api/mitglieder/{member_id}", json={"vorname": "Maximilian"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["vorname"] == "Maximilian"
    assert data["nachname"] == "Mustermann"  # unchanged


async def test_update_member_not_found(client):
    resp = await client.put("/api/mitglieder/99999", json={"vorname": "Nobody"})
    assert resp.status_code == 404


async def test_cancel_member(client):
    create_resp = await client.post("/api/mitglieder", json=MEMBER_DATA)
    member_id = create_resp.json()["id"]

    resp = await client.post(f"/api/mitglieder/{member_id}/kuendigen", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "gekuendigt"
    assert data["austrittsdatum"] is not None


async def test_cancel_member_with_date(client):
    create_resp = await client.post(
        "/api/mitglieder", json={**MEMBER_DATA, "email": "cancel2@example.de"}
    )
    member_id = create_resp.json()["id"]

    resp = await client.post(
        f"/api/mitglieder/{member_id}/kuendigen", json={"austrittsdatum": "2026-12-31"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["austrittsdatum"] == "2026-12-31"


async def test_department_assignment(client, session: AsyncSession):
    # Create a department
    dept = Abteilung(name="Fussball", beschreibung="Football dept")
    session.add(dept)
    await session.flush()
    dept_id = dept.id

    # Create a member
    create_resp = await client.post(
        "/api/mitglieder", json={**MEMBER_DATA, "email": "dept@example.de"}
    )
    member_id = create_resp.json()["id"]

    # Assign department
    resp = await client.post(f"/api/mitglieder/{member_id}/abteilungen/{dept_id}")
    assert resp.status_code == 201

    # Verify member has department
    member_resp = await client.get(f"/api/mitglieder/{member_id}")
    assert len(member_resp.json()["abteilungen"]) == 1
    assert member_resp.json()["abteilungen"][0]["abteilung_name"] == "Fussball"

    # Remove department
    del_resp = await client.delete(f"/api/mitglieder/{member_id}/abteilungen/{dept_id}")
    assert del_resp.status_code == 204


async def test_remove_department_not_found(client):
    create_resp = await client.post(
        "/api/mitglieder", json={**MEMBER_DATA, "email": "nodept@example.de"}
    )
    member_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/mitglieder/{member_id}/abteilungen/99999")
    assert resp.status_code == 404


async def test_list_departments(client, session: AsyncSession):
    dept = Abteilung(name="Tennis")
    session.add(dept)
    await session.flush()

    resp = await client.get("/api/mitglieder/abteilungen")
    assert resp.status_code == 200
    data = resp.json()
    assert any(d["name"] == "Tennis" for d in data)


async def test_401_without_auth(unauthed_client):
    resp = await unauthed_client.get("/api/mitglieder")
    assert resp.status_code in (401, 422)  # 422 if header missing, 401 if invalid


# ---------------------------------------------------------------------------
# DSGVO endpoint tests
# ---------------------------------------------------------------------------


async def test_dsgvo_datenschutz_export(client):
    """GET /api/mitglieder/{id}/datenschutz returns full DSGVO data export."""
    create_resp = await client.post(
        "/api/mitglieder", json={**MEMBER_DATA, "email": "dsgvo@example.de"}
    )
    member_id = create_resp.json()["id"]

    resp = await client.get(f"/api/mitglieder/{member_id}/datenschutz")
    assert resp.status_code == 200
    data = resp.json()
    assert "personal_data" in data
    assert "departments" in data
    assert "invoices" in data
    assert "payments" in data
    assert "sepa_mandates" in data
    assert "audit_log" in data
    assert data["personal_data"]["vorname"] == "Max"
    assert data["personal_data"]["nachname"] == "Mustermann"
    assert data["personal_data"]["email"] == "dsgvo@example.de"


async def test_dsgvo_datenschutz_export_not_found(client):
    """GET /api/mitglieder/{id}/datenschutz returns 404 for non-existent member."""
    resp = await client.get("/api/mitglieder/99999/datenschutz")
    assert resp.status_code == 404


async def test_dsgvo_loeschen(client):
    """DELETE /api/mitglieder/{id}/dsgvo-loeschen anonymizes personal data."""
    create_resp = await client.post(
        "/api/mitglieder", json={**MEMBER_DATA, "email": "delete@example.de"}
    )
    member_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/mitglieder/{member_id}/dsgvo-loeschen")
    assert resp.status_code == 200
    data = resp.json()
    assert data["mitglied_id"] == member_id
    assert data["geloescht_am"] is not None
    assert "anonymisiert" in data["message"]

    # Verify the member data is actually anonymized
    member_resp = await client.get(f"/api/mitglieder/{member_id}")
    assert member_resp.status_code == 200
    member_data = member_resp.json()
    assert member_data["vorname"] == "Geloescht"
    assert member_data["nachname"] == "Geloescht"
    assert member_data["email"] == f"geloescht-{member_id}@deleted.local"
    assert member_data["telefon"] is None
    assert member_data["strasse"] is None
    assert member_data["status"] == "gekuendigt"


async def test_dsgvo_loeschen_not_found(client):
    """DELETE /api/mitglieder/{id}/dsgvo-loeschen returns 404 for non-existent member."""
    resp = await client.delete("/api/mitglieder/99999/dsgvo-loeschen")
    assert resp.status_code == 404


async def test_dsgvo_loeschen_double_deletion(client):
    """DELETE /api/mitglieder/{id}/dsgvo-loeschen on already anonymized member returns 404."""
    create_resp = await client.post(
        "/api/mitglieder", json={**MEMBER_DATA, "email": "double@example.de"}
    )
    member_id = create_resp.json()["id"]

    # First deletion succeeds
    resp1 = await client.delete(f"/api/mitglieder/{member_id}/dsgvo-loeschen")
    assert resp1.status_code == 200

    # Second deletion should fail (already anonymized)
    resp2 = await client.delete(f"/api/mitglieder/{member_id}/dsgvo-loeschen")
    assert resp2.status_code == 404
    assert "anonymisiert" in resp2.json()["detail"]


async def test_einwilligung_set_consent(client):
    """POST /api/mitglieder/{id}/einwilligung sets consent flag."""
    create_resp = await client.post(
        "/api/mitglieder", json={**MEMBER_DATA, "email": "consent@example.de"}
    )
    member_id = create_resp.json()["id"]

    # Grant consent
    resp = await client.post(
        f"/api/mitglieder/{member_id}/einwilligung", json={"consent": True}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["member_id"] == member_id
    assert data["dsgvo_einwilligung"] is True
    assert data["einwilligung_datum"] is not None


async def test_einwilligung_revoke_consent(client):
    """POST /api/mitglieder/{id}/einwilligung can revoke consent."""
    create_resp = await client.post(
        "/api/mitglieder", json={**MEMBER_DATA, "email": "revoke@example.de"}
    )
    member_id = create_resp.json()["id"]

    # Grant consent first
    await client.post(
        f"/api/mitglieder/{member_id}/einwilligung", json={"consent": True}
    )

    # Revoke consent
    resp = await client.post(
        f"/api/mitglieder/{member_id}/einwilligung", json={"consent": False}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["dsgvo_einwilligung"] is False
    assert data["einwilligung_datum"] is None


async def test_einwilligung_not_found(client):
    """POST /api/mitglieder/{id}/einwilligung returns 404 for non-existent member."""
    resp = await client.post(
        "/api/mitglieder/99999/einwilligung", json={"consent": True}
    )
    assert resp.status_code == 404


async def test_dsgvo_export_after_anonymization(client):
    """DSGVO export after anonymization returns anonymized data."""
    create_resp = await client.post(
        "/api/mitglieder", json={**MEMBER_DATA, "email": "exportanon@example.de"}
    )
    member_id = create_resp.json()["id"]

    # Anonymize first
    await client.delete(f"/api/mitglieder/{member_id}/dsgvo-loeschen")

    # Export should still work but show anonymized data
    resp = await client.get(f"/api/mitglieder/{member_id}/datenschutz")
    assert resp.status_code == 200
    data = resp.json()
    assert data["personal_data"]["vorname"] == "Geloescht"
    assert data["personal_data"]["nachname"] == "Geloescht"
