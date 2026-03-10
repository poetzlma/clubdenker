"""Tests for MCP member tools."""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from sportverein.models.base import Base

# Register all models
import sportverein.models  # noqa: F401

from sportverein.mcp.session import set_session_factory
from sportverein.mcp.tools_mitglieder import (
    mitglied_abteilung_zuordnen,
    mitglied_aktualisieren,
    mitglied_anlegen,
    mitglied_details,
    mitglied_kuendigen,
    mitglieder_suchen,
)
from sportverein.models.mitglied import Abteilung


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
async def sample_abteilung(mcp_session: AsyncSession):
    """Create a sample department for testing."""
    dept = Abteilung(name="Fußball", beschreibung="Fußballabteilung")
    mcp_session.add(dept)
    await mcp_session.commit()
    await mcp_session.refresh(dept)
    return dept


@pytest.mark.asyncio
async def test_mitglieder_suchen_empty(mcp_session_factory):
    """Search returns empty list when no members exist."""
    result = await mitglieder_suchen()
    assert result["items"] == []
    assert result["total"] == 0
    assert result["page"] == 1
    assert result["page_size"] == 20


@pytest.mark.asyncio
async def test_mitglied_anlegen(mcp_session_factory):
    """Create a new member via MCP tool."""
    result = await mitglied_anlegen(
        vorname="Max",
        nachname="Mustermann",
        email="max@example.de",
        geburtsdatum="1990-05-15",
        telefon="0171-1234567",
        strasse="Musterstr. 1",
        plz="12345",
        ort="Musterstadt",
    )
    assert result["vorname"] == "Max"
    assert result["nachname"] == "Mustermann"
    assert result["email"] == "max@example.de"
    assert result["mitgliedsnummer"] == "M-0001"
    assert result["status"] == "aktiv"
    assert result["beitragskategorie"] == "erwachsene"
    assert result["id"] is not None


@pytest.mark.asyncio
async def test_mitglieder_suchen_with_name(mcp_session_factory):
    """Search by name filter."""
    await mitglied_anlegen(
        vorname="Anna",
        nachname="Schmidt",
        email="anna@example.de",
        geburtsdatum="1985-03-20",
    )
    await mitglied_anlegen(
        vorname="Peter",
        nachname="Müller",
        email="peter@example.de",
        geburtsdatum="1992-07-10",
    )

    result = await mitglieder_suchen(name="Schmidt")
    assert result["total"] == 1
    assert result["items"][0]["nachname"] == "Schmidt"

    result_all = await mitglieder_suchen()
    assert result_all["total"] == 2


@pytest.mark.asyncio
async def test_mitglied_details(mcp_session_factory):
    """Get member details by ID."""
    created = await mitglied_anlegen(
        vorname="Lisa",
        nachname="Weber",
        email="lisa@example.de",
        geburtsdatum="1988-11-30",
    )
    member_id = created["id"]

    result = await mitglied_details(member_id=member_id)
    assert result["vorname"] == "Lisa"
    assert result["nachname"] == "Weber"
    assert "abteilungen" in result


@pytest.mark.asyncio
async def test_mitglied_details_not_found(mcp_session_factory):
    """Getting a non-existent member returns an error dict."""
    result = await mitglied_details(member_id=9999)
    assert "error" in result


@pytest.mark.asyncio
async def test_mitglied_aktualisieren(mcp_session_factory):
    """Update member fields."""
    created = await mitglied_anlegen(
        vorname="Jan",
        nachname="Klein",
        email="jan@example.de",
        geburtsdatum="1995-01-01",
    )
    member_id = created["id"]

    result = await mitglied_aktualisieren(
        member_id=member_id,
        nachname="Groß",
        telefon="0172-9876543",
    )
    assert result["nachname"] == "Groß"
    assert result["telefon"] == "0172-9876543"
    # Unchanged fields should remain
    assert result["vorname"] == "Jan"


@pytest.mark.asyncio
async def test_mitglied_kuendigen(mcp_session_factory):
    """Cancel a membership."""
    created = await mitglied_anlegen(
        vorname="Maria",
        nachname="Braun",
        email="maria@example.de",
        geburtsdatum="1970-06-15",
    )
    member_id = created["id"]

    result = await mitglied_kuendigen(
        member_id=member_id,
        austrittsdatum="2025-12-31",
    )
    assert result["status"] == "gekuendigt"
    assert result["austrittsdatum"] == "2025-12-31"


@pytest.mark.asyncio
async def test_mitglied_abteilung_zuordnen(mcp_session_factory, sample_abteilung):
    """Assign a member to a department."""
    created = await mitglied_anlegen(
        vorname="Tom",
        nachname="Bauer",
        email="tom@example.de",
        geburtsdatum="2000-02-28",
    )
    member_id = created["id"]

    result = await mitglied_abteilung_zuordnen(
        member_id=member_id,
        abteilung_id=sample_abteilung.id,
    )
    assert result["mitglied_id"] == member_id
    assert result["abteilung_id"] == sample_abteilung.id
    assert result["message"] == "Abteilung erfolgreich zugeordnet."

    # Verify it shows up in details
    details = await mitglied_details(member_id=member_id)
    assert len(details["abteilungen"]) == 1
    assert details["abteilungen"][0]["name"] == "Fußball"
