"""Comprehensive tests for MCP setup tools (batch 2)."""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from sportverein.models.base import Base

# Register all models
import sportverein.models  # noqa: F401

from sportverein.mcp.session import set_session_factory
from sportverein.mcp.tools_setup import (
    vereins_setup_abteilungen,
    vereins_setup_beitragskategorien,
)


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
    factory = async_sessionmaker(mcp_engine, class_=AsyncSession, expire_on_commit=False)
    set_session_factory(factory)
    yield factory
    set_session_factory(None)


@pytest_asyncio.fixture()
async def mcp_session(mcp_session_factory):
    async with mcp_session_factory() as session:
        yield session


# -- vereins_setup_abteilungen -----------------------------------------------


@pytest.mark.asyncio
async def test_abteilungen_list_empty(mcp_session_factory):
    result = await vereins_setup_abteilungen(action="list")
    assert result["items"] == []


@pytest.mark.asyncio
async def test_abteilungen_create(mcp_session_factory):
    result = await vereins_setup_abteilungen(
        action="create",
        name="Handball",
        beschreibung="Handballabteilung",
    )
    assert result["name"] == "Handball"
    assert result["beschreibung"] == "Handballabteilung"
    assert "id" in result
    assert result["message"] == "Abteilung erfolgreich erstellt."


@pytest.mark.asyncio
async def test_abteilungen_create_missing_name(mcp_session_factory):
    result = await vereins_setup_abteilungen(action="create")
    assert "error" in result


@pytest.mark.asyncio
async def test_abteilungen_update(mcp_session_factory):
    created = await vereins_setup_abteilungen(
        action="create",
        name="Schwimmen",
    )
    result = await vereins_setup_abteilungen(
        action="update",
        department_id=created["id"],
        name="Schwimmen & Tauchen",
        beschreibung="Erweitert",
    )
    assert result["name"] == "Schwimmen & Tauchen"
    assert result["beschreibung"] == "Erweitert"
    assert result["message"] == "Abteilung erfolgreich aktualisiert."


@pytest.mark.asyncio
async def test_abteilungen_delete(mcp_session_factory):
    created = await vereins_setup_abteilungen(
        action="create",
        name="Leichtathletik",
    )
    result = await vereins_setup_abteilungen(
        action="delete",
        department_id=created["id"],
    )
    assert "message" in result

    # Verify gone
    listed = await vereins_setup_abteilungen(action="list")
    assert len(listed["items"]) == 0


@pytest.mark.asyncio
async def test_abteilungen_delete_missing_id(mcp_session_factory):
    result = await vereins_setup_abteilungen(action="delete")
    assert "error" in result


# -- vereins_setup_beitragskategorien ----------------------------------------


@pytest.mark.asyncio
async def test_beitragskategorien_list_empty(mcp_session_factory):
    result = await vereins_setup_beitragskategorien(action="list")
    assert result["items"] == []


@pytest.mark.asyncio
async def test_beitragskategorien_create(mcp_session_factory):
    result = await vereins_setup_beitragskategorien(
        action="create",
        name="Senioren",
        jahresbeitrag=180.0,
        beschreibung="Seniorentarif",
    )
    assert result["name"] == "Senioren"
    assert result["jahresbeitrag"] == 180.0
    assert result["message"] == "Beitragskategorie erfolgreich erstellt."


@pytest.mark.asyncio
async def test_beitragskategorien_create_missing_fields(mcp_session_factory):
    result = await vereins_setup_beitragskategorien(action="create", name="X")
    assert "error" in result


@pytest.mark.asyncio
async def test_beitragskategorien_update(mcp_session_factory):
    created = await vereins_setup_beitragskategorien(
        action="create",
        name="Studenten",
        jahresbeitrag=100.0,
    )
    result = await vereins_setup_beitragskategorien(
        action="update",
        category_id=created["id"],
        jahresbeitrag=120.0,
    )
    assert result["jahresbeitrag"] == 120.0
    assert result["message"] == "Beitragskategorie erfolgreich aktualisiert."


@pytest.mark.asyncio
async def test_beitragskategorien_delete(mcp_session_factory):
    created = await vereins_setup_beitragskategorien(
        action="create",
        name="Probe",
        jahresbeitrag=50.0,
    )
    result = await vereins_setup_beitragskategorien(
        action="delete",
        category_id=created["id"],
    )
    assert "message" in result

    listed = await vereins_setup_beitragskategorien(action="list")
    assert len(listed["items"]) == 0
