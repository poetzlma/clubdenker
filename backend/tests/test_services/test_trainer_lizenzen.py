"""Tests for trainer license management in TrainingService."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from sportverein.models.mitglied import Mitglied
from sportverein.models.training import Lizenztyp
from sportverein.services.training import TrainingService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_mitglied(session: AsyncSession, nr: int = 1) -> Mitglied:
    m = Mitglied(
        mitgliedsnummer=f"M-{nr:04d}",
        vorname=f"Trainer{nr}",
        nachname=f"Test{nr}",
        email=f"trainer{nr}@example.de",
        geburtsdatum=date(1985, 6, 15),
    )
    session.add(m)
    await session.flush()
    await session.refresh(m)
    return m


# ---------------------------------------------------------------------------
# License CRUD
# ---------------------------------------------------------------------------


async def test_create_license(session: AsyncSession):
    m = await _create_mitglied(session)
    svc = TrainingService(session)

    lizenz = await svc.create_license(
        mitglied_id=m.id,
        lizenztyp=Lizenztyp.trainerlizenz_c,
        bezeichnung="DOSB Trainerlizenz C Breitensport",
        ausstellungsdatum=date(2024, 1, 15),
        ablaufdatum=date(2028, 1, 15),
        lizenznummer="TC-2024-001",
        ausstellende_stelle="DOSB",
    )

    assert lizenz.id is not None
    assert lizenz.mitglied_id == m.id
    assert lizenz.lizenztyp == Lizenztyp.trainerlizenz_c
    assert lizenz.bezeichnung == "DOSB Trainerlizenz C Breitensport"
    assert lizenz.ausstellungsdatum == date(2024, 1, 15)
    assert lizenz.ablaufdatum == date(2028, 1, 15)
    assert lizenz.lizenznummer == "TC-2024-001"
    assert lizenz.ausstellende_stelle == "DOSB"


async def test_create_license_minimal(session: AsyncSession):
    m = await _create_mitglied(session)
    svc = TrainingService(session)

    lizenz = await svc.create_license(
        mitglied_id=m.id,
        lizenztyp=Lizenztyp.erste_hilfe,
        bezeichnung="Erste Hilfe Kurs",
        ausstellungsdatum=date(2025, 3, 1),
        ablaufdatum=date(2027, 3, 1),
    )

    assert lizenz.id is not None
    assert lizenz.lizenznummer is None
    assert lizenz.ausstellende_stelle is None


async def test_list_licenses_all(session: AsyncSession):
    m1 = await _create_mitglied(session, 1)
    m2 = await _create_mitglied(session, 2)
    svc = TrainingService(session)

    await svc.create_license(
        m1.id, Lizenztyp.trainerlizenz_c, "Lizenz C", date(2024, 1, 1), date(2028, 1, 1)
    )
    await svc.create_license(
        m2.id, Lizenztyp.erste_hilfe, "Erste Hilfe", date(2025, 1, 1), date(2027, 1, 1)
    )

    all_licenses = await svc.list_licenses()
    assert len(all_licenses) == 2


async def test_list_licenses_by_mitglied(session: AsyncSession):
    m1 = await _create_mitglied(session, 1)
    m2 = await _create_mitglied(session, 2)
    svc = TrainingService(session)

    await svc.create_license(
        m1.id, Lizenztyp.trainerlizenz_c, "Lizenz C", date(2024, 1, 1), date(2028, 1, 1)
    )
    await svc.create_license(
        m2.id, Lizenztyp.erste_hilfe, "Erste Hilfe", date(2025, 1, 1), date(2027, 1, 1)
    )

    m1_licenses = await svc.list_licenses(mitglied_id=m1.id)
    assert len(m1_licenses) == 1
    assert m1_licenses[0].mitglied_id == m1.id


async def test_list_licenses_expired_filter(session: AsyncSession):
    m = await _create_mitglied(session)
    svc = TrainingService(session)

    # Expired license
    await svc.create_license(
        m.id,
        Lizenztyp.erste_hilfe,
        "Alte Erste Hilfe",
        date(2020, 1, 1),
        date(2022, 1, 1),
    )
    # Valid license
    await svc.create_license(
        m.id,
        Lizenztyp.trainerlizenz_b,
        "Gueltige B-Lizenz",
        date(2024, 1, 1),
        date.today() + timedelta(days=365),
    )

    expired = await svc.list_licenses(expired=True)
    assert len(expired) == 1
    assert expired[0].bezeichnung == "Alte Erste Hilfe"

    valid = await svc.list_licenses(expired=False)
    assert len(valid) == 1
    assert valid[0].bezeichnung == "Gueltige B-Lizenz"


async def test_get_expiring_licenses(session: AsyncSession):
    m = await _create_mitglied(session)
    svc = TrainingService(session)

    # Expiring in 30 days
    await svc.create_license(
        m.id,
        Lizenztyp.trainerlizenz_c,
        "Bald ablaufend",
        date(2022, 1, 1),
        date.today() + timedelta(days=30),
    )
    # Expiring in 180 days (outside 90-day window)
    await svc.create_license(
        m.id,
        Lizenztyp.trainerlizenz_b,
        "Noch lange gueltig",
        date(2024, 1, 1),
        date.today() + timedelta(days=180),
    )
    # Already expired
    await svc.create_license(
        m.id,
        Lizenztyp.erste_hilfe,
        "Bereits abgelaufen",
        date(2020, 1, 1),
        date(2022, 1, 1),
    )

    expiring = await svc.get_expiring_licenses(days=90)
    assert len(expiring) == 1
    assert expiring[0].bezeichnung == "Bald ablaufend"


async def test_get_expiring_licenses_custom_days(session: AsyncSession):
    m = await _create_mitglied(session)
    svc = TrainingService(session)

    await svc.create_license(
        m.id,
        Lizenztyp.trainerlizenz_c,
        "In 150 Tagen",
        date(2022, 1, 1),
        date.today() + timedelta(days=150),
    )

    # 90 days: should not find it
    expiring_90 = await svc.get_expiring_licenses(days=90)
    assert len(expiring_90) == 0

    # 200 days: should find it
    expiring_200 = await svc.get_expiring_licenses(days=200)
    assert len(expiring_200) == 1


async def test_delete_license(session: AsyncSession):
    m = await _create_mitglied(session)
    svc = TrainingService(session)

    lizenz = await svc.create_license(
        m.id,
        Lizenztyp.erste_hilfe,
        "Zu loeschen",
        date(2024, 1, 1),
        date(2026, 1, 1),
    )

    await svc.delete_license(lizenz.id)

    remaining = await svc.list_licenses()
    assert len(remaining) == 0


async def test_delete_license_not_found(session: AsyncSession):
    svc = TrainingService(session)
    with pytest.raises(ValueError, match="nicht gefunden"):
        await svc.delete_license(999)
