"""Comprehensive tests for MCP member tools (batch 2)."""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from sportverein.models.base import Base

# Register all models
import sportverein.models  # noqa: F401

from sportverein.mcp.session import set_session_factory
from sportverein.mcp.tools_mitglieder import (
    datenschutz_auskunft,
    datenschutz_einwilligung_setzen,
    mitglied_abteilung_entfernen,
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
    factory = async_sessionmaker(mcp_engine, class_=AsyncSession, expire_on_commit=False)
    set_session_factory(factory)
    yield factory
    set_session_factory(None)


@pytest_asyncio.fixture()
async def mcp_session(mcp_session_factory):
    async with mcp_session_factory() as session:
        yield session


@pytest_asyncio.fixture()
async def sample_abteilung(mcp_session: AsyncSession):
    dept = Abteilung(name="Fußball", beschreibung="Fußballabteilung")
    mcp_session.add(dept)
    await mcp_session.commit()
    await mcp_session.refresh(dept)
    return dept


@pytest_asyncio.fixture()
async def sample_member(mcp_session_factory):
    """Create and return a sample member dict."""
    return await mitglied_anlegen(
        vorname="Max",
        nachname="Mustermann",
        email="max@example.de",
        geburtsdatum="1990-05-15",
        telefon="0171-1234567",
        strasse="Musterstr. 1",
        plz="12345",
        ort="Musterstadt",
    )


# -- mitglieder_suchen -------------------------------------------------------


@pytest.mark.asyncio
async def test_mitglieder_suchen_empty(mcp_session_factory):
    result = await mitglieder_suchen()
    assert result["items"] == []
    assert result["total"] == 0


@pytest.mark.asyncio
async def test_mitglieder_suchen_with_filters(mcp_session_factory):
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

    result_status = await mitglieder_suchen(status="aktiv")
    assert result_status["total"] == 2


# -- mitglied_details --------------------------------------------------------


@pytest.mark.asyncio
async def test_mitglied_details_found(mcp_session_factory, sample_member):
    result = await mitglied_details(member_id=sample_member["id"])
    assert result["vorname"] == "Max"
    assert result["nachname"] == "Mustermann"
    assert "abteilungen" in result


@pytest.mark.asyncio
async def test_mitglied_details_not_found(mcp_session_factory):
    result = await mitglied_details(member_id=9999)
    assert "error" in result


# -- mitglied_anlegen --------------------------------------------------------


@pytest.mark.asyncio
async def test_mitglied_anlegen_basic(mcp_session_factory):
    result = await mitglied_anlegen(
        vorname="Lisa",
        nachname="Weber",
        email="lisa@example.de",
        geburtsdatum="1988-11-30",
    )
    assert result["vorname"] == "Lisa"
    assert result["mitgliedsnummer"] == "M-0001"
    assert result["status"] == "aktiv"
    assert result["beitragskategorie"] == "erwachsene"
    assert result["id"] is not None


# -- mitglied_aktualisieren --------------------------------------------------


@pytest.mark.asyncio
async def test_mitglied_aktualisieren_fields(mcp_session_factory, sample_member):
    result = await mitglied_aktualisieren(
        member_id=sample_member["id"],
        nachname="Groß",
        telefon="0172-9876543",
    )
    assert result["nachname"] == "Groß"
    assert result["telefon"] == "0172-9876543"
    assert result["vorname"] == "Max"


# -- mitglied_kuendigen ------------------------------------------------------


@pytest.mark.asyncio
async def test_mitglied_kuendigen_sets_status(mcp_session_factory, sample_member):
    result = await mitglied_kuendigen(
        member_id=sample_member["id"],
        austrittsdatum="2025-12-31",
    )
    assert result["status"] == "gekuendigt"
    assert result["austrittsdatum"] == "2025-12-31"


# -- mitglied_abteilung_zuordnen ---------------------------------------------


@pytest.mark.asyncio
async def test_mitglied_abteilung_zuordnen(mcp_session_factory, sample_abteilung, sample_member):
    result = await mitglied_abteilung_zuordnen(
        member_id=sample_member["id"],
        abteilung_id=sample_abteilung.id,
    )
    assert result["mitglied_id"] == sample_member["id"]
    assert result["abteilung_id"] == sample_abteilung.id
    assert result["message"] == "Abteilung erfolgreich zugeordnet."


# -- mitglied_abteilung_entfernen (new) --------------------------------------


@pytest.mark.asyncio
async def test_mitglied_abteilung_entfernen(mcp_session_factory, sample_abteilung, sample_member):
    # Assign first
    await mitglied_abteilung_zuordnen(
        member_id=sample_member["id"],
        abteilung_id=sample_abteilung.id,
    )
    # Verify assignment
    details = await mitglied_details(member_id=sample_member["id"])
    assert len(details["abteilungen"]) == 1

    # Remove
    result = await mitglied_abteilung_entfernen(
        member_id=sample_member["id"],
        abteilung_id=sample_abteilung.id,
    )
    assert result["message"] == "Abteilung erfolgreich entfernt."
    assert result["mitglied_id"] == sample_member["id"]

    # Verify removal
    details_after = await mitglied_details(member_id=sample_member["id"])
    assert len(details_after["abteilungen"]) == 0


@pytest.mark.asyncio
async def test_mitglied_abteilung_entfernen_not_found(mcp_session_factory, sample_member):
    result = await mitglied_abteilung_entfernen(
        member_id=sample_member["id"],
        abteilung_id=9999,
    )
    assert "error" in result


# -- datenschutz_auskunft ----------------------------------------------------


@pytest.mark.asyncio
async def test_datenschutz_auskunft(mcp_session_factory, sample_member):
    result = await datenschutz_auskunft(member_id=sample_member["id"])
    assert "personal_data" in result
    assert result["personal_data"]["vorname"] == "Max"
    assert "departments" in result
    assert "invoices" in result
    assert "payments" in result
    assert "sepa_mandates" in result
    assert "audit_log" in result


@pytest.mark.asyncio
async def test_datenschutz_auskunft_not_found(mcp_session_factory):
    result = await datenschutz_auskunft(member_id=9999)
    assert "error" in result


# -- datenschutz_einwilligung_setzen (new) -----------------------------------


@pytest.mark.asyncio
async def test_datenschutz_einwilligung_setzen_grant(mcp_session_factory, sample_member):
    result = await datenschutz_einwilligung_setzen(
        member_id=sample_member["id"],
        einwilligung=True,
    )
    assert result["dsgvo_einwilligung"] is True
    assert result["einwilligung_datum"] is not None
    assert result["message"] == "Einwilligung erfolgreich aktualisiert."


@pytest.mark.asyncio
async def test_datenschutz_einwilligung_setzen_revoke(mcp_session_factory, sample_member):
    # Grant first
    await datenschutz_einwilligung_setzen(
        member_id=sample_member["id"],
        einwilligung=True,
    )
    # Revoke
    result = await datenschutz_einwilligung_setzen(
        member_id=sample_member["id"],
        einwilligung=False,
    )
    assert result["dsgvo_einwilligung"] is False
    assert result["einwilligung_datum"] is None


@pytest.mark.asyncio
async def test_datenschutz_einwilligung_setzen_not_found(mcp_session_factory):
    result = await datenschutz_einwilligung_setzen(member_id=9999, einwilligung=True)
    assert "error" in result
