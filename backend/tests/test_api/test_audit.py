"""Tests for audit API endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from sportverein.services.audit import AuditService


async def test_list_audit_logs_empty(client: AsyncClient):
    resp = await client.get("/api/audit")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


async def test_list_audit_logs(client: AsyncClient, session: AsyncSession):
    svc = AuditService(session)
    await svc.log(action="create", entity_type="mitglied", entity_id=1)
    await svc.log(action="update", entity_type="buchung", entity_id=2)
    await session.flush()

    resp = await client.get("/api/audit")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


async def test_list_audit_logs_filter(client: AsyncClient, session: AsyncSession):
    svc = AuditService(session)
    await svc.log(action="create", entity_type="mitglied", entity_id=1)
    await svc.log(action="create", entity_type="buchung", entity_id=2)
    await session.flush()

    resp = await client.get("/api/audit", params={"entity_type": "mitglied"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["entity_type"] == "mitglied"


async def test_get_recent_audit(client: AsyncClient, session: AsyncSession):
    svc = AuditService(session)
    for i in range(5):
        await svc.log(action="create", entity_type="mitglied", entity_id=i)
    await session.flush()

    resp = await client.get("/api/audit/recent", params={"limit": 3})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3


async def test_audit_requires_auth(unauthed_client: AsyncClient):
    resp = await unauthed_client.get(
        "/api/audit",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert resp.status_code == 401
