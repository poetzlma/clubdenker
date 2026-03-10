from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from sportverein.auth.models import AdminUser, ApiToken
from sportverein.auth.service import AuthService


# ── Helpers ────────────────────────────────────────────────────────────


async def _create_admin(session, email="admin@example.com"):
    svc = AuthService(session)
    admin = await svc.create_admin(email=email, password="secret123", name="Test Admin")
    await session.flush()
    return admin


# ── Admin user tests ──────────────────────────────────────────────────


class TestCreateAdmin:
    async def test_create_admin(self, session):
        svc = AuthService(session)
        admin = await svc.create_admin(
            email="admin@example.com", password="secret123", name="Test Admin"
        )
        assert admin.id is not None
        assert admin.email == "admin@example.com"
        assert admin.name == "Test Admin"
        assert admin.hashed_password != "secret123"
        assert admin.is_active is True


class TestAuthenticate:
    async def test_correct_password(self, session):
        admin = await _create_admin(session)
        svc = AuthService(session)
        result = await svc.authenticate("admin@example.com", "secret123")
        assert result is not None
        assert result.id == admin.id

    async def test_wrong_password(self, session):
        await _create_admin(session)
        svc = AuthService(session)
        result = await svc.authenticate("admin@example.com", "wrong")
        assert result is None

    async def test_nonexistent_email(self, session):
        svc = AuthService(session)
        result = await svc.authenticate("nobody@example.com", "secret")
        assert result is None


# ── Token tests ───────────────────────────────────────────────────────


class TestTokenLifecycle:
    async def test_create_and_validate_token(self, session):
        admin = await _create_admin(session)
        svc = AuthService(session)

        plain, token = await svc.create_token(admin.id, "CI token")
        assert isinstance(plain, str)
        assert len(plain) > 20
        assert token.name == "CI token"
        assert token.is_active is True

        validated = await svc.validate_token(plain)
        assert validated is not None
        assert validated.id == token.id
        assert validated.last_used_at is not None

    async def test_invalid_token_rejected(self, session):
        svc = AuthService(session)
        result = await svc.validate_token("bogus-token-value")
        assert result is None

    async def test_expired_token_rejected(self, session):
        admin = await _create_admin(session)
        svc = AuthService(session)

        plain, token = await svc.create_token(admin.id, "short-lived", expires_in_hours=1)
        # Manually expire it
        token.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        await session.flush()

        result = await svc.validate_token(plain)
        assert result is None

    async def test_revoke_token(self, session):
        admin = await _create_admin(session)
        svc = AuthService(session)

        plain, token = await svc.create_token(admin.id, "to-revoke")
        assert await svc.revoke_token(token.id) is True

        result = await svc.validate_token(plain)
        assert result is None

    async def test_rotate_token(self, session):
        admin = await _create_admin(session)
        svc = AuthService(session)

        old_plain, old_token = await svc.create_token(admin.id, "rotate-me")
        new_plain, new_token = await svc.rotate_token(old_token.id)

        # Old token is now invalid
        assert await svc.validate_token(old_plain) is None
        # New token is valid
        validated = await svc.validate_token(new_plain)
        assert validated is not None
        assert validated.id == new_token.id
        # Name is preserved
        assert new_token.name == "rotate-me"

    async def test_list_tokens(self, session):
        admin = await _create_admin(session)
        svc = AuthService(session)

        await svc.create_token(admin.id, "token-1")
        await svc.create_token(admin.id, "token-2")

        tokens = await svc.list_tokens(admin.id)
        assert len(tokens) == 2
        names = {t.name for t in tokens}
        assert names == {"token-1", "token-2"}
