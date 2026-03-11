"""Tests for DatenschutzService."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

import pytest

from sportverein.models.beitrag import SepaMandat
from sportverein.models.finanzen import Zahlungsart
from sportverein.models.mitglied import Abteilung, Mitglied, MitgliedAbteilung, MitgliedStatus
from sportverein.services.audit import AuditService
from sportverein.services.datenschutz import DatenschutzService
from sportverein.services.finanzen import FinanzenService


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


async def test_generate_auskunft_basic(session: AsyncSession):
    member = _make_member()
    session.add(member)
    await session.flush()

    svc = DatenschutzService(session)
    data = await svc.generate_auskunft(member.id)

    assert data["personal_data"]["vorname"] == "Max"
    assert data["personal_data"]["nachname"] == "Mustermann"
    assert data["personal_data"]["email"] == "max@example.com"
    assert isinstance(data["departments"], list)
    assert isinstance(data["invoices"], list)
    assert isinstance(data["payments"], list)
    assert isinstance(data["sepa_mandates"], list)
    assert isinstance(data["audit_log"], list)


async def test_generate_auskunft_with_invoices(session: AsyncSession):
    member = _make_member()
    session.add(member)
    await session.flush()

    fin_svc = FinanzenService(session)
    await fin_svc.create_invoice(
        mitglied_id=member.id,
        betrag=Decimal("240.00"),
        beschreibung="Beitrag 2024",
        faelligkeitsdatum=date(2024, 1, 31),
    )

    svc = DatenschutzService(session)
    data = await svc.generate_auskunft(member.id)
    assert len(data["invoices"]) == 1
    assert data["invoices"][0]["betrag"] == "240.00"


async def test_generate_auskunft_with_sepa(session: AsyncSession):
    member = _make_member()
    session.add(member)
    await session.flush()

    mandat = SepaMandat(
        mitglied_id=member.id,
        mandatsreferenz="MREF-001",
        iban="DE89370400440532013000",
        kontoinhaber="Max Mustermann",
        unterschriftsdatum=date(2023, 1, 1),
        gueltig_ab=date(2023, 1, 1),
        aktiv=True,
    )
    session.add(mandat)
    await session.flush()

    svc = DatenschutzService(session)
    data = await svc.generate_auskunft(member.id)
    assert len(data["sepa_mandates"]) == 1
    assert data["sepa_mandates"][0]["iban"] == "DE89370400440532013000"


async def test_generate_auskunft_not_found(session: AsyncSession):
    svc = DatenschutzService(session)
    with pytest.raises(ValueError, match="not found"):
        await svc.generate_auskunft(9999)


async def test_set_consent_true(session: AsyncSession):
    member = _make_member()
    session.add(member)
    await session.flush()

    svc = DatenschutzService(session)
    updated = await svc.set_consent(member.id, True)
    assert updated.dsgvo_einwilligung is True
    assert updated.einwilligung_datum == date.today()


async def test_set_consent_false(session: AsyncSession):
    member = _make_member()
    member.dsgvo_einwilligung = True
    member.einwilligung_datum = date.today()
    session.add(member)
    await session.flush()

    svc = DatenschutzService(session)
    updated = await svc.set_consent(member.id, False)
    assert updated.dsgvo_einwilligung is False
    assert updated.einwilligung_datum is None


async def test_set_consent_not_found(session: AsyncSession):
    svc = DatenschutzService(session)
    with pytest.raises(ValueError, match="not found"):
        await svc.set_consent(9999, True)


async def test_schedule_deletion(session: AsyncSession):
    member = _make_member()
    session.add(member)
    await session.flush()

    svc = DatenschutzService(session)
    updated = await svc.schedule_deletion(member.id, retention_days=30)
    expected = date.today() + timedelta(days=30)
    assert updated.loesch_datum == expected


async def test_schedule_deletion_not_found(session: AsyncSession):
    svc = DatenschutzService(session)
    with pytest.raises(ValueError, match="not found"):
        await svc.schedule_deletion(9999)


async def test_get_pending_deletions(session: AsyncSession):
    m1 = _make_member(email="a@test.de", mitgliedsnummer="M-0001")
    m1.loesch_datum = date.today() - timedelta(days=1)  # past
    m2 = _make_member(email="b@test.de", mitgliedsnummer="M-0002")
    m2.loesch_datum = date.today() + timedelta(days=30)  # future
    m3 = _make_member(email="c@test.de", mitgliedsnummer="M-0003")
    # No loesch_datum
    session.add_all([m1, m2, m3])
    await session.flush()

    svc = DatenschutzService(session)
    pending = await svc.get_pending_deletions()
    assert len(pending) == 1
    assert pending[0].id == m1.id


# ---------------------------------------------------------------------------
# Edge cases: generate_auskunft -- all data sections populated
# ---------------------------------------------------------------------------


async def test_generate_auskunft_includes_payments(session: AsyncSession):
    """Payments linked to a member's invoices must appear in the export."""
    member = _make_member()
    session.add(member)
    await session.flush()

    fin_svc = FinanzenService(session)
    inv = await fin_svc.create_invoice(
        mitglied_id=member.id,
        betrag=Decimal("100.00"),
        beschreibung="Beitrag",
        faelligkeitsdatum=date(2024, 6, 30),
    )
    await fin_svc.record_payment(
        rechnung_id=inv.id,
        betrag=Decimal("100.00"),
        zahlungsart=Zahlungsart.ueberweisung,
    )

    svc = DatenschutzService(session)
    data = await svc.generate_auskunft(member.id)
    assert len(data["payments"]) == 1
    assert data["payments"][0]["betrag"] == "100.00"
    assert data["payments"][0]["zahlungsart"] == "ueberweisung"


