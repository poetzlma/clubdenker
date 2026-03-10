"""Auth router — login and token management."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from sportverein.api.schemas import (
    AdminResponse,
    LoginRequest,
    LoginResponse,
    TokenCreateRequest,
    TokenCreateResponse,
    TokenResponse,
)
from sportverein.auth.dependencies import get_current_token, get_db_session
from sportverein.auth.models import ApiToken
from sportverein.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    session: AsyncSession = Depends(get_db_session),
) -> LoginResponse:
    auth = AuthService(session)
    admin = await auth.authenticate(body.email, body.password)
    if admin is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    plain_token, _token_record = await auth.create_token(
        admin_user_id=admin.id, name="login-token"
    )
    await session.commit()
    return LoginResponse(
        access_token=plain_token,
        admin=AdminResponse(id=admin.id, email=admin.email, name=admin.name),
    )


@router.get("/tokens", response_model=list[TokenResponse])
async def list_tokens(
    token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> list[TokenResponse]:
    auth = AuthService(session)
    tokens = await auth.list_tokens(token.admin_user_id)
    return [TokenResponse.model_validate(t) for t in tokens]


@router.post("/tokens", response_model=TokenCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_token(
    body: TokenCreateRequest,
    token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> TokenCreateResponse:
    auth = AuthService(session)
    plain, record = await auth.create_token(
        admin_user_id=token.admin_user_id,
        name=body.name,
        expires_in_hours=body.expires_in_hours,
    )
    await session.commit()
    return TokenCreateResponse(token=plain, id=record.id, name=record.name)


@router.post("/tokens/{token_id}/rotate", response_model=TokenCreateResponse)
async def rotate_token(
    token_id: int,
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> TokenCreateResponse:
    auth = AuthService(session)
    plain, record = await auth.rotate_token(token_id)
    await session.commit()
    return TokenCreateResponse(token=plain, id=record.id, name=record.name)


@router.delete("/tokens/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_token(
    token_id: int,
    _token: ApiToken = Depends(get_current_token),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    auth = AuthService(session)
    ok = await auth.revoke_token(token_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token not found")
    await session.commit()
