"""Tests for DSGVO data deletion (anonymization) logic."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from sportverein.models.mitglied import Mitglied, MitgliedStatus
from sportverein.services.datenschutz import DatenschutzService
from sportverein.services.mitglieder import MitgliedCreate, MitgliederService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_create_data(**overrides) -> MitgliedCreate:
    defaults = dict(
        vorname="Max",
        nachname="Mustermann",
        email="max@example.com",
        geburtsdatum=date(1990, 5, 15),
        telefon="0171-1234567",
        strasse="Musterstr. 1",
        plz="12345",
        ort="Musterstadt",
    )
    defaults.update(overrides)
    return MitgliedCreate(**defaults)


async def _create_member(session: AsyncSession, **overrides) -> Mitglied:
    svc = MitgliederService(session)
    return await svc.create_member(_make_create_data(**overrides))


# ---------------------------------------------------------------------------
# Tests: delete_member_data
# ---------------------------------------------------------------------------


async def test_delete_member_data_anonymizes_fields(session: AsyncSession):
    member = await _create_member(session)
    svc = DatenschutzService(session)

    result = await svc.delete_member_data(member.id)

    assert result.vorname == "Geloescht"
    assert result.nachname == "Geloescht"
    assert result.email == f"geloescht-{member.id}@deleted.local"
    assert result.telefon is None
    assert result.strasse is None
    assert result.plz is None
    assert result.ort is None
    assert result.notizen is None
    assert result.geburtsdatum == date(1900, 1, 1)
    assert result.dsgvo_einwilligung is False
    assert result.einwilligung_datum is None
    assert result.status == MitgliedStatus.gekuendigt
    assert result.geloescht_am is not None


async def test_delete_member_data_preserves_record(session: AsyncSession):
    """The member record should still exist (soft-delete for audit trail)."""
    member = await _create_member(session)
    svc = DatenschutzService(session)

    await svc.delete_member_data(member.id)

    # Record still exists
    mitglieder_svc = MitgliederService(session)
    fetched = await mitglieder_svc.get_member(member.id)
    assert fetched is not None
    assert fetched.id == member.id
    assert fetched.mitgliedsnummer == member.mitgliedsnummer


async def test_delete_member_data_preserves_mitgliedsnummer(session: AsyncSession):
    member = await _create_member(session)
    original_nummer = member.mitgliedsnummer
    svc = DatenschutzService(session)

    result = await svc.delete_member_data(member.id)

    assert result.mitgliedsnummer == original_nummer


async def test_delete_member_data_not_found_raises(session: AsyncSession):
    svc = DatenschutzService(session)

    with pytest.raises(ValueError, match="nicht gefunden"):
        await svc.delete_member_data(9999)


async def test_delete_member_data_already_deleted_raises(session: AsyncSession):
    member = await _create_member(session)
    svc = DatenschutzService(session)

    await svc.delete_member_data(member.id)

    with pytest.raises(ValueError, match="bereits.*anonymisiert"):
        await svc.delete_member_data(member.id)


async def test_delete_member_data_creates_audit_log(session: AsyncSession):
    member = await _create_member(session)
    svc = DatenschutzService(session)

    await svc.delete_member_data(member.id)

    from sqlalchemy import select
    from sportverein.models.audit import AuditLog

    result = await session.execute(
        select(AuditLog).where(
            AuditLog.entity_type == "mitglied",
            AuditLog.entity_id == member.id,
            AuditLog.action == "dsgvo_loeschung",
        )
    )
    logs = result.scalars().all()
    assert len(logs) >= 1


# ---------------------------------------------------------------------------
# Tests: enforce_pending_deletions
# ---------------------------------------------------------------------------


async def test_enforce_pending_deletions_processes_due_members(session: AsyncSession):
    member = await _create_member(session)
    svc = DatenschutzService(session)

    # Set loesch_datum to yesterday
    member.loesch_datum = date.today() - timedelta(days=1)
    await session.flush()

    results = await svc.enforce_pending_deletions()

    assert len(results) == 1
    assert results[0]["mitglied_id"] == member.id
    assert results[0]["status"] == "geloescht"

    # Verify member was anonymized
    mitglieder_svc = MitgliederService(session)
    fetched = await mitglieder_svc.get_member(member.id)
    assert fetched is not None
    assert fetched.vorname == "Geloescht"
    assert fetched.geloescht_am is not None


async def test_enforce_pending_deletions_skips_future_dates(session: AsyncSession):
    member = await _create_member(session)
    svc = DatenschutzService(session)

    # Set loesch_datum to tomorrow
    member.loesch_datum = date.today() + timedelta(days=1)
    await session.flush()

    results = await svc.enforce_pending_deletions()

    assert len(results) == 0

    # Verify member was NOT anonymized
    mitglieder_svc = MitgliederService(session)
    fetched = await mitglieder_svc.get_member(member.id)
    assert fetched is not None
    assert fetched.vorname == "Max"


async def test_enforce_pending_deletions_skips_already_deleted(session: AsyncSession):
    member = await _create_member(session)
    svc = DatenschutzService(session)

    # Set loesch_datum to yesterday
    member.loesch_datum = date.today() - timedelta(days=1)
    await session.flush()

    # Delete once
    await svc.delete_member_data(member.id)

    # Enforce again -- should not try to re-delete
    results = await svc.enforce_pending_deletions()
    assert len(results) == 0


async def test_enforce_pending_deletions_multiple_members(session: AsyncSession):
    m1 = await _create_member(session, email="a@example.com")
    m2 = await _create_member(session, email="b@example.com")
    m3 = await _create_member(session, email="c@example.com")
    svc = DatenschutzService(session)

    # m1 and m2 are due, m3 is not
    m1.loesch_datum = date.today() - timedelta(days=10)
    m2.loesch_datum = date.today()
    m3.loesch_datum = date.today() + timedelta(days=30)
    await session.flush()

    results = await svc.enforce_pending_deletions()

    assert len(results) == 2
    deleted_ids = {r["mitglied_id"] for r in results}
    assert m1.id in deleted_ids
    assert m2.id in deleted_ids
    assert all(r["status"] == "geloescht" for r in results)


async def test_enforce_pending_deletions_empty(session: AsyncSession):
    svc = DatenschutzService(session)
    results = await svc.enforce_pending_deletions()
    assert results == []


# ---------------------------------------------------------------------------
# Tests: get_pending_deletions excludes already anonymized
# ---------------------------------------------------------------------------


async def test_get_pending_deletions_excludes_anonymized(session: AsyncSession):
    member = await _create_member(session)
    svc = DatenschutzService(session)

    member.loesch_datum = date.today() - timedelta(days=1)
    await session.flush()

    # Before deletion
    pending = await svc.get_pending_deletions()
    assert len(pending) == 1

    # After deletion
    await svc.delete_member_data(member.id)
    pending = await svc.get_pending_deletions()
    assert len(pending) == 0
