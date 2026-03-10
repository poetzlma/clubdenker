"""Tests for DatenschutzService."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

import pytest

from sportverein.models.beitrag import SepaMandat
from sportverein.models.mitglied import Mitglied, MitgliedStatus
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