async def test_generate_auskunft_includes_audit_log(session: AsyncSession):
    """Audit log entries referencing the member must appear."""
    member = _make_member()
    session.add(member)
    await session.flush()

    audit_svc = AuditService(session)
    await audit_svc.log(
        action="test_action",
        entity_type="mitglied",
        entity_id=member.id,
        details="Some audit detail",
    )

    svc = DatenschutzService(session)
    data = await svc.generate_auskunft(member.id)
    assert len(data["audit_log"]) >= 1
    assert data["audit_log"][0]["action"] == "test_action"
    assert data["audit_log"][0]["details"] == "Some audit detail"
    assert data["audit_log"][0]["timestamp"] is not None


async def test_generate_auskunft_includes_departments(session: AsyncSession):
    """Department memberships must appear in the export."""
    member = _make_member()
    session.add(member)
    dept = Abteilung(name="Fussball", beschreibung="Fussball-Abteilung")
    session.add(dept)
    await session.flush()

    ma = MitgliedAbteilung(
        mitglied_id=member.id,
        abteilung_id=dept.id,
        beitrittsdatum=date(2023, 3, 1),
    )
    session.add(ma)
    await session.flush()

    svc = DatenschutzService(session)
    data = await svc.generate_auskunft(member.id)
    assert len(data["departments"]) == 1
    assert data["departments"][0]["abteilung"] == "Fussball"
    assert data["departments"][0]["beitrittsdatum"] == "2023-03-01"


async def test_generate_auskunft_all_personal_fields(session: AsyncSession):
    """Verify all personal data fields are present and correct."""
    member = _make_member()
    member.telefon = "0171-1234567"
    member.strasse = "Teststr. 1"
    member.plz = "12345"
    member.ort = "Teststadt"
    member.dsgvo_einwilligung = True
    member.einwilligung_datum = date(2024, 1, 1)
    member.notizen = "Test-Notiz"
    session.add(member)
    await session.flush()

    svc = DatenschutzService(session)
    data = await svc.generate_auskunft(member.id)
    pd = data["personal_data"]
    assert pd["id"] == member.id
    assert pd["mitgliedsnummer"] == "M-0001"
    assert pd["geburtsdatum"] == "1990-01-01"
    assert pd["eintrittsdatum"] == "2020-01-01"
    assert pd["austrittsdatum"] is None
    assert pd["status"] == "aktiv"
    assert pd["beitragskategorie"] == "erwachsene"
    assert pd["dsgvo_einwilligung"] is True
    assert pd["einwilligung_datum"] == "2024-01-01"
    assert pd["loesch_datum"] is None
    assert pd["strasse"] == "Teststr. 1"


async def test_generate_auskunft_with_multiple_invoices_no_payments(session: AsyncSession):
    """Multiple invoices but no payments -- payments list must be empty."""
    member = _make_member()
    session.add(member)
    await session.flush()

    fin_svc = FinanzenService(session)
    await fin_svc.create_invoice(
        mitglied_id=member.id,
        betrag=Decimal("50.00"),
        beschreibung="Invoice 1",
        faelligkeitsdatum=date(2024, 3, 31),
    )
    await fin_svc.create_invoice(
        mitglied_id=member.id,
        betrag=Decimal("75.00"),
        beschreibung="Invoice 2",
        faelligkeitsdatum=date(2024, 6, 30),
    )

    svc = DatenschutzService(session)
    data = await svc.generate_auskunft(member.id)
    assert len(data["invoices"]) == 2
    assert len(data["payments"]) == 0


