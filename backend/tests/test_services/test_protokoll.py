"""Comprehensive tests for ProtokollService."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from sportverein.models.protokoll import Protokoll, ProtokollTyp
from sportverein.services.protokoll import ProtokollService

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_protokoll(
    session: AsyncSession,
    *,
    titel: str = "Vorstandssitzung Q1",
    datum: str = "2026-01-15",
    inhalt: str = "TOP 1: Haushalt\nTOP 2: Planung",
    typ: str = "vorstandssitzung",
    erstellt_von: str | None = "Max Mustermann",
    teilnehmer: str | None = "Max, Erika",
    beschluesse: str | None = "Haushalt angenommen.",
) -> Protokoll:
    svc = ProtokollService(session)
    p = await svc.create_protokoll(
        titel=titel,
        datum=datum,
        inhalt=inhalt,
        typ=typ,
        erstellt_von=erstellt_von,
        teilnehmer=teilnehmer,
        beschluesse=beschluesse,
    )
    await session.flush()
    return p


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


async def test_create_protokoll(session: AsyncSession):
    p = await _create_protokoll(session)
    assert p.id is not None
    assert p.titel == "Vorstandssitzung Q1"
    assert p.typ == ProtokollTyp.vorstandssitzung
    assert p.erstellt_von == "Max Mustermann"
    assert p.teilnehmer == "Max, Erika"
    assert p.beschluesse == "Haushalt angenommen."


async def test_create_minimal(session: AsyncSession):
    """Create with only required fields."""
    svc = ProtokollService(session)
    p = await svc.create_protokoll(
        titel="Kurzes Protokoll",
        datum="2026-03-01",
        inhalt="Kurze Notizen.",
    )
    assert p.id is not None
    assert p.typ == ProtokollTyp.sonstige  # default
    assert p.erstellt_von is None
    assert p.teilnehmer is None
    assert p.beschluesse is None


async def test_create_all_types(session: AsyncSession):
    """All ProtokollTyp values should be valid."""
    svc = ProtokollService(session)
    for typ_val in ProtokollTyp:
        p = await svc.create_protokoll(
            titel=f"Test {typ_val.value}",
            datum="2026-02-01",
            inhalt="Inhalt",
            typ=typ_val.value,
        )
        assert p.typ == typ_val


# ---------------------------------------------------------------------------
# Get
# ---------------------------------------------------------------------------


async def test_get_protokoll(session: AsyncSession):
    created = await _create_protokoll(session)
    svc = ProtokollService(session)
    fetched = await svc.get_protokoll(created.id)
    assert fetched.id == created.id
    assert fetched.titel == created.titel
    assert fetched.inhalt == created.inhalt


async def test_get_not_found(session: AsyncSession):
    svc = ProtokollService(session)
    with pytest.raises(ValueError, match="nicht gefunden"):
        await svc.get_protokoll(9999)


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------


async def test_list_empty(session: AsyncSession):
    svc = ProtokollService(session)
    items, total = await svc.list_protokolle()
    assert total == 0
    assert items == []


async def test_list_returns_all(session: AsyncSession):
    await _create_protokoll(session, titel="Sitzung 1", datum="2026-01-01")
    await _create_protokoll(session, titel="Sitzung 2", datum="2026-02-01")
    await _create_protokoll(session, titel="Sitzung 3", datum="2026-03-01")

    svc = ProtokollService(session)
    items, total = await svc.list_protokolle()
    assert total == 3
    assert len(items) == 3


async def test_list_ordered_by_datum_desc(session: AsyncSession):
    await _create_protokoll(session, titel="Jan", datum="2026-01-01")
    await _create_protokoll(session, titel="Mar", datum="2026-03-01")
    await _create_protokoll(session, titel="Feb", datum="2026-02-01")

    svc = ProtokollService(session)
    items, total = await svc.list_protokolle()
    assert total == 3
    assert items[0].titel == "Mar"
    assert items[1].titel == "Feb"
    assert items[2].titel == "Jan"


async def test_list_filter_by_typ(session: AsyncSession):
    await _create_protokoll(session, titel="VS1", typ="vorstandssitzung")
    await _create_protokoll(session, titel="MV1", typ="mitgliederversammlung")
    await _create_protokoll(session, titel="VS2", typ="vorstandssitzung")

    svc = ProtokollService(session)
    items, total = await svc.list_protokolle(typ="vorstandssitzung")
    assert total == 2
    assert all(p.typ == ProtokollTyp.vorstandssitzung for p in items)


async def test_list_search_title(session: AsyncSession):
    await _create_protokoll(session, titel="Tennis Abteilung")
    await _create_protokoll(session, titel="Fussball Abteilung")

    svc = ProtokollService(session)
    items, total = await svc.list_protokolle(search="Tennis")
    assert total == 1
    assert items[0].titel == "Tennis Abteilung"


async def test_list_search_inhalt(session: AsyncSession):
    await _create_protokoll(session, titel="Sitzung A", inhalt="Thema: Hallenmiete")
    await _create_protokoll(session, titel="Sitzung B", inhalt="Thema: Mitgliedsbeitrag")

    svc = ProtokollService(session)
    items, total = await svc.list_protokolle(search="Hallenmiete")
    assert total == 1
    assert items[0].titel == "Sitzung A"


async def test_list_search_case_insensitive(session: AsyncSession):
    await _create_protokoll(session, titel="Vorstandssitzung April")

    svc = ProtokollService(session)
    items, total = await svc.list_protokolle(search="vorstandssitzung april")
    assert total == 1


async def test_list_pagination(session: AsyncSession):
    for i in range(5):
        await _create_protokoll(session, titel=f"Sitzung {i}", datum=f"2026-0{i+1}-01")

    svc = ProtokollService(session)
    items_p1, total = await svc.list_protokolle(page=1, page_size=2)
    assert total == 5
    assert len(items_p1) == 2

    items_p2, total2 = await svc.list_protokolle(page=2, page_size=2)
    assert total2 == 5
    assert len(items_p2) == 2

    # No overlap
    ids_p1 = {p.id for p in items_p1}
    ids_p2 = {p.id for p in items_p2}
    assert ids_p1.isdisjoint(ids_p2)

    # Last page
    items_p3, _ = await svc.list_protokolle(page=3, page_size=2)
    assert len(items_p3) == 1


async def test_list_filter_and_search_combined(session: AsyncSession):
    await _create_protokoll(session, titel="VS Tennis", typ="vorstandssitzung")
    await _create_protokoll(session, titel="VS Fussball", typ="vorstandssitzung")
    await _create_protokoll(session, titel="MV Tennis", typ="mitgliederversammlung")

    svc = ProtokollService(session)
    items, total = await svc.list_protokolle(typ="vorstandssitzung", search="Tennis")
    assert total == 1
    assert items[0].titel == "VS Tennis"


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------


async def test_update_titel(session: AsyncSession):
    p = await _create_protokoll(session)
    svc = ProtokollService(session)
    updated = await svc.update_protokoll(p.id, titel="Neuer Titel")
    assert updated.titel == "Neuer Titel"
    assert updated.inhalt == p.inhalt  # unchanged


async def test_update_typ(session: AsyncSession):
    p = await _create_protokoll(session, typ="sonstige")
    svc = ProtokollService(session)
    updated = await svc.update_protokoll(p.id, typ="mitgliederversammlung")
    assert updated.typ == ProtokollTyp.mitgliederversammlung


async def test_update_multiple_fields(session: AsyncSession):
    p = await _create_protokoll(session)
    svc = ProtokollService(session)
    updated = await svc.update_protokoll(
        p.id,
        titel="Aktualisiert",
        inhalt="Neuer Inhalt",
        beschluesse="Neuer Beschluss",
    )
    assert updated.titel == "Aktualisiert"
    assert updated.inhalt == "Neuer Inhalt"
    assert updated.beschluesse == "Neuer Beschluss"


async def test_update_not_found(session: AsyncSession):
    svc = ProtokollService(session)
    with pytest.raises(ValueError, match="nicht gefunden"):
        await svc.update_protokoll(9999, titel="Nope")


async def test_update_ignores_unknown_fields(session: AsyncSession):
    p = await _create_protokoll(session)
    svc = ProtokollService(session)
    # unknown_field should be silently ignored (hasattr check in service)
    updated = await svc.update_protokoll(p.id, unknown_field="value")
    assert updated.id == p.id


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


async def test_delete_protokoll(session: AsyncSession):
    p = await _create_protokoll(session)
    svc = ProtokollService(session)
    await svc.delete_protokoll(p.id)
    await session.flush()

    with pytest.raises(ValueError, match="nicht gefunden"):
        await svc.get_protokoll(p.id)


async def test_delete_not_found(session: AsyncSession):
    svc = ProtokollService(session)
    with pytest.raises(ValueError, match="nicht gefunden"):
        await svc.delete_protokoll(9999)
