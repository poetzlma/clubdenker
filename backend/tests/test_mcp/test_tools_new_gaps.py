"""Tests for newly added MCP tools closing chat-first gaps:
- rechnungen_auflisten (invoice listing/filtering)
- sepa_mandate_verwalten (SEPA mandate CRUD)
- kostenstellen_verwalten (cost center CRUD)
- datenschutz_loeschfrist_planen (DSGVO deletion scheduling)
- datenschutz_ausstehende_loeschungen (pending deletions)
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from sportverein.models.base import Base

# Register all models
import sportverein.models  # noqa: F401

from sportverein.mcp.session import set_session_factory
from sportverein.mcp.tools_beitraege import (
    kostenstellen_verwalten,
    rechnung_erstellen,
    rechnungen_auflisten,
    sepa_mandate_verwalten,
)
from sportverein.mcp.tools_mitglieder import (
    datenschutz_ausstehende_loeschungen,
    datenschutz_loeschfrist_planen,
)
from sportverein.models.mitglied import BeitragKategorie, Mitglied, MitgliedStatus


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# rechnungen_auflisten
# ---------------------------------------------------------------------------


class TestRechnungenAuflisten:
    @pytest.mark.asyncio
    async def test_list_empty(self, mcp_session_factory):
        result = await rechnungen_auflisten()
        assert result["rechnungen"] == []
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_list_with_invoices(self, mcp_session_factory, sample_member):
        await rechnung_erstellen(
            mitglied_id=sample_member.id,
            betrag=100.0,
            beschreibung="Beitrag 1",
            faelligkeitsdatum="2025-06-30",
        )
        await rechnung_erstellen(
            mitglied_id=sample_member.id,
            betrag=200.0,
            beschreibung="Beitrag 2",
            faelligkeitsdatum="2025-06-30",
        )
        result = await rechnungen_auflisten()
        assert result["total"] == 2
        assert len(result["rechnungen"]) == 2

    @pytest.mark.asyncio
    async def test_filter_by_status(self, mcp_session_factory, sample_member):
        await rechnung_erstellen(
            mitglied_id=sample_member.id,
            betrag=100.0,
            beschreibung="Test",
            faelligkeitsdatum="2025-06-30",
        )
        result = await rechnungen_auflisten(status="entwurf")
        assert result["total"] >= 1
        for r in result["rechnungen"]:
            assert r["status"] == "entwurf"

    @pytest.mark.asyncio
    async def test_filter_by_member(self, mcp_session_factory, sample_member):
        await rechnung_erstellen(
            mitglied_id=sample_member.id,
            betrag=100.0,
            beschreibung="Test",
            faelligkeitsdatum="2025-06-30",
        )
        result = await rechnungen_auflisten(mitglied_id=sample_member.id)
        assert result["total"] >= 1
        for r in result["rechnungen"]:
            assert r["mitglied_id"] == sample_member.id

    @pytest.mark.asyncio
    async def test_pagination(self, mcp_session_factory, sample_member):
        for i in range(5):
            await rechnung_erstellen(
                mitglied_id=sample_member.id,
                betrag=float(100 + i),
                beschreibung=f"R-{i}",
                faelligkeitsdatum="2025-06-30",
            )
        result = await rechnungen_auflisten(page=1, page_size=2)
        assert result["total"] == 5
        assert len(result["rechnungen"]) == 2
        assert result["page"] == 1
        assert result["page_size"] == 2


# ---------------------------------------------------------------------------
# sepa_mandate_verwalten
# ---------------------------------------------------------------------------


class TestSepaMandateVerwalten:
    @pytest.mark.asyncio
    async def test_list_empty(self, mcp_session_factory):
        result = await sepa_mandate_verwalten(action="list")
        assert result["items"] == []
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_create(self, mcp_session_factory, sample_member):
        result = await sepa_mandate_verwalten(
            action="create",
            mitglied_id=sample_member.id,
            iban="DE89370400440532013000",
            kontoinhaber="Max Mustermann",
            mandatsreferenz="MAND-001",
        )
        assert "id" in result
        assert result["aktiv"] is True
        assert result["message"] == "SEPA-Mandat erfolgreich erstellt."

    @pytest.mark.asyncio
    async def test_create_missing_fields(self, mcp_session_factory):
        result = await sepa_mandate_verwalten(action="create", iban="DE123")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_update(self, mcp_session_factory, sample_member):
        created = await sepa_mandate_verwalten(
            action="create",
            mitglied_id=sample_member.id,
            iban="DE89370400440532013000",
            kontoinhaber="Max Mustermann",
            mandatsreferenz="MAND-002",
        )
        result = await sepa_mandate_verwalten(
            action="update",
            mandat_id=created["id"],
            bic="COBADEFFXXX",
        )
        assert result["message"] == "SEPA-Mandat erfolgreich aktualisiert."

    @pytest.mark.asyncio
    async def test_update_missing_id(self, mcp_session_factory):
        result = await sepa_mandate_verwalten(action="update", bic="COBADEFFXXX")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_deactivate(self, mcp_session_factory, sample_member):
        created = await sepa_mandate_verwalten(
            action="create",
            mitglied_id=sample_member.id,
            iban="DE89370400440532013000",
            kontoinhaber="Max Mustermann",
            mandatsreferenz="MAND-003",
        )
        result = await sepa_mandate_verwalten(
            action="deactivate",
            mandat_id=created["id"],
        )
        assert result["aktiv"] is False
        assert result["message"] == "SEPA-Mandat deaktiviert."

    @pytest.mark.asyncio
    async def test_deactivate_missing_id(self, mcp_session_factory):
        result = await sepa_mandate_verwalten(action="deactivate")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_list_filter_aktiv(self, mcp_session_factory, sample_member):
        await sepa_mandate_verwalten(
            action="create",
            mitglied_id=sample_member.id,
            iban="DE89370400440532013000",
            kontoinhaber="Max Mustermann",
            mandatsreferenz="MAND-004",
        )
        result = await sepa_mandate_verwalten(action="list", aktiv=True)
        assert result["total"] >= 1

    @pytest.mark.asyncio
    async def test_unknown_action(self, mcp_session_factory):
        result = await sepa_mandate_verwalten(action="nope")
        assert "error" in result


# ---------------------------------------------------------------------------
# kostenstellen_verwalten
# ---------------------------------------------------------------------------


class TestKostenstellenVerwalten:
    @pytest.mark.asyncio
    async def test_list_empty(self, mcp_session_factory):
        result = await kostenstellen_verwalten(action="list")
        assert result["items"] == []

    @pytest.mark.asyncio
    async def test_create(self, mcp_session_factory):
        result = await kostenstellen_verwalten(
            action="create",
            name="Fussball",
            beschreibung="Fussball-Abteilung",
            budget=5000.0,
            freigabelimit=500.0,
        )
        assert "id" in result
        assert result["name"] == "Fussball"
        assert result["budget"] == 5000.0
        assert result["message"] == "Kostenstelle erfolgreich erstellt."

    @pytest.mark.asyncio
    async def test_create_missing_name(self, mcp_session_factory):
        result = await kostenstellen_verwalten(action="create")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_update(self, mcp_session_factory):
        created = await kostenstellen_verwalten(action="create", name="Tennis", budget=3000.0)
        result = await kostenstellen_verwalten(
            action="update",
            kostenstelle_id=created["id"],
            budget=4000.0,
        )
        assert result["budget"] == 4000.0
        assert result["message"] == "Kostenstelle erfolgreich aktualisiert."

    @pytest.mark.asyncio
    async def test_update_missing_id(self, mcp_session_factory):
        result = await kostenstellen_verwalten(action="update", name="X")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_delete(self, mcp_session_factory):
        created = await kostenstellen_verwalten(action="create", name="Temporaer")
        result = await kostenstellen_verwalten(action="delete", kostenstelle_id=created["id"])
        assert "message" in result

        # Verify it's gone
        listed = await kostenstellen_verwalten(action="list")
        ids = [ks["id"] for ks in listed["items"]]
        assert created["id"] not in ids

    @pytest.mark.asyncio
    async def test_delete_missing_id(self, mcp_session_factory):
        result = await kostenstellen_verwalten(action="delete")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, mcp_session_factory):
        result = await kostenstellen_verwalten(action="delete", kostenstelle_id=9999)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_unknown_action(self, mcp_session_factory):
        result = await kostenstellen_verwalten(action="nope")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_list_after_create(self, mcp_session_factory):
        await kostenstellen_verwalten(action="create", name="KS-A", budget=1000.0)
        await kostenstellen_verwalten(action="create", name="KS-B", budget=2000.0)
        result = await kostenstellen_verwalten(action="list")
        assert len(result["items"]) == 2


# ---------------------------------------------------------------------------
# datenschutz_loeschfrist_planen
# ---------------------------------------------------------------------------


class TestDatenschutzLoeschfrist:
    @pytest.mark.asyncio
    async def test_schedule_deletion(self, mcp_session_factory, sample_member):
        result = await datenschutz_loeschfrist_planen(
            member_id=sample_member.id,
            retention_days=365,
        )
        assert result["mitglied_id"] == sample_member.id
        assert result["loesch_datum"] is not None
        expected = (date.today() + timedelta(days=365)).isoformat()
        assert result["loesch_datum"] == expected

    @pytest.mark.asyncio
    async def test_schedule_deletion_default_retention(self, mcp_session_factory, sample_member):
        result = await datenschutz_loeschfrist_planen(
            member_id=sample_member.id,
        )
        assert result["mitglied_id"] == sample_member.id
        assert result["loesch_datum"] is not None

    @pytest.mark.asyncio
    async def test_schedule_deletion_invalid_member(self, mcp_session_factory):
        result = await datenschutz_loeschfrist_planen(member_id=9999)
        assert "error" in result


# ---------------------------------------------------------------------------
# datenschutz_ausstehende_loeschungen
# ---------------------------------------------------------------------------


class TestDatenschutzAusstehend:
    @pytest.mark.asyncio
    async def test_no_pending(self, mcp_session_factory):
        result = await datenschutz_ausstehende_loeschungen()
        assert result["ausstehend"] == []
        assert result["count"] == 0

    @pytest.mark.asyncio
    async def test_with_pending(self, mcp_session_factory, sample_member, mcp_session):
        # Set loesch_datum in the past
        sample_member.loesch_datum = date.today() - timedelta(days=1)
        mcp_session.add(sample_member)
        await mcp_session.commit()

        result = await datenschutz_ausstehende_loeschungen()
        assert result["count"] == 1
        assert result["ausstehend"][0]["mitglied_id"] == sample_member.id
        assert result["ausstehend"][0]["name"] == "Max Mustermann"
