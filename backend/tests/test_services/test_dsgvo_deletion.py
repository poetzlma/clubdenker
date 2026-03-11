"""Tests for DSGVO data deletion (anonymization) logic."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sportverein.models.audit import AuditLog
from sportverein.models.beitrag import SepaMandat
from sportverein.models.finanzen import Rechnung, Zahlung, Zahlungsart
from sportverein.models.mitglied import Mitglied, MitgliedStatus
from sportverein.services.datenschutz import DatenschutzService
from sportverein.services.finanzen import FinanzenService
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


# ---------------------------------------------------------------------------
# Edge cases: delete_member_data with related financial data
# ---------------------------------------------------------------------------


async def test_delete_member_data_with_invoices_and_payments(session: AsyncSession):
    """Anonymization works when member has invoices and payments.

    Invoices and payments should remain intact (audit trail) while personal
    data on the member record is anonymized.
    """
    member = await _create_member(session)
    fin_svc = FinanzenService(session)

    inv = await fin_svc.create_invoice(
        mitglied_id=member.id,
        betrag=Decimal("200.00"),
        beschreibung="Jahresbeitrag",
        faelligkeitsdatum=date(2024, 12, 31),
    )
    payment = await fin_svc.record_payment(
        rechnung_id=inv.id,
        betrag=Decimal("200.00"),
        zahlungsart=Zahlungsart.ueberweisung,
    )

    svc = DatenschutzService(session)
    result = await svc.delete_member_data(member.id)

    # Member is anonymized
    assert result.vorname == "Geloescht"
    assert result.nachname == "Geloescht"
    assert result.geloescht_am is not None

    # Invoice still exists with original amounts
    inv_result = await session.execute(
        select(Rechnung).where(Rechnung.id == inv.id)
    )
    fetched_inv = inv_result.scalar_one()
    assert fetched_inv.betrag == Decimal("200.00")
    assert fetched_inv.mitglied_id == member.id

    # Payment still exists
    pay_result = await session.execute(
        select(Zahlung).where(Zahlung.id == payment.id)
    )
    fetched_pay = pay_result.scalar_one()
    assert fetched_pay.betrag == Decimal("200.00")


async def test_delete_member_data_with_sepa_mandate(session: AsyncSession):
    """Anonymization works when member has a SEPA mandate.

    The mandate record should remain (audit trail).
    """
    member = await _create_member(session)

    mandat = SepaMandat(
        mitglied_id=member.id,
        mandatsreferenz="MREF-DEL-001",
        iban="DE89370400440532013000",
        kontoinhaber="Max Mustermann",
        unterschriftsdatum=date(2023, 1, 1),
        gueltig_ab=date(2023, 1, 1),
        aktiv=True,
    )
    session.add(mandat)
    await session.flush()

    svc = DatenschutzService(session)
    result = await svc.delete_member_data(member.id)
    assert result.vorname == "Geloescht"

    # Mandate record still exists
    m_result = await session.execute(
        select(SepaMandat).where(SepaMandat.mitglied_id == member.id)
    )
    fetched_mandat = m_result.scalar_one()
    assert fetched_mandat.mandatsreferenz == "MREF-DEL-001"


async def test_delete_member_data_anonymizes_all_fields_exhaustive(session: AsyncSession):
    """Verify every single PII field is anonymized or cleared."""
    member = await _create_member(
        session,
        vorname="Erika",
        nachname="Musterfrau",
        email="erika@example.com",
        telefon="0172-9999999",
        strasse="Hauptstr. 42",
        plz="54321",
        ort="Musterort",
    )
    member.dsgvo_einwilligung = True
    member.einwilligung_datum = date(2024, 1, 15)
    member.notizen = "Sensible Notizen hier"
    await session.flush()

    svc = DatenschutzService(session)
    result = await svc.delete_member_data(member.id)

    assert result.vorname == "Geloescht"
    assert result.nachname == "Geloescht"
    assert result.email == f"geloescht-{member.id}@deleted.local"
    assert result.telefon is None
    assert result.strasse is None
    assert result.plz is None
    assert result.ort is None
    assert result.geburtsdatum == date(1900, 1, 1)
    assert result.notizen is None
    assert result.dsgvo_einwilligung is False
    assert result.einwilligung_datum is None
    assert result.status == MitgliedStatus.gekuendigt
    assert result.geloescht_am is not None
    # mitgliedsnummer is preserved for financial traceability
    assert result.mitgliedsnummer is not None
    assert result.mitgliedsnummer != ""


async def test_delete_member_data_audit_log_contains_reason(session: AsyncSession):
    """The audit log entry for deletion must contain the DSGVO reason text."""
    member = await _create_member(session)
    svc = DatenschutzService(session)

    await svc.delete_member_data(member.id)

    result = await session.execute(
        select(AuditLog).where(
            AuditLog.entity_type == "mitglied",
            AuditLog.entity_id == member.id,
            AuditLog.action == "dsgvo_loeschung",
        )
    )
    log_entry = result.scalar_one()
    assert "DSGVO" in log_entry.details
    assert "Datenlöschung" in log_entry.details or "Datenl" in log_entry.details


# ---------------------------------------------------------------------------
# Edge cases: enforce_pending_deletions
# ---------------------------------------------------------------------------


async def test_enforce_pending_deletions_with_no_members_at_all(session: AsyncSession):
    """Empty database returns empty results list."""
    svc = DatenschutzService(session)
    results = await svc.enforce_pending_deletions()
    assert results == []


async def test_enforce_pending_deletions_only_future_dates(session: AsyncSession):
    """All members have future loesch_datum -- nothing to enforce."""
    m1 = await _create_member(session, email="f1@example.com")
    m2 = await _create_member(session, email="f2@example.com")
    m1.loesch_datum = date.today() + timedelta(days=10)
    m2.loesch_datum = date.today() + timedelta(days=365)
    await session.flush()

    svc = DatenschutzService(session)
    results = await svc.enforce_pending_deletions()
    assert results == []

    # Verify members are untouched
    ms = MitgliederService(session)
    for m in [m1, m2]:
        fetched = await ms.get_member(m.id)
        assert fetched.vorname != "Geloescht"


async def test_enforce_pending_deletions_today_exact(session: AsyncSession):
    """Members with loesch_datum == today should be processed."""
    member = await _create_member(session)
    member.loesch_datum = date.today()
    await session.flush()

    svc = DatenschutzService(session)
    results = await svc.enforce_pending_deletions()

    assert len(results) == 1
    assert results[0]["mitglied_id"] == member.id
    assert results[0]["status"] == "geloescht"


async def test_enforce_pending_deletions_mixed_past_and_already_deleted(session: AsyncSession):
    """Mix of past-due members: one already deleted, one pending, one future."""
    m_already = await _create_member(session, email="already@example.com")
    m_pending = await _create_member(session, email="pending@example.com")
    m_future = await _create_member(session, email="future@example.com")

    m_already.loesch_datum = date.today() - timedelta(days=30)
    m_pending.loesch_datum = date.today() - timedelta(days=5)
    m_future.loesch_datum = date.today() + timedelta(days=100)
    await session.flush()

    svc = DatenschutzService(session)

    # Pre-delete m_already
    await svc.delete_member_data(m_already.id)

    results = await svc.enforce_pending_deletions()

    # Only m_pending should be processed (m_already excluded by geloescht_am filter)
    assert len(results) == 1
    assert results[0]["mitglied_id"] == m_pending.id
    assert results[0]["status"] == "geloescht"


async def test_enforce_pending_deletions_verifies_anonymization(session: AsyncSession):
    """After enforcement, verify the member data is actually anonymized."""
    member = await _create_member(
        session,
        vorname="Tobias",
        nachname="Test",
        email="tobias@example.com",
        telefon="0160-1111111",
        strasse="Loeschstr. 7",
        plz="99999",
        ort="Loeschstadt",
    )
    member.loesch_datum = date.today() - timedelta(days=1)
    await session.flush()

    svc = DatenschutzService(session)
    await svc.enforce_pending_deletions()

    ms = MitgliederService(session)
    fetched = await ms.get_member(member.id)
    assert fetched.vorname == "Geloescht"
    assert fetched.nachname == "Geloescht"
    assert fetched.email == f"geloescht-{member.id}@deleted.local"
    assert fetched.telefon is None
    assert fetched.strasse is None
    assert fetched.plz is None
    assert fetched.ort is None
    assert fetched.geloescht_am is not None
