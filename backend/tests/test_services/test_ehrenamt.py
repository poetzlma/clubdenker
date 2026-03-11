"""Tests for EhrenamtService."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from sportverein.models.ehrenamt import AufwandTyp
from sportverein.models.mitglied import Mitglied, MitgliedStatus
from sportverein.services.ehrenamt import EhrenamtService


def _make_member(
    *,
    vorname: str = "Max",
    nachname: str = "Mustermann",
    email: str = "max@example.com",
    mitgliedsnummer: str = "M-0001",
) -> Mitglied:
    return Mitglied(
        vorname=vorname,
        nachname=nachname,
        email=email,
        mitgliedsnummer=mitgliedsnummer,
        geburtsdatum=date(1990, 1, 1),
        eintrittsdatum=date(2020, 1, 1),
        status=MitgliedStatus.aktiv,
    )


async def test_create_compensation(session: AsyncSession):
    member = _make_member()
    session.add(member)
    await session.flush()

    svc = EhrenamtService(session)
    entry = await svc.create_compensation(
        {
            "mitglied_id": member.id,
            "betrag": Decimal("500.00"),
            "datum": date(2025, 6, 1),
            "typ": "uebungsleiter",
            "beschreibung": "Trainertaetigkeit",
        }
    )
    assert entry.id is not None
    assert entry.betrag == Decimal("500.00")
    assert entry.typ == AufwandTyp.uebungsleiter


async def test_get_annual_total(session: AsyncSession):
    member = _make_member()
    session.add(member)
    await session.flush()

    svc = EhrenamtService(session)
    await svc.create_compensation(
        {
            "mitglied_id": member.id,
            "betrag": Decimal("500.00"),
            "datum": date(2025, 3, 1),
            "typ": "uebungsleiter",
            "beschreibung": "Q1",
        }
    )
    await svc.create_compensation(
        {
            "mitglied_id": member.id,
            "betrag": Decimal("300.00"),
            "datum": date(2025, 6, 1),
            "typ": "uebungsleiter",
            "beschreibung": "Q2",
        }
    )
    # Different type
    await svc.create_compensation(
        {
            "mitglied_id": member.id,
            "betrag": Decimal("100.00"),
            "datum": date(2025, 6, 1),
            "typ": "ehrenamt",
            "beschreibung": "Ehrenamt Q2",
        }
    )

    total_ul = await svc.get_annual_total(member.id, 2025, AufwandTyp.uebungsleiter)
    assert total_ul == Decimal("800.00")

    total_ea = await svc.get_annual_total(member.id, 2025, AufwandTyp.ehrenamt)
    assert total_ea == Decimal("100.00")


async def test_get_annual_total_empty(session: AsyncSession):
    member = _make_member()
    session.add(member)
    await session.flush()

    svc = EhrenamtService(session)
    total = await svc.get_annual_total(member.id, 2025, AufwandTyp.uebungsleiter)
    assert total == Decimal("0.00")


async def test_check_limits(session: AsyncSession):
    member = _make_member()
    session.add(member)
    await session.flush()

    svc = EhrenamtService(session)
    await svc.create_compensation(
        {
            "mitglied_id": member.id,
            "betrag": Decimal("2500.00"),
            "datum": date(2025, 6, 1),
            "typ": "uebungsleiter",
            "beschreibung": "Trainertaetigkeit",
        }
    )

    limits = await svc.check_limits(member.id, 2025)
    assert limits["uebungsleiter"]["total"] == Decimal("2500.00")
    assert limits["uebungsleiter"]["limit"] == Decimal("3000.00")
    assert limits["uebungsleiter"]["remaining"] == Decimal("500.00")
    assert limits["uebungsleiter"]["percent"] == 83.3

    assert limits["ehrenamt"]["total"] == Decimal("0.00")
    assert limits["ehrenamt"]["limit"] == Decimal("840.00")
    assert limits["ehrenamt"]["remaining"] == Decimal("840.00")


async def test_get_warnings(session: AsyncSession):
    m1 = _make_member(email="a@test.de", mitgliedsnummer="M-0001")
    m2 = _make_member(email="b@test.de", mitgliedsnummer="M-0002")
    session.add_all([m1, m2])
    await session.flush()

    svc = EhrenamtService(session)
    # m1: 2500 of 3000 = 83% (above 80%)
    await svc.create_compensation(
        {
            "mitglied_id": m1.id,
            "betrag": Decimal("2500.00"),
            "datum": date(2025, 6, 1),
            "typ": "uebungsleiter",
            "beschreibung": "A",
        }
    )
    # m2: 500 of 3000 = 16% (below 80%)
    await svc.create_compensation(
        {
            "mitglied_id": m2.id,
            "betrag": Decimal("500.00"),
            "datum": date(2025, 6, 1),
            "typ": "uebungsleiter",
            "beschreibung": "B",
        }
    )

    warnings = await svc.get_warnings(2025)
    assert len(warnings) == 1
    assert warnings[0]["member_id"] == m1.id
    assert warnings[0]["typ"] == "uebungsleiter"
    assert warnings[0]["percent"] > 80


async def test_get_warnings_empty(session: AsyncSession):
    svc = EhrenamtService(session)
    warnings = await svc.get_warnings(2025)
    assert warnings == []
