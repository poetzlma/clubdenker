"""Tests for the health check endpoint."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio


async def test_health_ok(login_client):
    resp = await login_client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


async def test_health_includes_version(login_client):
    resp = await login_client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "version" in data
    assert data["version"] == "1.0.0"


async def test_health_database_ok(login_client):
    resp = await login_client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["database"] == "ok"
