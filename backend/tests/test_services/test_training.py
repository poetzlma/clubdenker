"""Tests for TrainingService."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from sportverein.models.mitglied import Abteilung, Mitglied
from sportverein.models.training import Wochentag
from sportverein.services.training import TrainingService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_abteilung(session: AsyncSession, name: str = "Fussball") -> Abteilung:
    abt = Abteilung(name=name)
    session.add(abt)
    await session.flush()
    await session.refresh(abt)
    return abt


async def _create_mitglied(session: AsyncSession, nr: int = 1) -> Mitglied:
    m = Mitglied(
        mitgliedsnummer=f"M-{nr:04d}",
        vorname=f"Test{nr}",
        nachname=f"Member{nr}",
        email=f"test{nr}@example.de",
        geburtsdatum=date(1990, 1, 1),
    )
    session.add(m)
    await session.flush()
    await session.refresh(m)
    return m


# ---------------------------------------------------------------------------
# Trainingsgruppe CRUD
# ---------------------------------------------------------------------------


async def test_create_trainingsgruppe(session: AsyncSession):
    abt = await _create_abteilung(session)
    svc = TrainingService(session)

    gruppe = await svc.create_trainingsgruppe(
        name="Herren 1",
        abteilung_id=abt.id,
        wochentag=Wochentag.dienstag,
        uhrzeit="18:30",
        trainer="Max Trainer",
        dauer_minuten=90,
        max_teilnehmer=22,
        ort="Sportplatz A",
    )

    assert gruppe.id is not None
    assert gruppe.name == "Herren 1"
    assert gruppe.abteilung_id == abt.id
    assert gruppe.wochentag == Wochentag.dienstag
    assert gruppe.uhrzeit == "18:30"
    assert gruppe.trainer == "Max Trainer"
    assert gruppe.dauer_minuten == 90
    assert gruppe.max_teilnehmer == 22
    assert gruppe.ort == "Sportplatz A"
    assert gruppe.aktiv is True


async def test_list_trainingsgruppen_filter_by_abteilung(session: AsyncSession):
    abt1 = await _create_abteilung(session, "Fussball")
    abt2 = await _create_abteilung(session, "Tennis")
    svc = TrainingService(session)

    await svc.create_trainingsgruppe("Gruppe A", abt1.id, Wochentag.montag, "18:00")
    await svc.create_trainingsgruppe("Gruppe B", abt2.id, Wochentag.dienstag, "19:00")

    all_groups = await svc.list_trainingsgruppen(aktiv=None)
    assert len(all_groups) == 2

    fussball_groups = await svc.list_trainingsgruppen(abteilung_id=abt1.id, aktiv=None)
    assert len(fussball_groups) == 1
    assert fussball_groups[0].name == "Gruppe A"


async def test_list_trainingsgruppen_filter_aktiv(session: AsyncSession):
    abt = await _create_abteilung(session)
    svc = TrainingService(session)

    await svc.create_trainingsgruppe("Active", abt.id, Wochentag.montag, "18:00", aktiv=True)
    await svc.create_trainingsgruppe("Inactive", abt.id, Wochentag.dienstag, "19:00", aktiv=False)

    active = await svc.list_trainingsgruppen(aktiv=True)
    assert len(active) == 1
    assert active[0].name == "Active"

    inactive = await svc.list_trainingsgruppen(aktiv=False)
    assert len(inactive) == 1
    assert inactive[0].name == "Inactive"


async def test_get_trainingsgruppe(session: AsyncSession):
    abt = await _create_abteilung(session)
    svc = TrainingService(session)

    gruppe = await svc.create_trainingsgruppe("Test", abt.id, Wochentag.montag, "18:00")
    fetched = await svc.get_trainingsgruppe(gruppe.id)
    assert fetched is not None
    assert fetched.name == "Test"


async def test_get_trainingsgruppe_not_found(session: AsyncSession):
    svc = TrainingService(session)
    result = await svc.get_trainingsgruppe(999)
    assert result is None


async def test_update_trainingsgruppe(session: AsyncSession):
    abt = await _create_abteilung(session)
    svc = TrainingService(session)

    gruppe = await svc.create_trainingsgruppe("Old Name", abt.id, Wochentag.montag, "18:00")
    updated = await svc.update_trainingsgruppe(gruppe.id, name="New Name", uhrzeit="19:00")
    assert updated.name == "New Name"
    assert updated.uhrzeit == "19:00"


async def test_update_trainingsgruppe_not_found(session: AsyncSession):
    svc = TrainingService(session)
    with pytest.raises(ValueError, match="nicht gefunden"):
        await svc.update_trainingsgruppe(999, name="X")


async def test_delete_trainingsgruppe(session: AsyncSession):
    abt = await _create_abteilung(session)
    svc = TrainingService(session)

    gruppe = await svc.create_trainingsgruppe("To Delete", abt.id, Wochentag.montag, "18:00")
    await svc.delete_trainingsgruppe(gruppe.id)

    fetched = await svc.get_trainingsgruppe(gruppe.id)
    assert fetched is None


async def test_delete_trainingsgruppe_not_found(session: AsyncSession):
    svc = TrainingService(session)
    with pytest.raises(ValueError, match="nicht gefunden"):
        await svc.delete_trainingsgruppe(999)


async def test_delete_trainingsgruppe_with_attendance_fails(session: AsyncSession):
    abt = await _create_abteilung(session)
    m = await _create_mitglied(session)
    svc = TrainingService(session)

    gruppe = await svc.create_trainingsgruppe("With Data", abt.id, Wochentag.montag, "18:00")
    await svc.record_anwesenheit(
        gruppe.id, date.today() - timedelta(days=1), [{"mitglied_id": m.id, "anwesend": True}]
    )

    with pytest.raises(ValueError, match="Anwesenheitseintraege"):
        await svc.delete_trainingsgruppe(gruppe.id)


# ---------------------------------------------------------------------------
# Anwesenheit
# ---------------------------------------------------------------------------


async def test_record_anwesenheit(session: AsyncSession):
    abt = await _create_abteilung(session)
    m1 = await _create_mitglied(session, 1)
    m2 = await _create_mitglied(session, 2)
    svc = TrainingService(session)

    gruppe = await svc.create_trainingsgruppe("Test", abt.id, Wochentag.montag, "18:00")
    today = date.today() - timedelta(days=1)

    records = await svc.record_anwesenheit(
        gruppe.id,
        today,
        [
            {"mitglied_id": m1.id, "anwesend": True, "notiz": "Gut trainiert"},
            {"mitglied_id": m2.id, "anwesend": False, "notiz": "Krank"},
        ],
    )

    assert len(records) == 2
    assert records[0].mitglied_id == m1.id
    assert records[0].anwesend is True
    assert records[0].notiz == "Gut trainiert"
    assert records[1].anwesend is False


async def test_record_anwesenheit_upsert(session: AsyncSession):
    """Recording attendance for the same member+group+date updates the record."""
    abt = await _create_abteilung(session)
    m = await _create_mitglied(session)
    svc = TrainingService(session)

    gruppe = await svc.create_trainingsgruppe("Test", abt.id, Wochentag.montag, "18:00")
    today = date.today() - timedelta(days=1)

    # First record
    records1 = await svc.record_anwesenheit(
        gruppe.id, today, [{"mitglied_id": m.id, "anwesend": True}]
    )
    assert records1[0].anwesend is True

    # Update same member/group/date
    records2 = await svc.record_anwesenheit(
        gruppe.id, today, [{"mitglied_id": m.id, "anwesend": False, "notiz": "Aktualisiert"}]
    )
    assert records2[0].anwesend is False
    assert records2[0].notiz == "Aktualisiert"

    # Should still only be one record
    all_records = await svc.get_anwesenheit(trainingsgruppe_id=gruppe.id)
    assert len(all_records) == 1


async def test_get_anwesenheit_with_filters(session: AsyncSession):
    abt = await _create_abteilung(session)
    m1 = await _create_mitglied(session, 1)
    m2 = await _create_mitglied(session, 2)
    svc = TrainingService(session)

    gruppe = await svc.create_trainingsgruppe("Test", abt.id, Wochentag.montag, "18:00")
    d1 = date.today() - timedelta(days=7)
    d2 = date.today() - timedelta(days=1)

    await svc.record_anwesenheit(
        gruppe.id, d1, [{"mitglied_id": m1.id, "anwesend": True}]
    )
    await svc.record_anwesenheit(
        gruppe.id, d2, [{"mitglied_id": m2.id, "anwesend": True}]
    )

    # Filter by mitglied
    records = await svc.get_anwesenheit(mitglied_id=m1.id)
    assert len(records) == 1
    assert records[0].mitglied_id == m1.id

    # Filter by date range
    records = await svc.get_anwesenheit(datum_von=d2, datum_bis=d2)
    assert len(records) == 1
    assert records[0].datum == d2

    # Filter by gruppe
    records = await svc.get_anwesenheit(trainingsgruppe_id=gruppe.id)
    assert len(records) == 2


async def test_anwesenheit_statistik(session: AsyncSession):
    abt = await _create_abteilung(session)
    m = await _create_mitglied(session)
    svc = TrainingService(session)

    gruppe = await svc.create_trainingsgruppe("Test", abt.id, Wochentag.montag, "18:00")

    # Add some attendance records over the past weeks
    for i in range(1, 5):
        d = date.today() - timedelta(weeks=i)
        await svc.record_anwesenheit(
            gruppe.id, d, [{"mitglied_id": m.id, "anwesend": i % 2 == 0}]
        )

    stats = await svc.get_anwesenheit_statistik(abt.id, wochen=12)
    assert "heatmap" in stats
    assert len(stats["heatmap"]) == 7  # 7 days
    assert stats["total_sessions"] == 4
    assert stats["total_present"] == 2
    assert stats["avg_attendance_pct"] == 50.0


async def test_mitglied_anwesenheit(session: AsyncSession):
    abt = await _create_abteilung(session)
    m = await _create_mitglied(session)
    svc = TrainingService(session)

    gruppe = await svc.create_trainingsgruppe("Test", abt.id, Wochentag.montag, "18:00")

    for i in range(1, 4):
        d = date.today() - timedelta(weeks=i)
        await svc.record_anwesenheit(
            gruppe.id, d, [{"mitglied_id": m.id, "anwesend": True}]
        )

    stats = await svc.get_mitglied_anwesenheit(m.id, wochen=12)
    assert stats["mitglied_id"] == m.id
    assert stats["total_eintraege"] == 3
    assert stats["anwesend"] == 3
    assert stats["abwesend"] == 0
    assert stats["anwesenheit_pct"] == 100.0
