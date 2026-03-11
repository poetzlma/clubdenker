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


# ---------------------------------------------------------------------------
# list_compensations tests
# ---------------------------------------------------------------------------


async def test_list_compensations_empty(session: AsyncSession):
    svc = EhrenamtService(session)
    entries = await svc.list_compensations(year=2025)
    assert entries == []


async def test_list_compensations_with_data(session: AsyncSession):
    m1 = _make_member(email="a@test.de", mitgliedsnummer="M-0010")
    m2 = _make_member(
        vorname="Erika", nachname="Musterfrau", email="b@test.de", mitgliedsnummer="M-0011"
    )
    session.add_all([m1, m2])
    await session.flush()

    svc = EhrenamtService(session)
    await svc.create_compensation(
        {
            "mitglied_id": m1.id,
            "betrag": Decimal("500.00"),
            "datum": date(2025, 3, 1),
            "typ": "uebungsleiter",
            "beschreibung": "Training Q1",
        }
    )
    await svc.create_compensation(
        {
            "mitglied_id": m2.id,
            "betrag": Decimal("200.00"),
            "datum": date(2025, 4, 1),
            "typ": "ehrenamt",
            "beschreibung": "Vereinsarbeit",
        }
    )

    entries = await svc.list_compensations(year=2025)
    assert len(entries) == 2
    # Ordered by datum desc, so m2 entry (April) comes first
    assert entries[0]["mitglied_name"] == "Erika Musterfrau"
    assert entries[0]["betrag"] == 200.00
    assert entries[0]["typ"] == "ehrenamt"
    assert entries[1]["mitglied_name"] == "Max Mustermann"
    assert entries[1]["betrag"] == 500.00
    assert entries[1]["datum"] == "2025-03-01"
    assert entries[1]["beschreibung"] == "Training Q1"


async def test_list_compensations_year_filter(session: AsyncSession):
    member = _make_member(email="c@test.de", mitgliedsnummer="M-0012")
    session.add(member)
    await session.flush()

    svc = EhrenamtService(session)
    await svc.create_compensation(
        {
            "mitglied_id": member.id,
            "betrag": Decimal("100.00"),
            "datum": date(2024, 6, 1),
            "typ": "ehrenamt",
            "beschreibung": "Last year",
        }
    )
    await svc.create_compensation(
        {
            "mitglied_id": member.id,
            "betrag": Decimal("200.00"),
            "datum": date(2025, 6, 1),
            "typ": "ehrenamt",
            "beschreibung": "This year",
        }
    )

    entries_2024 = await svc.list_compensations(year=2024)
    assert len(entries_2024) == 1
    assert entries_2024[0]["beschreibung"] == "Last year"

    entries_2025 = await svc.list_compensations(year=2025)
    assert len(entries_2025) == 1
    assert entries_2025[0]["beschreibung"] == "This year"


async def test_list_compensations_typ_filter(session: AsyncSession):
    member = _make_member(email="d@test.de", mitgliedsnummer="M-0013")
    session.add(member)
    await session.flush()

    svc = EhrenamtService(session)
    await svc.create_compensation(
        {
            "mitglied_id": member.id,
            "betrag": Decimal("500.00"),
            "datum": date(2025, 3, 1),
            "typ": "uebungsleiter",
            "beschreibung": "UL",
        }
    )
    await svc.create_compensation(
        {
            "mitglied_id": member.id,
            "betrag": Decimal("100.00"),
            "datum": date(2025, 3, 1),
            "typ": "ehrenamt",
            "beschreibung": "EA",
        }
    )

    entries = await svc.list_compensations(year=2025, typ="uebungsleiter")
    assert len(entries) == 1
    assert entries[0]["typ"] == "uebungsleiter"


# ---------------------------------------------------------------------------
# get_freibetrag_summary tests
# ---------------------------------------------------------------------------


async def test_get_freibetrag_summary_empty(session: AsyncSession):
    svc = EhrenamtService(session)
    summaries = await svc.get_freibetrag_summary(year=2025)
    assert summaries == []


async def test_get_freibetrag_summary_multiple_members(session: AsyncSession):
    m1 = _make_member(email="e@test.de", mitgliedsnummer="M-0020")
    m2 = _make_member(
        vorname="Erika", nachname="Musterfrau", email="f@test.de", mitgliedsnummer="M-0021"
    )
    session.add_all([m1, m2])
    await session.flush()

    svc = EhrenamtService(session)
    # m1: 2500 of 3000 uebungsleiter limit = 83.3%
    await svc.create_compensation(
        {
            "mitglied_id": m1.id,
            "betrag": Decimal("2500.00"),
            "datum": date(2025, 6, 1),
            "typ": "uebungsleiter",
            "beschreibung": "Training",
        }
    )
    # m2: 700 of 840 ehrenamt limit = 83.3%
    await svc.create_compensation(
        {
            "mitglied_id": m2.id,
            "betrag": Decimal("700.00"),
            "datum": date(2025, 6, 1),
            "typ": "ehrenamt",
            "beschreibung": "Vereinsarbeit",
        }
    )

    summaries = await svc.get_freibetrag_summary(year=2025)
    assert len(summaries) == 2

    by_name = {s["mitglied_name"]: s for s in summaries}

    s1 = by_name["Max Mustermann"]
    assert s1["typ"] == "uebungsleiter"
    assert s1["total"] == 2500.00
    assert s1["limit"] == 3000.00
    assert s1["remaining"] == 500.00
    assert s1["percent"] == 83.3
    assert s1["warning"] is True

    s2 = by_name["Erika Musterfrau"]
    assert s2["typ"] == "ehrenamt"
    assert s2["total"] == 700.00
    assert s2["limit"] == 840.00
    assert s2["remaining"] == 140.00
    assert s2["warning"] is True
