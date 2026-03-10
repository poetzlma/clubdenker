"""Tests for MCP dashboard tools (batch 2)."""

from __future__ import annotations

from datetime import date

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from sportverein.models.base import Base

# Register all models
import sportverein.models  # noqa: F401

from sportverein.mcp.session import set_session_factory
from sportverein.mcp.tools_dashboard import (
    dashboard_schatzmeister,
    dashboard_spartenleiter,
    dashboard_vorstand,
)
from sportverein.models.mitglied import (
    Abteilung,
    BeitragKategorie,
    Mitglied,
    MitgliedAbteilung,
    MitgliedStatus,
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
async def seed_data(mcp_session: AsyncSession):
    """Create minimal seed data: department + member."""
    dept = Abteilung(name="Fußball", beschreibung="Fußballabteilung")
    mcp_session.add(dept)
    await mcp_session.flush()
    await mcp_session.refresh(dept)

    member = Mitglied(
        mitgliedsnummer="M-0001",
        vorname="Max",
        nachname="Mustermann",
        email="max@example.de",
        geburtsdatum=date(1990, 5, 15),
        eintrittsdatum=date(2024, 1, 1),
        status=MitgliedStatus.aktiv,
        beitragskategorie=BeitragKategorie.erwachsene,
    )
    mcp_session.add(member)
    await mcp_session.flush()
    await mcp_session.refresh(member)

    assoc = MitgliedAbteilung(mitglied_id=member.id, abteilung_id=dept.id)
    mcp_session.add(assoc)
    await mcp_session.commit()

    return {"department": dept, "member": member}


# -- dashboard_vorstand ------------------------------------------------------


@pytest.mark.asyncio
async def test_dashboard_vorstand_empty(mcp_session_factory):
    result = await dashboard_vorstand()
    assert "summary" in result
    assert "data" in result
    data = result["data"]
    assert "kpis" in data
    assert "member_trend" in data
    assert "cashflow" in data
    assert "open_actions" in data


@pytest.mark.asyncio
async def test_dashboard_vorstand_with_data(mcp_session_factory, seed_data):
    result = await dashboard_vorstand()
    data = result["data"]
    assert data["kpis"]["active_members"] >= 1


# -- dashboard_schatzmeister -------------------------------------------------


@pytest.mark.asyncio
async def test_dashboard_schatzmeister_empty(mcp_session_factory):
    result = await dashboard_schatzmeister()
    assert "summary" in result
    assert "data" in result
    data = result["data"]
    assert "sepa_hero" in data
    assert "kpis" in data
    assert "open_items" in data
    assert "budget_burn" in data


@pytest.mark.asyncio
async def test_dashboard_schatzmeister_with_data(mcp_session_factory, seed_data):
    result = await dashboard_schatzmeister()
    data = result["data"]
    assert data["sepa_hero"]["total_count"] >= 0
    assert "balance_ideell" in data["kpis"]


# -- dashboard_spartenleiter -------------------------------------------------


@pytest.mark.asyncio
async def test_dashboard_spartenleiter_not_found(mcp_session_factory):
    result = await dashboard_spartenleiter(abteilung="NichtExistent")
    assert "error" in result


@pytest.mark.asyncio
async def test_dashboard_spartenleiter_with_data(mcp_session_factory, seed_data):
    result = await dashboard_spartenleiter(abteilung="Fußball")
    assert "summary" in result
    assert "data" in result
    data = result["data"]
    assert "kpis" in data
    assert data["kpis"]["member_count"] >= 1
    assert "attendance_heatmap" in data
    assert "training_schedule" in data
    assert "risk_members" in data
    assert "budget_donut" in data
