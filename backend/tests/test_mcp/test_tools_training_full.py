"""Comprehensive tests for MCP training and attendance tools (batch 2)."""

from __future__ import annotations

from datetime import date

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from sportverein.models.base import Base

# Register all models
import sportverein.models  # noqa: F401

from sportverein.mcp.session import set_session_factory
from sportverein.mcp.tools_training import (
    anwesenheit_abrufen,
    anwesenheit_erfassen,
    anwesenheit_mitglied_statistik,
    anwesenheit_statistik,
    training_verwalten,
)
from sportverein.models.mitglied import Abteilung, BeitragKategorie, Mitglied, MitgliedStatus


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
    dept = Abteilung(name="Tennis", beschreibung="Tennisabteilung")
    mcp_session.add(dept)
    await mcp_session.commit()
    await mcp_session.refresh(dept)
    return dept


@pytest_asyncio.fixture()
async def sample_member(mcp_session: AsyncSession):
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


@pytest_asyncio.fixture()
async def sample_gruppe(mcp_session_factory, sample_abteilung):
    result = await training_verwalten(
        action="create",
        name="Anfänger",
        abteilung_id=sample_abteilung.id,
        wochentag="montag",
        uhrzeit="18:00",
        trainer="T. Trainer",
        dauer_minuten=90,
        ort="Halle 1",
    )
    return result


# -- training_verwalten (list/create/update/delete) --------------------------


@pytest.mark.asyncio
async def test_training_verwalten_list_empty(mcp_session_factory):
    result = await training_verwalten(action="list")
    assert result["items"] == []


@pytest.mark.asyncio
async def test_training_verwalten_create(mcp_session_factory, sample_abteilung):
    result = await training_verwalten(
        action="create",
        name="Fortgeschrittene",
        abteilung_id=sample_abteilung.id,
        wochentag="mittwoch",
        uhrzeit="19:00",
        trainer="M. Mueller",
    )
    assert result["name"] == "Fortgeschrittene"
    assert result["wochentag"] == "mittwoch"
    assert result["uhrzeit"] == "19:00"
    assert result["id"] is not None


@pytest.mark.asyncio
async def test_training_verwalten_update(mcp_session_factory, sample_gruppe):
    result = await training_verwalten(
        action="update",
        gruppe_id=sample_gruppe["id"],
        trainer="N. Neu",
    )
    assert result["trainer"] == "N. Neu"
    assert result["name"] == "Anfänger"


@pytest.mark.asyncio
async def test_training_verwalten_delete(mcp_session_factory, sample_gruppe):
    result = await training_verwalten(
        action="delete",
        gruppe_id=sample_gruppe["id"],
    )
    assert "message" in result

    # Verify gone
    listed = await training_verwalten(action="list", aktiv=None)
    assert len(listed["items"]) == 0


@pytest.mark.asyncio
async def test_training_verwalten_create_missing_fields(mcp_session_factory):
    result = await training_verwalten(action="create", name="X")
    assert "error" in result


# -- anwesenheit_erfassen ----------------------------------------------------


@pytest.mark.asyncio
async def test_anwesenheit_erfassen(mcp_session_factory, sample_gruppe, sample_member):
    result = await anwesenheit_erfassen(
        trainingsgruppe_id=sample_gruppe["id"],
        datum="2025-03-10",
        teilnehmer=[
            {"mitglied_id": sample_member.id, "anwesend": True, "notiz": "Gut"},
        ],
    )
    assert "items" in result
    assert len(result["items"]) == 1
    assert result["items"][0]["anwesend"] is True
    assert result["items"][0]["mitglied_id"] == sample_member.id


# -- anwesenheit_statistik ---------------------------------------------------


@pytest.mark.asyncio
async def test_anwesenheit_statistik(
    mcp_session_factory, sample_abteilung, sample_gruppe, sample_member
):
    # Record some attendance
    await anwesenheit_erfassen(
        trainingsgruppe_id=sample_gruppe["id"],
        datum="2025-03-03",
        teilnehmer=[{"mitglied_id": sample_member.id, "anwesend": True}],
    )

    result = await anwesenheit_statistik(abteilung_id=sample_abteilung.id, wochen=12)
    assert "heatmap" in result
    assert "total_sessions" in result
    assert "avg_attendance_pct" in result


# -- anwesenheit_abrufen (new) -----------------------------------------------


@pytest.mark.asyncio
async def test_anwesenheit_abrufen_all(mcp_session_factory, sample_gruppe, sample_member):
    await anwesenheit_erfassen(
        trainingsgruppe_id=sample_gruppe["id"],
        datum="2025-03-10",
        teilnehmer=[{"mitglied_id": sample_member.id, "anwesend": True}],
    )

    result = await anwesenheit_abrufen()
    assert "items" in result
    assert len(result["items"]) >= 1


@pytest.mark.asyncio
async def test_anwesenheit_abrufen_filtered(mcp_session_factory, sample_gruppe, sample_member):
    await anwesenheit_erfassen(
        trainingsgruppe_id=sample_gruppe["id"],
        datum="2025-03-10",
        teilnehmer=[{"mitglied_id": sample_member.id, "anwesend": True}],
    )

    # Filter by member
    result = await anwesenheit_abrufen(mitglied_id=sample_member.id)
    assert len(result["items"]) == 1

    # Filter by gruppe
    result2 = await anwesenheit_abrufen(trainingsgruppe_id=sample_gruppe["id"])
    assert len(result2["items"]) == 1

    # Filter by date range
    result3 = await anwesenheit_abrufen(datum_von="2025-03-01", datum_bis="2025-03-31")
    assert len(result3["items"]) == 1

    # Filter with no match
    result4 = await anwesenheit_abrufen(datum_von="2024-01-01", datum_bis="2024-01-31")
    assert len(result4["items"]) == 0


# -- anwesenheit_mitglied_statistik (new) ------------------------------------


@pytest.mark.asyncio
async def test_anwesenheit_mitglied_statistik(mcp_session_factory, sample_gruppe, sample_member):
    await anwesenheit_erfassen(
        trainingsgruppe_id=sample_gruppe["id"],
        datum="2025-03-10",
        teilnehmer=[
            {"mitglied_id": sample_member.id, "anwesend": True},
        ],
    )
    await anwesenheit_erfassen(
        trainingsgruppe_id=sample_gruppe["id"],
        datum="2025-03-03",
        teilnehmer=[
            {"mitglied_id": sample_member.id, "anwesend": False},
        ],
    )

    result = await anwesenheit_mitglied_statistik(mitglied_id=sample_member.id)
    assert result["mitglied_id"] == sample_member.id
    assert "total_eintraege" in result
    assert "anwesend" in result
    assert "abwesend" in result
    assert "anwesenheit_pct" in result


@pytest.mark.asyncio
async def test_anwesenheit_mitglied_statistik_no_records(mcp_session_factory, sample_member):
    result = await anwesenheit_mitglied_statistik(mitglied_id=sample_member.id)
    assert result["total_eintraege"] == 0
    assert result["anwesenheit_pct"] == 0.0
