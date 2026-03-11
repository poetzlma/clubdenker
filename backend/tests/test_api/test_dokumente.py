"""Tests for documents/protokoll API endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


PROTOKOLL_DATA = {
    "titel": "Vorstandssitzung Q1 2026",
    "datum": "2026-01-15",
    "inhalt": "TOP 1: Haushalt\nTOP 2: Mitgliederentwicklung",
    "typ": "vorstandssitzung",
    "erstellt_von": "Max Mustermann",
    "teilnehmer": "Max Mustermann, Erika Musterfrau",
    "beschluesse": "Haushalt einstimmig angenommen.",
}


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


async def test_create_protokoll(client: AsyncClient):
    resp = await client.post("/api/dokumente/protokolle", json=PROTOKOLL_DATA)
    assert resp.status_code == 201
    data = resp.json()
    assert data["titel"] == PROTOKOLL_DATA["titel"]
    assert data["typ"] == "vorstandssitzung"
    assert data["id"] > 0


async def test_list_protokolle(client: AsyncClient):
    await client.post("/api/dokumente/protokolle", json=PROTOKOLL_DATA)
    await client.post(
        "/api/dokumente/protokolle",
        json={**PROTOKOLL_DATA, "titel": "MV 2026", "typ": "mitgliederversammlung"},
    )
    resp = await client.get("/api/dokumente/protokolle")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


async def test_list_filter_by_typ(client: AsyncClient):
    await client.post("/api/dokumente/protokolle", json=PROTOKOLL_DATA)
    await client.post(
        "/api/dokumente/protokolle",
        json={**PROTOKOLL_DATA, "titel": "MV 2026", "typ": "mitgliederversammlung"},
    )
    resp = await client.get("/api/dokumente/protokolle?typ=vorstandssitzung")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["typ"] == "vorstandssitzung"


async def test_list_search(client: AsyncClient):
    await client.post("/api/dokumente/protokolle", json=PROTOKOLL_DATA)
    await client.post(
        "/api/dokumente/protokolle",
        json={**PROTOKOLL_DATA, "titel": "Abteilungssitzung Tennis"},
    )
    resp = await client.get("/api/dokumente/protokolle?search=Tennis")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert "Tennis" in data["items"][0]["titel"]


async def test_get_protokoll(client: AsyncClient):
    create_resp = await client.post("/api/dokumente/protokolle", json=PROTOKOLL_DATA)
    pid = create_resp.json()["id"]
    resp = await client.get(f"/api/dokumente/protokolle/{pid}")
    assert resp.status_code == 200
    assert resp.json()["id"] == pid
    assert resp.json()["inhalt"] == PROTOKOLL_DATA["inhalt"]


async def test_get_protokoll_not_found(client: AsyncClient):
    resp = await client.get("/api/dokumente/protokolle/9999")
    assert resp.status_code == 404


async def test_update_protokoll(client: AsyncClient):
    create_resp = await client.post("/api/dokumente/protokolle", json=PROTOKOLL_DATA)
    pid = create_resp.json()["id"]
    resp = await client.put(
        f"/api/dokumente/protokolle/{pid}",
        json={"titel": "Aktualisierte Sitzung"},
    )
    assert resp.status_code == 200
    assert resp.json()["titel"] == "Aktualisierte Sitzung"


async def test_delete_protokoll(client: AsyncClient):
    create_resp = await client.post("/api/dokumente/protokolle", json=PROTOKOLL_DATA)
    pid = create_resp.json()["id"]
    resp = await client.delete(f"/api/dokumente/protokolle/{pid}")
    assert resp.status_code == 204
    # Verify deleted
    resp = await client.get(f"/api/dokumente/protokolle/{pid}")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


async def test_requires_auth(unauthed_client: AsyncClient):
    resp = await unauthed_client.get("/api/dokumente/protokolle")
    assert resp.status_code in (401, 422)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


async def test_list_protokolle_invalid_typ(client: AsyncClient):
    """GET /protokolle?typ=invalid should return 400."""
    resp = await client.get("/api/dokumente/protokolle?typ=invalid_type")
    assert resp.status_code == 400


async def test_create_protokoll_invalid_typ(client: AsyncClient):
    """POST /protokolle with invalid typ should return 400 or 422."""
    data = {**PROTOKOLL_DATA, "typ": "invalid_type"}
    resp = await client.post("/api/dokumente/protokolle", json=data)
    assert resp.status_code in (400, 422)


async def test_create_protokoll_invalid_datum(client: AsyncClient):
    """POST /protokolle with invalid datum should return 400."""
    data = {**PROTOKOLL_DATA, "datum": "not-a-date"}
    resp = await client.post("/api/dokumente/protokolle", json=data)
    assert resp.status_code == 400


async def test_update_protokoll_not_found(client: AsyncClient):
    """PUT /protokolle/{id} for non-existent returns 404."""
    resp = await client.put(
        "/api/dokumente/protokolle/9999",
        json={"titel": "Does not exist"},
    )
    assert resp.status_code == 404


async def test_delete_protokoll_not_found(client: AsyncClient):
    """DELETE /protokolle/{id} for non-existent returns 404."""
    resp = await client.delete("/api/dokumente/protokolle/9999")
    assert resp.status_code == 404
