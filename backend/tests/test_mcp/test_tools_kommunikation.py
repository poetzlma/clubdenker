"""Tests for MCP communication tools (Kommunikation)."""

from __future__ import annotations

from unittest.mock import patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from sportverein.models.base import Base

# Register all models
import sportverein.models  # noqa: F401

from sportverein.mcp.tools_kommunikation import (
    dokument_generieren,
    nachricht_senden,
    newsletter_erstellen,
    protokoll_anlegen,
)


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
    yield factory


@pytest_asyncio.fixture()
async def mcp_session(mcp_session_factory):
    async with mcp_session_factory() as session:
        yield session


# ===================================================================
# nachricht_senden
# ===================================================================


class TestNachrichtSenden:
    """Tests for the nachricht_senden MCP tool."""

    @pytest.mark.asyncio
    async def test_send_to_single_recipient(self):
        result = await nachricht_senden(
            empfaenger_ids=[1],
            betreff="Testbetreff",
            inhalt="Testinhalt",
        )
        assert result["status"] == "success"
        assert result["empfaenger_count"] == 1
        assert "Testbetreff" in result["message"]

    @pytest.mark.asyncio
    async def test_send_to_multiple_recipients(self):
        result = await nachricht_senden(
            empfaenger_ids=[1, 2, 3, 4, 5],
            betreff="Rundschreiben",
            inhalt="Inhalt an alle",
        )
        assert result["status"] == "success"
        assert result["empfaenger_count"] == 5
        assert "5 Empf" in result["message"]

    @pytest.mark.asyncio
    async def test_send_with_empty_recipients(self):
        result = await nachricht_senden(
            empfaenger_ids=[],
            betreff="Leerer Verteiler",
            inhalt="Niemand bekommt das.",
        )
        assert result["status"] == "success"
        assert result["empfaenger_count"] == 0

    @pytest.mark.asyncio
    async def test_send_with_custom_typ(self):
        result = await nachricht_senden(
            empfaenger_ids=[42],
            betreff="Brief",
            inhalt="Briefinhalt",
            typ="brief",
        )
        assert result["status"] == "success"
        assert result["empfaenger_count"] == 1

    @pytest.mark.asyncio
    async def test_default_typ_is_email(self):
        """Verify the default typ parameter."""
        result = await nachricht_senden(
            empfaenger_ids=[1],
            betreff="Default type",
            inhalt="Inhalt",
        )
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_long_subject_and_content(self):
        long_betreff = "B" * 500
        long_inhalt = "I" * 10000
        result = await nachricht_senden(
            empfaenger_ids=[1],
            betreff=long_betreff,
            inhalt=long_inhalt,
        )
        assert result["status"] == "success"
        assert long_betreff in result["message"]

    @pytest.mark.asyncio
    async def test_special_characters_in_subject(self):
        result = await nachricht_senden(
            empfaenger_ids=[1],
            betreff="Umlaute: ae oe ue ss Sonderzeichen: @#$%",
            inhalt="Inhalt mit Sonderzeichen",
        )
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_large_recipient_list(self):
        ids = list(range(1, 1001))
        result = await nachricht_senden(
            empfaenger_ids=ids,
            betreff="Massenversand",
            inhalt="An alle 1000 Mitglieder",
        )
        assert result["empfaenger_count"] == 1000


# ===================================================================
# newsletter_erstellen
# ===================================================================


class TestNewsletterErstellen:
    """Tests for the newsletter_erstellen MCP tool."""

    @pytest.mark.asyncio
    async def test_create_without_sending(self):
        result = await newsletter_erstellen(
            betreff="Vereinsnachrichten Q1",
            inhalt="Neuigkeiten aus dem Verein",
        )
        assert result["status"] == "success"
        assert result["versandt"] is False
        assert "Versand" not in result["message"]

    @pytest.mark.asyncio
    async def test_create_with_sending(self):
        result = await newsletter_erstellen(
            betreff="Dringender Newsletter",
            inhalt="Wichtige Mitteilung",
            versenden=True,
        )
        assert result["status"] == "success"
        assert result["versandt"] is True
        assert "Versand gestartet" in result["message"]

    @pytest.mark.asyncio
    async def test_default_versenden_is_false(self):
        result = await newsletter_erstellen(
            betreff="Test",
            inhalt="Inhalt",
        )
        assert result["versandt"] is False

    @pytest.mark.asyncio
    async def test_empty_content(self):
        result = await newsletter_erstellen(
            betreff="Leerer Newsletter",
            inhalt="",
        )
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_subject_in_message(self):
        result = await newsletter_erstellen(
            betreff="Spezial-Ausgabe 2026",
            inhalt="Inhalt der Spezial-Ausgabe",
        )
        assert "Spezial-Ausgabe 2026" in result["message"]

    @pytest.mark.asyncio
    async def test_html_content(self):
        result = await newsletter_erstellen(
            betreff="HTML Newsletter",
            inhalt="<h1>Titel</h1><p>Absatz mit <b>fett</b></p>",
        )
        assert result["status"] == "success"


# ===================================================================
# dokument_generieren
# ===================================================================


