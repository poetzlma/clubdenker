"""Tests for MCP finance/beitraege tools."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from sportverein.models.base import Base

# Register all models
import sportverein.models  # noqa: F401

from sportverein.mcp.session import set_session_factory
from sportverein.mcp.tools_beitraege import (
    beitraege_berechnen,
    buchung_anlegen,
    finanzbericht_erstellen,
    rechnung_erstellen,
    zahlung_verbuchen,
)
from sportverein.models.mitglied import BeitragKategorie, Mitglied, MitgliedStatus


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
async def sample_member(mcp_session: AsyncSession):
    """Create a sample member for testing."""
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
    await mcp_session.commit()
    await mcp_session.refresh(member)
    return member


@pytest.mark.asyncio
async def test_beitraege_berechnen(mcp_session_factory, sample_member):
    """Calculate fees for a single member."""
    result = await beitraege_berechnen(
        billing_year=2025,
        member_id=sample_member.id,
    )
    assert "fees" in result
    assert len(result["fees"]) == 1
    fee = result["fees"][0]
    assert fee["member_id"] == sample_member.id
    assert fee["jahresbeitrag"] == 240.0
    assert fee["prorata_betrag"] > 0


@pytest.mark.asyncio
async def test_buchung_anlegen(mcp_session_factory, sample_member):
    """Create a booking via MCP tool."""
    result = await buchung_anlegen(
        buchungsdatum="2025-01-15",
        betrag=100.0,
        beschreibung="Testbuchung",
        konto="1200",
        gegenkonto="4000",
        sphare="ideell",
        mitglied_id=sample_member.id,
    )
    assert result["id"] is not None
    assert result["betrag"] == 100.0
    assert result["sphare"] == "ideell"
    assert result["beschreibung"] == "Testbuchung"


@pytest.mark.asyncio
async def test_rechnung_erstellen(mcp_session_factory, sample_member):
    """Create an invoice via MCP tool."""
    result = await rechnung_erstellen(
        mitglied_id=sample_member.id,
        betrag=240.0,
        beschreibung="Jahresbeitrag 2025",
        faelligkeitsdatum="2025-03-31",
    )
    assert result["id"] is not None
    assert result["rechnungsnummer"] == "R-0001"
    assert result["betrag"] == 240.0
    assert result["status"] == "offen"
    assert result["mitglied_id"] == sample_member.id


@pytest.mark.asyncio
async def test_zahlung_verbuchen(mcp_session_factory, sample_member):
    """Record a payment via MCP tool."""
    # First create an invoice
    invoice = await rechnung_erstellen(
        mitglied_id=sample_member.id,
        betrag=240.0,
        beschreibung="Jahresbeitrag 2025",
        faelligkeitsdatum="2025-03-31",
    )
    rechnung_id = invoice["id"]

    result = await zahlung_verbuchen(
        rechnung_id=rechnung_id,
        betrag=240.0,
        zahlungsart="ueberweisung",
        referenz="TX-001",
    )
    assert result["id"] is not None
    assert result["betrag"] == 240.0
    assert result["zahlungsart"] == "ueberweisung"
    assert result["referenz"] == "TX-001"


@pytest.mark.asyncio
async def test_finanzbericht_erstellen(mcp_session_factory, sample_member):
    """Generate financial report via MCP tool."""
    # Create some bookings first
    await buchung_anlegen(
        buchungsdatum="2025-01-15",
        betrag=100.0,
        beschreibung="Einnahme",
        konto="1200",
        gegenkonto="4000",
        sphare="ideell",
    )
    await buchung_anlegen(
        buchungsdatum="2025-02-15",
        betrag=200.0,
        beschreibung="Einnahme 2",
        konto="1200",
        gegenkonto="4000",
        sphare="zweckbetrieb",
    )

    result = await finanzbericht_erstellen()
    assert "by_sphere" in result
    assert "total" in result
    assert result["total"] == 300.0
    assert result["by_sphere"]["ideell"] == 100.0
    assert result["by_sphere"]["zweckbetrieb"] == 200.0
