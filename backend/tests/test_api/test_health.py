"""Tests for the health check endpoint."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

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


async def test_health_database_error(login_client):
    """When the database is unreachable, health returns 503 with degraded status."""
    mock_session = AsyncMock()
    mock_session.execute.side_effect = ConnectionError("DB down")

    with patch("sportverein.api.health.get_db_session", return_value=mock_session):
        # The dependency override in the test client doesn't apply here,
        # so we test the function directly instead
        from sportverein.api.health import health_check

        response = await health_check(session=mock_session)
        assert response.status_code == 503
        import json

        body = json.loads(response.body)
        assert body["status"] == "degraded"
        assert body["database"] == "error"
        assert "DB down" in body["detail"]
