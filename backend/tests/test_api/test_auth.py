"""Tests for the auth router."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from sportverein.auth.service import AuthService


pytestmark = pytest.mark.asyncio


async def test_login_success(login_client, session: AsyncSession):
    auth = AuthService(session)
    await auth.create_admin(email="login@test.de", password="pass123", name="Login Admin")
    await session.commit()

    resp = await login_client.post(
        "/auth/login", json={"email": "login@test.de", "password": "pass123"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["admin"]["email"] == "login@test.de"
    assert data["admin"]["name"] == "Login Admin"


async def test_login_wrong_credentials(login_client, session: AsyncSession):
    auth = AuthService(session)
    await auth.create_admin(email="wrong@test.de", password="pass123", name="Admin")
    await session.commit()

    resp = await login_client.post(
        "/auth/login", json={"email": "wrong@test.de", "password": "wrongpass"}
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid credentials"


async def test_login_nonexistent_user(login_client):
    resp = await login_client.post(
        "/auth/login", json={"email": "nobody@test.de", "password": "pass123"}
    )
    assert resp.status_code == 401


async def test_list_tokens(client):
    resp = await client.get("/auth/tokens")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    # At least the token used for auth should exist
    assert len(data) >= 1


async def test_create_token(client):
    resp = await client.post("/auth/tokens", json={"name": "new-token"})
    assert resp.status_code == 201
    data = resp.json()
    assert "token" in data
    assert data["name"] == "new-token"
    assert "id" in data


async def test_create_token_with_expiry(client):
    resp = await client.post("/auth/tokens", json={"name": "expiring", "expires_in_hours": 48})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "expiring"


async def test_rotate_token(client, admin_and_token):
    _admin, _plain, token_record = admin_and_token
    resp = await client.post(f"/auth/tokens/{token_record.id}/rotate")
    assert resp.status_code == 200
    data = resp.json()
    assert "token" in data
    assert data["name"] == token_record.name


async def test_revoke_token(client, session: AsyncSession, admin_and_token):
    _admin, _plain, _token_record = admin_and_token
    # Create a fresh token to revoke
    auth = AuthService(session)
    _plain2, record2 = await auth.create_token(admin_user_id=_admin.id, name="to-revoke")
    await session.commit()

    resp = await client.delete(f"/auth/tokens/{record2.id}")
    assert resp.status_code == 204


async def test_revoke_nonexistent_token(client):
    resp = await client.delete("/auth/tokens/99999")
    assert resp.status_code == 404
