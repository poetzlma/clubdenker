from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt as _bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sportverein.auth.models import AdminUser, ApiToken


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ── Admin user management ──────────────────────────────────────────

    async def create_admin(self, email: str, password: str, name: str) -> AdminUser:
        """Create an admin user with a bcrypt-hashed password."""
        hashed = _bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode()
        admin = AdminUser(email=email, hashed_password=hashed, name=name)
        self.session.add(admin)
        await self.session.flush()
        return admin

    async def authenticate(self, email: str, password: str) -> AdminUser | None:
        """Verify credentials; returns the admin user or None."""
        result = await self.session.execute(
            select(AdminUser).where(AdminUser.email == email, AdminUser.is_active == True)  # noqa: E712
        )
        admin = result.scalar_one_or_none()
        if admin is None:
            return None
        if not _bcrypt.checkpw(password.encode(), admin.hashed_password.encode()):
            return None
        return admin

    # ── API token management ───────────────────────────────────────────

    @staticmethod
    def _hash_token(plain_token: str) -> str:
        return hashlib.sha256(plain_token.encode()).hexdigest()

    async def create_token(
        self,
        admin_user_id: int,
        name: str,
        expires_in_hours: int | None = None,
    ) -> tuple[str, ApiToken]:
        """Generate a new API token.

        Returns (plain_token, token_record). The plain token is shown only once.
        """
        plain_token = secrets.token_urlsafe(32)
        token_hash = self._hash_token(plain_token)

        expires_at = None
        if expires_in_hours is not None:
            expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)

        token = ApiToken(
            name=name,
            token_hash=token_hash,
            admin_user_id=admin_user_id,
            expires_at=expires_at,
        )
        self.session.add(token)
        await self.session.flush()
        return plain_token, token

    async def validate_token(self, plain_token: str) -> ApiToken | None:
        """Hash the token, look up in DB, check validity, update last_used_at."""
        token_hash = self._hash_token(plain_token)
        result = await self.session.execute(
            select(ApiToken).where(
                ApiToken.token_hash == token_hash,
                ApiToken.is_active == True,  # noqa: E712
            )
        )
        token = result.scalar_one_or_none()
        if token is None:
            return None

        # Check expiry
        if token.expires_at is not None:
            now = datetime.now(timezone.utc)
            expires = token.expires_at
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            if now >= expires:
                return None

        token.last_used_at = datetime.now(timezone.utc)
        await self.session.flush()
        return token

    async def rotate_token(self, token_id: int) -> tuple[str, ApiToken]:
        """Deactivate old token and create a new one with the same name."""
        result = await self.session.execute(select(ApiToken).where(ApiToken.id == token_id))
        old_token = result.scalar_one()
        old_token.is_active = False
        await self.session.flush()

        return await self.create_token(
            admin_user_id=old_token.admin_user_id,
            name=old_token.name,
        )

    async def revoke_token(self, token_id: int) -> bool:
        """Set is_active = False on a token."""
        result = await self.session.execute(select(ApiToken).where(ApiToken.id == token_id))
        token = result.scalar_one_or_none()
        if token is None:
            return False
        token.is_active = False
        await self.session.flush()
        return True

    async def list_tokens(self, admin_user_id: int) -> list[ApiToken]:
        """List all tokens for an admin user."""
        result = await self.session.execute(
            select(ApiToken).where(ApiToken.admin_user_id == admin_user_id)
        )
        return list(result.scalars().all())
