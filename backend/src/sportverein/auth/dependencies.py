"""FastAPI dependencies for authentication."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from sportverein.db.session import get_session


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async DB session."""
    async for session in get_session():
        yield session


async def get_current_token(
    authorization: str = Header(),
    session: AsyncSession = Depends(get_db_session),
) -> ApiToken:
    """Extract and validate Bearer token from Authorization header.

    Raises 401 if the token is missing, malformed, or invalid.
    """
    from sportverein.auth.models import ApiToken
    from sportverein.auth.service import AuthService

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header",
        )

    plain_token = authorization.removeprefix("Bearer ").strip()
    if not plain_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing",
        )

    auth_service = AuthService(session)
    token = await auth_service.validate_token(plain_token)
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    return token
