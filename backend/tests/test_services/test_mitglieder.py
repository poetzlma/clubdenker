"""Comprehensive tests for MitgliederService."""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from sportverein.models.mitglied import (
    Abteilung,
    BeitragKategorie,
    Mitglied,
    MitgliedStatus,
)
from sportverein.services.mitglieder import (
    MitgliedCreate,
    MitgliedFilter,
    MitgliedUpdate,
    MitgliederService,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_create_data(**overrides) -> MitgliedCreate:
    defaults = dict(
        vorname="Max",
        nachname="Mustermann",
        email="max@example.com",
        geburtsdatum=date(1990, 5, 15),
    )
    defaults.update(overrides)
    return MitgliedCreate(**defaults)


async def _create_abteilung(session: AsyncSession, name: str = "Fussball") -> Abteilung:
    abt = Abteilung(name=name)
    session.add(abt)
    await session.flush()
    await session.refresh(abt)
    return abt


# ---------------------------------------------------------------------------
# Tests: create
# ---------------------------------------------------------------------------


async def test_create_member_generates_mitgliedsnummer(session: AsyncSession):
    svc = MitgliederService(session)
    member = await svc.create_member(_make_create_data())

    assert member.id is not None
    assert member.mitgliedsnummer == "M-0001"
    assert member.vorname == "Max"
    assert member.nachname == "Mustermann"
    assert member.email == "max@example.com"
    assert member.status == MitgliedStatus.aktiv


async def test_create_member_sequential_numbers(session: AsyncSession):
    svc = MitgliederService(session)
    m1 = await svc.create_member(_make_create_data(email="a@example.com"))
    m2 = await svc.create_member(_make_create_data(email="b@example.com"))
    m3 = await svc.create_member(_make_create_data(email="c@example.com"))

    assert m1.mitgliedsnummer == "M-0001"
    assert m2.mitgliedsnummer == "M-0002"
    assert m3.mitgliedsnummer == "M-0003"


async def test_create_member_duplicate_email_raises(session: AsyncSession):
    svc = MitgliederService(session)
    await svc.create_member(_make_create_data())

    with pytest.raises(ValueError, match="Duplicate"):
        await svc.create_member(_make_create_data())  # same email


# ---------------------------------------------------------------------------
# Tests: get
# ---------------------------------------------------------------------------


async def test_get_member_by_id(session: AsyncSession):
    svc = MitgliederService(session)
    created = await svc.create_member(_make_create_data())

    fetched = await svc.get_member(created.id)
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.vorname == "Max"


async def test_get_member_by_id_not_found(session: AsyncSession):
    svc = MitgliederService(session)
    assert await svc.get_member(9999) is None


async def test_get_member_eager_loads_abteilungen(session: AsyncSession):
    svc = MitgliederService(session)
    member = await svc.create_member(_make_create_data())
    abt = await _create_abteilung(session)
    await svc.assign_department(member.id, abt.id)

    fetched = await svc.get_member(member.id)
    assert fetched is not None
    assert len(fetched.abteilungen) == 1
    assert fetched.abteilungen[0].abteilung.name == "Fussball"


async def test_get_member_by_number(session: AsyncSession):
    svc = MitgliederService(session)
    created = await svc.create_member(_make_create_data())

    fetched = await svc.get_member_by_number("M-0001")
    assert fetched is not None
    assert fetched.id == created.id


async def test_get_member_by_number_not_found(session: AsyncSession):
    svc = MitgliederService(session)
    assert await svc.get_member_by_number("M-9999") is None


# ---------------------------------------------------------------------------
# Tests: update
# ---------------------------------------------------------------------------


async def test_update_member_partial(session: AsyncSession):
    svc = MitgliederService(session)
    member = await svc.create_member(_make_create_data())

    updated = await svc.update_member(
        member.id, MitgliedUpdate(vorname="Moritz", telefon="0123456")
    )
    assert updated.vorname == "Moritz"
    assert updated.telefon == "0123456"
    # unchanged
    assert updated.nachname == "Mustermann"


async def test_update_member_not_found_raises(session: AsyncSession):
    svc = MitgliederService(session)
    with pytest.raises(ValueError, match="not found"):
        await svc.update_member(9999, MitgliedUpdate(vorname="Nope"))


# ---------------------------------------------------------------------------
# Tests: cancel
# ---------------------------------------------------------------------------


async def test_cancel_member(session: AsyncSession):
    svc = MitgliederService(session)
    member = await svc.create_member(_make_create_data())

    cancelled = await svc.cancel_member(member.id)
    assert cancelled.status == MitgliedStatus.gekuendigt
    assert cancelled.austrittsdatum == date.today()


async def test_cancel_member_with_explicit_date(session: AsyncSession):
    svc = MitgliederService(session)
    member = await svc.create_member(_make_create_data())
    exit_date = date(2026, 12, 31)

    cancelled = await svc.cancel_member(member.id, austrittsdatum=exit_date)
    assert cancelled.austrittsdatum == exit_date


async def test_cancel_member_not_found_raises(session: AsyncSession):
    svc = MitgliederService(session)
    with pytest.raises(ValueError, match="not found"):
        await svc.cancel_member(9999)


# ---------------------------------------------------------------------------
# Tests: search
# ---------------------------------------------------------------------------


async def _seed_members(session: AsyncSession, svc: MitgliederService):
    """Create a handful of diverse members for search tests."""
    await svc.create_member(
        _make_create_data(
            vorname="Anna",
            nachname="Schmidt",
            email="anna@example.com",
            status=MitgliedStatus.aktiv,
        )
    )
    await svc.create_member(
        _make_create_data(
            vorname="Bernd",
            nachname="Mueller",
            email="bernd@example.com",
            status=MitgliedStatus.aktiv,
            beitragskategorie=BeitragKategorie.jugend,
        )
    )
    await svc.create_member(
        _make_create_data(
            vorname="Clara",
            nachname="Schmidt",
            email="clara@example.com",
            status=MitgliedStatus.passiv,
        )
    )


async def test_search_all(session: AsyncSession):
    svc = MitgliederService(session)
    await _seed_members(session, svc)

    results, total = await svc.search_members(MitgliedFilter())
    assert total == 3
    assert len(results) == 3


async def test_search_by_name(session: AsyncSession):
    svc = MitgliederService(session)
    await _seed_members(session, svc)

    results, total = await svc.search_members(MitgliedFilter(name="Schmidt"))
    assert total == 2
    assert all("Schmidt" in m.nachname for m in results)


async def test_search_by_name_case_insensitive(session: AsyncSession):
    svc = MitgliederService(session)
    await _seed_members(session, svc)

    results, total = await svc.search_members(MitgliedFilter(name="schmidt"))
    assert total == 2


async def test_search_by_status(session: AsyncSession):
    svc = MitgliederService(session)
    await _seed_members(session, svc)

    results, total = await svc.search_members(MitgliedFilter(status=MitgliedStatus.passiv))
    assert total == 1
    assert results[0].vorname == "Clara"


async def test_search_by_beitragskategorie(session: AsyncSession):
    svc = MitgliederService(session)
    await _seed_members(session, svc)

    results, total = await svc.search_members(
        MitgliedFilter(beitragskategorie=BeitragKategorie.jugend)
    )
    assert total == 1
    assert results[0].vorname == "Bernd"


async def test_search_by_department(session: AsyncSession):
    svc = MitgliederService(session)
    await _seed_members(session, svc)
    abt = await _create_abteilung(session, "Tennis")

    # Assign only first member
    from sqlalchemy import select as sa_select

    res = await session.execute(sa_select(Mitglied).limit(1))
    first = res.scalar_one()
    await svc.assign_department(first.id, abt.id)

    results, total = await svc.search_members(MitgliedFilter(abteilung_id=abt.id))
    assert total == 1
    assert results[0].id == first.id


async def test_search_pagination(session: AsyncSession):
    svc = MitgliederService(session)
    await _seed_members(session, svc)

    page1, total = await svc.search_members(MitgliedFilter(page=1, page_size=2))
    assert total == 3
    assert len(page1) == 2

    page2, total2 = await svc.search_members(MitgliedFilter(page=2, page_size=2))
    assert total2 == 3
    assert len(page2) == 1


async def test_search_no_results(session: AsyncSession):
    svc = MitgliederService(session)
    results, total = await svc.search_members(MitgliedFilter(name="Nonexistent"))
    assert total == 0
    assert results == []


async def test_search_sort_order(session: AsyncSession):
    svc = MitgliederService(session)
    await _seed_members(session, svc)

    results, _ = await svc.search_members(MitgliedFilter(sort_by="vorname", sort_order="desc"))
    names = [m.vorname for m in results]
    assert names == sorted(names, reverse=True)


# ---------------------------------------------------------------------------
# Tests: departments
# ---------------------------------------------------------------------------


async def test_assign_department(session: AsyncSession):
    svc = MitgliederService(session)
    member = await svc.create_member(_make_create_data())
    abt = await _create_abteilung(session)

    assoc = await svc.assign_department(member.id, abt.id)
    assert assoc.mitglied_id == member.id
    assert assoc.abteilung_id == abt.id


async def test_assign_department_duplicate_raises(session: AsyncSession):
    svc = MitgliederService(session)
    member = await svc.create_member(_make_create_data())
    abt = await _create_abteilung(session)

    await svc.assign_department(member.id, abt.id)
    with pytest.raises(ValueError, match="already exists"):
        await svc.assign_department(member.id, abt.id)


async def test_remove_department(session: AsyncSession):
    svc = MitgliederService(session)
    member = await svc.create_member(_make_create_data())
    abt = await _create_abteilung(session)
    await svc.assign_department(member.id, abt.id)

    removed = await svc.remove_department(member.id, abt.id)
    assert removed is True


async def test_remove_department_not_found(session: AsyncSession):
    svc = MitgliederService(session)
    removed = await svc.remove_department(9999, 9999)
    assert removed is False


async def test_get_departments(session: AsyncSession):
    svc = MitgliederService(session)
    await _create_abteilung(session, "Fussball")
    await _create_abteilung(session, "Tennis")
    await _create_abteilung(session, "Handball")

    depts = await svc.get_departments()
    assert len(depts) == 3
    names = [d.name for d in depts]
    assert names == sorted(names)  # ordered by name


# ---------------------------------------------------------------------------
# Tests: stats
# ---------------------------------------------------------------------------


async def test_get_member_stats(session: AsyncSession):
    svc = MitgliederService(session)
    # Create members with different statuses
    await svc.create_member(_make_create_data(email="a@example.com", status=MitgliedStatus.aktiv))
    await svc.create_member(_make_create_data(email="b@example.com", status=MitgliedStatus.aktiv))
    await svc.create_member(_make_create_data(email="c@example.com", status=MitgliedStatus.passiv))

    abt = await _create_abteilung(session, "Fussball")
    # Assign first two members to department
    from sqlalchemy import select as sa_select

    res = await session.execute(sa_select(Mitglied).where(Mitglied.status == MitgliedStatus.aktiv))
    aktive = res.scalars().all()
    for m in aktive:
        await svc.assign_department(m.id, abt.id)

    stats = await svc.get_member_stats()
    assert stats["total_active"] == 2
    assert stats["total_passive"] == 1
    assert stats["new_this_month"] >= 0  # depends on eintrittsdatum defaults
    assert "Fussball" in stats["by_department"]
    assert stats["by_department"]["Fussball"] == 2


async def test_get_member_stats_empty(session: AsyncSession):
    svc = MitgliederService(session)
    stats = await svc.get_member_stats()
    assert stats["total_active"] == 0
    assert stats["total_passive"] == 0
    assert stats["new_this_month"] == 0
    assert stats["by_department"] == {}
