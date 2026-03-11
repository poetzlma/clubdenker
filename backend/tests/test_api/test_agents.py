"""Tests for agent workflow API endpoints."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from sportverein.models.ehrenamt import Aufwandsentschaedigung, AufwandTyp
from sportverein.models.finanzen import Rechnung, RechnungStatus
from sportverein.models.mitglied import BeitragKategorie, Mitglied, MitgliedStatus


pytestmark = pytest.mark.asyncio


async def _create_member(session: AsyncSession) -> Mitglied:
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
    session.add(member)
    await session.flush()
    await session.refresh(member)
    return member


async def test_beitragseinzug(client, session: AsyncSession):
    await _create_member(session)
    resp = await client.post(
        "/api/agents/beitragseinzug",
        json={
            "year": 2025,
            "month": 3,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["year"] == 2025
    assert body["month"] == 3
    assert body["fees_calculated"] >= 1
    assert body["invoices_created"] >= 1


async def test_mahnwesen_no_overdue(client, session: AsyncSession):
    resp = await client.post("/api/agents/mahnwesen")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_overdue"] == 0
    assert body["report"] == []


async def test_mahnwesen_with_overdue(client, session: AsyncSession):
    member = await _create_member(session)
    rechnung = Rechnung(
        rechnungsnummer="R-9001",
        mitglied_id=member.id,
        betrag=Decimal("200.00"),
        beschreibung="Overdue test",
        rechnungsdatum=date(2024, 1, 1),
        faelligkeitsdatum=date(2024, 1, 1),  # Very old
        status=RechnungStatus.offen,
    )
    session.add(rechnung)
    await session.flush()

    resp = await client.post("/api/agents/mahnwesen")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_overdue"] >= 1
    assert len(body["report"]) >= 1


async def test_aufwand_monitor_empty(client, session: AsyncSession):
    resp = await client.get("/api/agents/aufwand-monitor")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 0


async def test_compliance_monitor_empty(client, session: AsyncSession):
    resp = await client.post("/api/agents/compliance-monitor")
    assert resp.status_code == 200
    body = resp.json()
    assert "findings" in body
    assert "total" in body
    assert body["total"] >= 1  # At least the Stammdaten warning


async def test_compliance_monitor_with_findings(client, session: AsyncSession):
    member = await _create_member(session)
    # Member past deletion date
    member.loesch_datum = date.today() - timedelta(days=5)
    member.geloescht_am = None
    session.add(member)
    await session.flush()

    resp = await client.post("/api/agents/compliance-monitor")
    assert resp.status_code == 200
    body = resp.json()
    dsgvo = [f for f in body["findings"] if f["category"] == "dsgvo"]
    assert len(dsgvo) == 1
    assert dsgvo[0]["severity"] == "critical"


async def test_aufwand_monitor_with_warning(client, session: AsyncSession):
    member = await _create_member(session)
    entry = Aufwandsentschaedigung(
        mitglied_id=member.id,
        betrag=Decimal("700.00"),
        datum=date.today(),
        typ=AufwandTyp.ehrenamt,
        beschreibung="Test",
    )
    session.add(entry)
    await session.flush()

    resp = await client.get("/api/agents/aufwand-monitor")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] >= 1
    assert len(body["warnings"]) >= 1
