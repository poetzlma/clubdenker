"""Tests for MCP audit log tool (batch 2)."""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from sportverein.models.base import Base

# Register all models
import sportverein.models  # noqa: F401

from sportverein.mcp.session import set_session_factory
from sportverein.mcp.tools_audit import audit_logs_abrufen
from sportverein.models.audit import AuditLog


@pytest_asyncio.fixture()
async def mcp_engine():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture()
async def mcp_session_factory(mcp_engine):
    factory = async_sessionmaker(
        mcp_engine, class_=AsyncSession, expire_on_commit=False
    )
    set_session_factory(factory)
    yield factory
    set_session_factory(None)


@pytest_asyncio.fixture()
async def mcp_session(mcp_session_factory):
    async with mcp_session_factory() as session:
        yield session


@pytest_asyncio.fixture()
async def seed_audit_logs(mcp_session: AsyncSession):
    """Create sample audit log entries."""
    logs = [
        AuditLog(action="create", entity_type="mitglied", entity_id=1, details="Neues Mitglied angelegt"),
        AuditLog(action="update", entity_type="mitglied", entity_id=1, details="Name geaendert"),
        AuditLog(action="create", entity_type="buchung", entity_id=10, details="Neue Buchung"),
        AuditLog(action="delete", entity_type="rechnung", entity_id=5, details="Rechnung geloescht"),
    ]
    for log in logs:
        mcp_session.add(log)
    await mcp_session.commit()
    return logs


@pytest.mark.asyncio
async def test_audit_logs_abrufen_empty(mcp_session_factory):
    result = await audit_logs_abrufen()
    assert result["items"] == []
    assert result["total"] == 0


@pytest.mark.asyncio
async def test_audit_logs_abrufen_all(mcp_session_factory, seed_audit_logs):
    result = await audit_logs_abrufen()
    assert result["total"] == 4
    assert len(result["items"]) == 4
    # Should have expected fields
    item = result["items"][0]
    assert "id" in item
    assert "timestamp" in item
    assert "action" in item
    assert "entity_type" in item


@pytest.mark.asyncio
async def test_audit_logs_abrufen_filter_action(mcp_session_factory, seed_audit_logs):
    result = await audit_logs_abrufen(aktion="create")
    assert result["total"] == 2
    for item in result["items"]:
        assert item["action"] == "create"


@pytest.mark.asyncio
async def test_audit_logs_abrufen_filter_bereich(mcp_session_factory, seed_audit_logs):
    result = await audit_logs_abrufen(bereich="mitglied")
    assert result["total"] == 2
    for item in result["items"]:
        assert item["entity_type"] == "mitglied"


@pytest.mark.asyncio
async def test_audit_logs_abrufen_filter_combined(mcp_session_factory, seed_audit_logs):
    result = await audit_logs_abrufen(aktion="create", bereich="mitglied")
    assert result["total"] == 1
    assert result["items"][0]["entity_type"] == "mitglied"
    assert result["items"][0]["action"] == "create"


@pytest.mark.asyncio
async def test_audit_logs_abrufen_limit(mcp_session_factory, seed_audit_logs):
    result = await audit_logs_abrufen(limit=2)
    assert len(result["items"]) == 2
    assert result["total"] == 4