async def test_generate_auskunft_with_multiple_sepa_mandates(session: AsyncSession):
    """Multiple SEPA mandates must all appear."""
    member = _make_member()
    session.add(member)
    await session.flush()

    for i in range(3):
        mandat = SepaMandat(
            mitglied_id=member.id,
            mandatsreferenz=f"MREF-{i:03d}",
            iban=f"DE8937040044053201300{i}",
            kontoinhaber="Max Mustermann",
            unterschriftsdatum=date(2023, 1, 1),
            gueltig_ab=date(2023, 1, 1),
            aktiv=(i == 0),
        )
        session.add(mandat)
    await session.flush()

    svc = DatenschutzService(session)
    data = await svc.generate_auskunft(member.id)
    assert len(data["sepa_mandates"]) == 3
    refs = {m["mandatsreferenz"] for m in data["sepa_mandates"]}
    assert refs == {"MREF-000", "MREF-001", "MREF-002"}


# ---------------------------------------------------------------------------
# Edge cases: set_consent
# ---------------------------------------------------------------------------


async def test_set_consent_toggle_twice(session: AsyncSession):
    """Setting consent True then False clears einwilligung_datum."""
    member = _make_member()
    session.add(member)
    await session.flush()

    svc = DatenschutzService(session)
    updated = await svc.set_consent(member.id, True)
    assert updated.dsgvo_einwilligung is True
    assert updated.einwilligung_datum == date.today()

    updated2 = await svc.set_consent(member.id, False)
    assert updated2.dsgvo_einwilligung is False
    assert updated2.einwilligung_datum is None


async def test_set_consent_idempotent_true(session: AsyncSession):
    """Setting consent True when already True is idempotent."""
    member = _make_member()
    member.dsgvo_einwilligung = True
    member.einwilligung_datum = date(2023, 6, 1)
    session.add(member)
    await session.flush()

    svc = DatenschutzService(session)
    updated = await svc.set_consent(member.id, True)
    assert updated.dsgvo_einwilligung is True
    # einwilligung_datum gets updated to today
    assert updated.einwilligung_datum == date.today()


async def test_set_consent_idempotent_false(session: AsyncSession):
    """Setting consent False when already False is idempotent."""
    member = _make_member()
    member.dsgvo_einwilligung = False
    member.einwilligung_datum = None
    session.add(member)
    await session.flush()

    svc = DatenschutzService(session)
    updated = await svc.set_consent(member.id, False)
    assert updated.dsgvo_einwilligung is False
    assert updated.einwilligung_datum is None


# ---------------------------------------------------------------------------
# Edge cases: schedule_deletion
# ---------------------------------------------------------------------------


async def test_schedule_deletion_default_retention(session: AsyncSession):
    """Default retention is 10 years (365*10 days)."""
    member = _make_member()
    session.add(member)
    await session.flush()

    svc = DatenschutzService(session)
    updated = await svc.schedule_deletion(member.id)
    expected = date.today() + timedelta(days=365 * 10)
    assert updated.loesch_datum == expected


async def test_schedule_deletion_overwrite(session: AsyncSession):
    """Calling schedule_deletion again overwrites loesch_datum."""
    member = _make_member()
    session.add(member)
    await session.flush()

    svc = DatenschutzService(session)
    await svc.schedule_deletion(member.id, retention_days=30)
    updated = await svc.schedule_deletion(member.id, retention_days=60)
    expected = date.today() + timedelta(days=60)
    assert updated.loesch_datum == expected


# ---------------------------------------------------------------------------
# Edge cases: get_pending_deletions
# ---------------------------------------------------------------------------


async def test_get_pending_deletions_today_is_included(session: AsyncSession):
    """Members with loesch_datum == today are pending (<=)."""
    member = _make_member()
    member.loesch_datum = date.today()
    session.add(member)
    await session.flush()

    svc = DatenschutzService(session)
    pending = await svc.get_pending_deletions()
    assert len(pending) == 1
    assert pending[0].id == member.id


async def test_get_pending_deletions_empty_db(session: AsyncSession):
    """No members at all returns empty list."""
    svc = DatenschutzService(session)
    pending = await svc.get_pending_deletions()
    assert pending == []
