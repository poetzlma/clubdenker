"""Tests for the chat endpoint (POST /api/chat)."""

from __future__ import annotations

from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from sportverein.models.mitglied import (
    BeitragKategorie,
    Mitglied,
    MitgliedStatus,
)

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _seed_member(
    session: AsyncSession,
    *,
    vorname: str = "Max",
    nachname: str = "Mustermann",
    email: str = "max@example.com",
    mitgliedsnummer: str = "M001",
    status: MitgliedStatus = MitgliedStatus.aktiv,
    beitragskategorie: BeitragKategorie = BeitragKategorie.erwachsene,
    eintrittsdatum: date | None = None,
) -> Mitglied:
    m = Mitglied(
        vorname=vorname,
        nachname=nachname,
        email=email,
        mitgliedsnummer=mitgliedsnummer,
        geburtsdatum=date(1990, 1, 1),
        eintrittsdatum=eintrittsdatum or date(2024, 1, 1),
        status=status,
        beitragskategorie=beitragskategorie,
    )
    session.add(m)
    await session.flush()
    return m


# ---------------------------------------------------------------------------
# Fallback / help
# ---------------------------------------------------------------------------


async def test_fallback_returns_help(client: AsyncClient):
    """Unknown query should return a help message listing available topics."""
    resp = await client.post("/api/chat", json={"message": "hallo wie gehts"})
    assert resp.status_code == 200
    data = resp.json()
    assert "helfen" in data["response"].lower() or "Mitgliederstatistik" in data["response"]
    assert data["tool_used"] is None
    assert data["data"] is None


async def test_empty_message_returns_fallback(client: AsyncClient):
    resp = await client.post("/api/chat", json={"message": ""})
    assert resp.status_code == 200
    data = resp.json()
    assert data["tool_used"] is None


# ---------------------------------------------------------------------------
# Mitglieder-Statistik
# ---------------------------------------------------------------------------


async def test_mitglieder_statistik(client: AsyncClient, session: AsyncSession):
    await _seed_member(
        session, vorname="Anna", nachname="Eins", email="anna@example.com", mitgliedsnummer="M010"
    )
    await _seed_member(
        session,
        vorname="Bernd",
        nachname="Zwei",
        email="bernd@example.com",
        mitgliedsnummer="M011",
        status=MitgliedStatus.passiv,
    )
    await session.flush()

    resp = await client.post(
        "/api/chat", json={"message": "Wie viele Mitglieder hat der Verein?"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["tool_used"] == "MitgliederService.get_member_stats"
    assert "1" in data["response"]  # 1 active
    assert data["data"] is not None


async def test_mitglieder_statistik_variant(client: AsyncClient, session: AsyncSession):
    """Alternative phrasing should also trigger member stats."""
    await _seed_member(session, mitgliedsnummer="M020")
    await session.flush()

    resp = await client.post("/api/chat", json={"message": "mitgliederzahl"})
    assert resp.status_code == 200
    assert resp.json()["tool_used"] == "MitgliederService.get_member_stats"


# ---------------------------------------------------------------------------
# Mitglied suchen
# ---------------------------------------------------------------------------


async def test_suche_mitglied(client: AsyncClient, session: AsyncSession):
    await _seed_member(
        session, vorname="Erika", nachname="Musterfrau", mitgliedsnummer="M030"
    )
    await session.flush()

    resp = await client.post(
        "/api/chat", json={"message": "Suche Mitglied Musterfrau"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["tool_used"] == "MitgliederService.search_members"
    assert "Musterfrau" in data["response"]
    assert data["data"]["total"] >= 1


async def test_suche_mitglied_no_name(client: AsyncClient):
    """Search without a name should prompt the user to supply one."""
    resp = await client.post("/api/chat", json={"message": "suche mitglied"})
    assert resp.status_code == 200
    data = resp.json()
    assert "Namen" in data["response"] or "Name" in data["response"].lower() or "name" in data["response"].lower()


async def test_suche_mitglied_not_found(client: AsyncClient):
    resp = await client.post(
        "/api/chat", json={"message": "suche mitglied Nichtvorhanden"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "nicht" in data["response"].lower() or "kein" in data["response"].lower()
    assert data["tool_used"] == "MitgliederService.search_members"


async def test_finde_mitglied_variant(client: AsyncClient, session: AsyncSession):
    """'Finde Mitglied' should also trigger search."""
    await _seed_member(
        session, vorname="Karl", nachname="Test", mitgliedsnummer="M031"
    )
    await session.flush()

    resp = await client.post("/api/chat", json={"message": "finde mitglied Test"})
    assert resp.status_code == 200
    assert resp.json()["tool_used"] == "MitgliederService.search_members"


# ---------------------------------------------------------------------------
# Kassenstand / Finanzen
# ---------------------------------------------------------------------------


async def test_kassenstand(client: AsyncClient):
    resp = await client.post("/api/chat", json={"message": "Wie ist der Kassenstand?"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["tool_used"] == "FinanzenService.get_balance_by_sphere"
    assert "Kassenstand" in data["response"]
    assert data["data"] is not None


async def test_finanzen_variant(client: AsyncClient):
    resp = await client.post("/api/chat", json={"message": "zeige mir die finanzen"})
    assert resp.status_code == 200
    assert resp.json()["tool_used"] == "FinanzenService.get_balance_by_sphere"


async def test_bilanz_variant(client: AsyncClient):
    resp = await client.post("/api/chat", json={"message": "bilanz bitte"})
    assert resp.status_code == 200
    assert resp.json()["tool_used"] == "FinanzenService.get_balance_by_sphere"


# ---------------------------------------------------------------------------
# Beitraege berechnen
# ---------------------------------------------------------------------------


async def test_beitraege_berechnen_no_members(client: AsyncClient):
    resp = await client.post(
        "/api/chat", json={"message": "Beiträge berechnen 2026"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["tool_used"] == "BeitraegeService.calculate_all_fees"
    # No members -> should say no active members found
    assert "keine" in data["response"].lower() or "Keine" in data["response"]


async def test_beitraege_berechnen_with_members(client: AsyncClient, session: AsyncSession):
    await _seed_member(session, mitgliedsnummer="M040", eintrittsdatum=date(2024, 1, 1))
    await session.flush()

    resp = await client.post(
        "/api/chat", json={"message": "beiträge berechnen"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["tool_used"] == "BeitraegeService.calculate_all_fees"
    assert data["data"] is not None
    assert data["data"]["count"] >= 1


async def test_beitraege_with_year(client: AsyncClient, session: AsyncSession):
    """Year extraction from message should work."""
    await _seed_member(session, mitgliedsnummer="M041", eintrittsdatum=date(2024, 1, 1))
    await session.flush()

    resp = await client.post(
        "/api/chat", json={"message": "fee calc 2025"}
    )
    assert resp.status_code == 200
    assert resp.json()["tool_used"] == "BeitraegeService.calculate_all_fees"


# ---------------------------------------------------------------------------
# Context field
# ---------------------------------------------------------------------------


async def test_context_field_accepted(client: AsyncClient):
    """The context field should be accepted (even if not used currently)."""
    resp = await client.post(
        "/api/chat",
        json={"message": "kassenstand", "context": "some extra context"},
    )
    assert resp.status_code == 200
    assert resp.json()["tool_used"] == "FinanzenService.get_balance_by_sphere"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


async def test_missing_message_field(client: AsyncClient):
    """POST without message field should return 422."""
    resp = await client.post("/api/chat", json={})
    assert resp.status_code == 422