class TestDokumentGenerieren:
    """Tests for the dokument_generieren MCP tool."""

    @pytest.mark.asyncio
    async def test_generate_bescheinigung(self):
        result = await dokument_generieren(
            typ="bescheinigung",
            mitglied_id=1,
        )
        assert result["status"] == "success"
        assert result["typ"] == "bescheinigung"
        assert result["mitglied_id"] == 1

    @pytest.mark.asyncio
    async def test_generate_without_mitglied(self):
        result = await dokument_generieren(
            typ="brief",
        )
        assert result["status"] == "success"
        assert result["typ"] == "brief"
        assert result["mitglied_id"] is None

    @pytest.mark.asyncio
    async def test_generate_with_daten(self):
        result = await dokument_generieren(
            typ="spendenbescheinigung",
            mitglied_id=42,
            daten={"betrag": 500.0, "jahr": 2025},
        )
        assert result["status"] == "success"
        assert result["typ"] == "spendenbescheinigung"
        assert result["mitglied_id"] == 42

    @pytest.mark.asyncio
    async def test_generate_with_empty_daten(self):
        result = await dokument_generieren(
            typ="satzung",
            daten={},
        )
        assert result["status"] == "success"
        assert result["typ"] == "satzung"

    @pytest.mark.asyncio
    async def test_generate_various_types(self):
        for typ in ["bescheinigung", "brief", "vertrag", "kuendigung", "mahnung"]:
            result = await dokument_generieren(typ=typ)
            assert result["status"] == "success"
            assert result["typ"] == typ

    @pytest.mark.asyncio
    async def test_typ_in_message(self):
        result = await dokument_generieren(typ="mitgliedsausweis")
        assert "mitgliedsausweis" in result["message"]

    @pytest.mark.asyncio
    async def test_generate_with_none_daten(self):
        result = await dokument_generieren(typ="brief", daten=None)
        assert result["status"] == "success"


# ===================================================================
# protokoll_anlegen
# ===================================================================


class TestProtokollAnlegen:
    """Tests for the protokoll_anlegen MCP tool.

    The tool does a lazy import of async_session from sportverein.db.session,
    so we mock the session to use our in-memory DB.
    """

    @pytest.mark.asyncio
    async def test_create_basic_protokoll(self, mcp_session_factory, mcp_session):
        """Create a basic protocol entry."""
        # The tool does a lazy import of async_session from db.session.
        # That name doesn't exist in the module, so we patch with create=True.
        with patch(
            "sportverein.db.session.async_session_factory",
            mcp_session_factory,
        ):
            result = await protokoll_anlegen(
                titel="Vorstandssitzung Q1/2026",
                inhalt="Tagesordnung besprochen.",
                datum="2026-03-01",
                typ="vorstandssitzung",
            )
        assert result["status"] == "success"
        assert result["id"] is not None
        assert result["titel"] == "Vorstandssitzung Q1/2026"
        assert result["datum"] == "2026-03-01"
        assert result["typ"] == "vorstandssitzung"

    @pytest.mark.asyncio
    async def test_create_protokoll_with_all_fields(self, mcp_session_factory):
        with patch(
            "sportverein.db.session.async_session_factory",
            mcp_session_factory,
        ):
            result = await protokoll_anlegen(
                titel="Jahreshauptversammlung 2026",
                inhalt="Jahresbericht, Entlastung, Wahlen.",
                datum="2026-01-15",
                typ="mitgliederversammlung",
                erstellt_von="Max Mustermann",
                teilnehmer="Max, Erika, Hans, Petra",
                beschluesse="Vorstand entlastet. Neuwahl: Max als 1. Vorsitzender.",
            )
        assert result["status"] == "success"
        assert result["typ"] == "mitgliederversammlung"

    @pytest.mark.asyncio
    async def test_create_protokoll_default_typ(self, mcp_session_factory):
        """Default typ should be 'sonstige'."""
        with patch(
            "sportverein.db.session.async_session_factory",
            mcp_session_factory,
        ):
            result = await protokoll_anlegen(
                titel="Besprechung",
                inhalt="Allgemeine Besprechung.",
                datum="2026-02-01",
            )
        assert result["typ"] == "sonstige"

    @pytest.mark.asyncio
    async def test_create_protokoll_default_datum(self, mcp_session_factory):
        """When datum is None, today's date should be used."""
        with patch(
            "sportverein.db.session.async_session_factory",
            mcp_session_factory,
        ):
            result = await protokoll_anlegen(
                titel="Spontanes Treffen",
                inhalt="Ohne festes Datum.",
            )
        assert result["status"] == "success"
        assert result["datum"] is not None

    @pytest.mark.asyncio
    async def test_create_protokoll_abteilungssitzung(self, mcp_session_factory):
        with patch(
            "sportverein.db.session.async_session_factory",
            mcp_session_factory,
        ):
            result = await protokoll_anlegen(
                titel="Fussball-Abteilung Sitzung",
                inhalt="Trainingsplan besprochen.",
                datum="2026-03-10",
                typ="abteilungssitzung",
            )
        assert result["typ"] == "abteilungssitzung"

    @pytest.mark.asyncio
    async def test_create_protokoll_invalid_typ(self, mcp_session_factory):
        """Invalid typ should raise an error."""
        with patch(
            "sportverein.db.session.async_session_factory",
            mcp_session_factory,
        ):
            with pytest.raises(ValueError):
                await protokoll_anlegen(
                    titel="Fehlerhaft",
                    inhalt="Ungueltig.",
                    datum="2026-01-01",
                    typ="ungueltig",
                )

    @pytest.mark.asyncio
    async def test_create_multiple_protokolle(self, mcp_session_factory):
        """Create multiple protocols and verify each gets a unique ID."""
        ids = []
        with patch(
            "sportverein.db.session.async_session_factory",
            mcp_session_factory,
        ):
            for i in range(5):
                result = await protokoll_anlegen(
                    titel=f"Protokoll Nr. {i+1}",
                    inhalt=f"Inhalt {i+1}",
                    datum=f"2026-03-{i+1:02d}",
                )
                ids.append(result["id"])
        assert len(set(ids)) == 5  # All IDs unique
