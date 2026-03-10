"""Integration tests: verify MCP changes are visible via the REST API.

The root cause of the two-database bug was a relative DB path that resolved
differently depending on the working directory.  These tests ensure that
both layers share the same session/database so that writes in MCP are
immediately readable through the API.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from sportverein.models.base import Base
import sportverein.models  # noqa: F401
from sportverein.auth.dependencies import get_current_token, get_db_session
from sportverein.auth.service import AuthService
from sportverein.main import app
from sportverein.mcp.session import set_session_factory
from sportverein.services.mitglieder import MitgliederService, MitgliedCreate, MitgliedUpdate
from sportverein.services.finanzen import FinanzenService


@pytest_asyncio.fixture()
async def shared_engine():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture()
async def shared_factory(shared_engine):
    return async_sessionmaker(
        shared_engine, class_=AsyncSession, expire_on_commit=False
    )


@pytest_asyncio.fixture()
async def mcp_session(shared_factory):
    """Session simulating MCP tool usage."""
    set_session_factory(shared_factory)
    async with shared_factory() as session:
        yield session
    set_session_factory(None)


@pytest_asyncio.fixture()
async def api_client(shared_factory):
    """HTTP client sharing the same DB as MCP."""
    async with shared_factory() as session:
        auth = AuthService(session)
        admin = await auth.create_admin(
            email="test@sportverein.de", password="secret123", name="Test Admin"
        )
        _plain_token, token_record = await auth.create_token(
            admin_user_id=admin.id, name="test-token"
        )
        await session.commit()

    async def _override_db_session():
        async with shared_factory() as s:
            yield s

    async def _override_current_token():
        return token_record

    app.dependency_overrides[get_db_session] = _override_db_session
    app.dependency_overrides[get_current_token] = _override_current_token

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Mitglieder
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mcp_member_visible_in_api(mcp_session: AsyncSession, api_client: AsyncClient):
    """A member created via MCP service must appear in the API."""
    svc = MitgliederService(mcp_session)
    member = await svc.create_member(MitgliedCreate(
        vorname="Test",
        nachname="MCP-User",
        email="test.mcp@example.de",
        geburtsdatum="1990-01-01",
    ))
    await mcp_session.commit()

    resp = await api_client.get("/api/mitglieder")
    assert resp.status_code == 200
    data = resp.json()
    ids = [m["id"] for m in data["items"]]
    assert member.id in ids, "Member created via MCP not visible in API"


@pytest.mark.asyncio
async def test_mcp_member_update_visible_in_api(mcp_session: AsyncSession, api_client: AsyncClient):
    """A member updated via MCP must show updated data in the API."""
    svc = MitgliederService(mcp_session)
    member = await svc.create_member(MitgliedCreate(
        vorname="Original",
        nachname="Name",
        email="original@example.de",
        geburtsdatum="1985-06-15",
    ))
    await mcp_session.commit()

    await svc.update_member(member.id, MitgliedUpdate(vorname="Updated"))
    await mcp_session.commit()

    resp = await api_client.get(f"/api/mitglieder/{member.id}")
    assert resp.status_code == 200
    assert resp.json()["vorname"] == "Updated"


# ---------------------------------------------------------------------------
# Buchungen (Finanzen)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mcp_buchung_visible_in_api(mcp_session: AsyncSession, api_client: AsyncClient):
    """A booking created via MCP service must appear in the API."""
    svc = FinanzenService(mcp_session)
    buchung = await svc.create_booking({
        "buchungsdatum": __import__("datetime").date(2026, 3, 10),
        "betrag": 150.00,
        "beschreibung": "Testbuchung via MCP",
        "konto": "4100",
        "gegenkonto": "1200",
        "sphare": "ideell",
    })
    await mcp_session.commit()

    resp = await api_client.get("/api/finanzen/buchungen")
    assert resp.status_code == 200
    data = resp.json()
    ids = [b["id"] for b in data["items"]]
    assert buchung.id in ids, "Buchung created via MCP not visible in API"


# ---------------------------------------------------------------------------
# Config: absolute DB path
# ---------------------------------------------------------------------------


def test_database_url_is_absolute():
    """DB path must be absolute so MCP and API always resolve to the same file."""
    import os
    from sportverein.config import settings

    url = settings.database_url
    assert url.startswith("sqlite+aiosqlite:///"), f"Unexpected DB URL scheme: {url}"
    db_path = url.removeprefix("sqlite+aiosqlite:///")
    assert os.path.isabs(db_path), f"DB path must be absolute, got: {db_path}"
