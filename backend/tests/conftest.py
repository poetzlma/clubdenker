from __future__ import annotations

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from sportverein.models.base import Base

# Import all models so tables are registered
import sportverein.models  # noqa: F401

from sportverein.auth.dependencies import get_current_token, get_db_session
from sportverein.auth.service import AuthService
from sportverein.main import app


@pytest_asyncio.fixture()
async def async_engine():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture()
async def session(async_engine):
    factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest_asyncio.fixture()
async def admin_and_token(session: AsyncSession):
    """Create an admin user and a valid API token. Returns (admin, plain_token, token_record)."""
    auth = AuthService(session)
    admin = await auth.create_admin(
        email="test@sportverein.de", password="secret123", name="Test Admin"
    )
    plain_token, token_record = await auth.create_token(admin_user_id=admin.id, name="test-token")
    await session.commit()
    return admin, plain_token, token_record


@pytest_asyncio.fixture()
async def auth_headers(admin_and_token):
    """Authorization headers with a valid Bearer token."""
    _admin, plain_token, _record = admin_and_token
    return {"Authorization": f"Bearer {plain_token}"}


@pytest_asyncio.fixture()
async def client(session: AsyncSession, admin_and_token):
    """Async HTTP test client with DB session and auth token overrides."""
    _admin, plain_token, token_record = admin_and_token

    async def _override_db_session():
        yield session

    async def _override_current_token():
        return token_record

    app.dependency_overrides[get_db_session] = _override_db_session
    app.dependency_overrides[get_current_token] = _override_current_token

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture()
async def unauthed_client(session: AsyncSession):
    """Async HTTP test client without auth token override (for testing 401)."""

    async def _override_db_session():
        yield session

    app.dependency_overrides[get_db_session] = _override_db_session
    # Do NOT override get_current_token so that auth checks happen normally

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture()
async def login_client(session: AsyncSession):
    """Async HTTP test client with only DB override (for login tests)."""

    async def _override_db_session():
        yield session

    app.dependency_overrides[get_db_session] = _override_db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    app.dependency_overrides.clear()
