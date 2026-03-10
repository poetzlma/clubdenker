from __future__ import annotations

import hashlib
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from sportverein.models.mitglied import (
    Abteilung,
    BeitragKategorie,
    Mitglied,
    MitgliedAbteilung,
    MitgliedStatus,
)
from sportverein.models.beitrag import BeitragsKategorie, SepaMandat
from sportverein.auth.models import AdminUser, ApiToken


# ---- Helpers ----

def _make_mitglied(nr: str = "M-0001", email: str = "test@example.de") -> Mitglied:
    return Mitglied(
        mitgliedsnummer=nr,
        vorname="Hans",
        nachname="Mueller",
        email=email,
        geburtsdatum=date(1990, 5, 15),
        eintrittsdatum=date(2024, 1, 1),
        status=MitgliedStatus.aktiv,
        beitragskategorie=BeitragKategorie.erwachsene,
    )


# ---- Mitglied tests ----

@pytest.mark.asyncio
async def test_create_mitglied(session: AsyncSession):
    m = _make_mitglied()
    session.add(m)
    await session.commit()

    result = await session.execute(select(Mitglied))
    fetched = result.scalar_one()
    assert fetched.mitgliedsnummer == "M-0001"
    assert fetched.vorname == "Hans"
    assert fetched.status == MitgliedStatus.aktiv
    assert fetched.beitragskategorie == BeitragKategorie.erwachsene
    assert fetched.created_at is not None


@pytest.mark.asyncio
async def test_mitglied_unique_email(session: AsyncSession):
    session.add(_make_mitglied("M-0001", "dup@example.de"))
    session.add(_make_mitglied("M-0002", "dup@example.de"))
    with pytest.raises(IntegrityError):
        await session.commit()


@pytest.mark.asyncio
async def test_mitglied_unique_nummer(session: AsyncSession):
    session.add(_make_mitglied("M-0001", "a@example.de"))
    session.add(_make_mitglied("M-0001", "b@example.de"))
    with pytest.raises(IntegrityError):
        await session.commit()


# ---- Abteilung tests ----

@pytest.mark.asyncio
async def test_create_abteilung(session: AsyncSession):
    a = Abteilung(name="Fussball", beschreibung="Fussballabteilung")
    session.add(a)
    await session.commit()

    result = await session.execute(select(Abteilung))
    fetched = result.scalar_one()
    assert fetched.name == "Fussball"


@pytest.mark.asyncio
async def test_abteilung_unique_name(session: AsyncSession):
    session.add(Abteilung(name="Tennis"))
    session.add(Abteilung(name="Tennis"))
    with pytest.raises(IntegrityError):
        await session.commit()


# ---- MitgliedAbteilung relationship tests ----

@pytest.mark.asyncio
async def test_mitglied_abteilung_relationship(session: AsyncSession):
    m = _make_mitglied()
    a = Abteilung(name="Schwimmen")
    session.add_all([m, a])
    await session.flush()

    ma = MitgliedAbteilung(
        mitglied_id=m.id,
        abteilung_id=a.id,
        beitrittsdatum=date(2024, 1, 1),
    )
    session.add(ma)
    await session.commit()

    result = await session.execute(
        select(MitgliedAbteilung).where(MitgliedAbteilung.mitglied_id == m.id)
    )
    link = result.scalar_one()
    assert link.abteilung_id == a.id


@pytest.mark.asyncio
async def test_mitglied_abteilung_unique_constraint(session: AsyncSession):
    m = _make_mitglied()
    a = Abteilung(name="Leichtathletik")
    session.add_all([m, a])
    await session.flush()

    session.add(MitgliedAbteilung(mitglied_id=m.id, abteilung_id=a.id, beitrittsdatum=date(2024, 1, 1)))
    await session.flush()
    session.add(MitgliedAbteilung(mitglied_id=m.id, abteilung_id=a.id, beitrittsdatum=date(2024, 6, 1)))
    with pytest.raises(IntegrityError):
        await session.flush()


# ---- BeitragsKategorie tests ----

@pytest.mark.asyncio
async def test_create_beitragskategorie(session: AsyncSession):
    bk = BeitragsKategorie(name="erwachsene", jahresbeitrag=Decimal("240.00"), beschreibung="Erwachsene")
    session.add(bk)
    await session.commit()

    result = await session.execute(select(BeitragsKategorie))
    fetched = result.scalar_one()
    assert fetched.jahresbeitrag == Decimal("240.00")


# ---- SepaMandat tests ----

@pytest.mark.asyncio
async def test_create_sepa_mandat(session: AsyncSession):
    m = _make_mitglied()
    session.add(m)
    await session.flush()

    sm = SepaMandat(
        mitglied_id=m.id,
        mandatsreferenz="MANDATE-0001",
        iban="DE89370400440532013000",
        bic="COBADEFFXXX",
        kontoinhaber="Hans Mueller",
        unterschriftsdatum=date(2024, 1, 1),
        gueltig_ab=date(2024, 1, 1),
        aktiv=True,
    )
    session.add(sm)
    await session.commit()

    result = await session.execute(select(SepaMandat))
    fetched = result.scalar_one()
    assert fetched.mandatsreferenz == "MANDATE-0001"
    assert fetched.aktiv is True


@pytest.mark.asyncio
async def test_sepa_mandat_unique_referenz(session: AsyncSession):
    m = _make_mitglied()
    session.add(m)
    await session.flush()

    for _ in range(2):
        session.add(SepaMandat(
            mitglied_id=m.id,
            mandatsreferenz="MANDATE-DUP",
            iban="DE89370400440532013000",
            kontoinhaber="Hans Mueller",
            unterschriftsdatum=date(2024, 1, 1),
            gueltig_ab=date(2024, 1, 1),
        ))
    with pytest.raises(IntegrityError):
        await session.flush()


# ---- AdminUser tests ----

@pytest.mark.asyncio
async def test_create_admin_user(session: AsyncSession):
    admin = AdminUser(
        email="admin@test.de",
        hashed_password="hashed123",
        name="Admin",
        is_active=True,
    )
    session.add(admin)
    await session.commit()

    result = await session.execute(select(AdminUser))
    fetched = result.scalar_one()
    assert fetched.email == "admin@test.de"
    assert fetched.is_active is True


@pytest.mark.asyncio
async def test_admin_user_unique_email(session: AsyncSession):
    session.add(AdminUser(email="dup@test.de", hashed_password="h1", name="A"))
    session.add(AdminUser(email="dup@test.de", hashed_password="h2", name="B"))
    with pytest.raises(IntegrityError):
        await session.commit()


# ---- ApiToken tests ----

@pytest.mark.asyncio
async def test_create_api_token(session: AsyncSession):
    admin = AdminUser(email="admin2@test.de", hashed_password="h", name="Admin")
    session.add(admin)
    await session.flush()

    token_hash = hashlib.sha256(b"test-token").hexdigest()
    token = ApiToken(
        name="test",
        token_hash=token_hash,
        admin_user_id=admin.id,
        is_active=True,
    )
    session.add(token)
    await session.commit()

    result = await session.execute(select(ApiToken))
    fetched = result.scalar_one()
    assert fetched.name == "test"
    assert fetched.token_hash == token_hash
    assert fetched.admin_user_id == admin.id


@pytest.mark.asyncio
async def test_api_token_unique_hash(session: AsyncSession):
    admin = AdminUser(email="admin3@test.de", hashed_password="h", name="Admin")
    session.add(admin)
    await session.flush()

    same_hash = hashlib.sha256(b"same").hexdigest()
    session.add(ApiToken(name="t1", token_hash=same_hash, admin_user_id=admin.id))
    session.add(ApiToken(name="t2", token_hash=same_hash, admin_user_id=admin.id))
    with pytest.raises(IntegrityError):
        await session.flush()


# ---- Enum value tests ----

def test_mitglied_status_values():
    assert MitgliedStatus.aktiv.value == "aktiv"
    assert MitgliedStatus.passiv.value == "passiv"
    assert MitgliedStatus.gekuendigt.value == "gekuendigt"
    assert MitgliedStatus.ehrenmitglied.value == "ehrenmitglied"


def test_beitrag_kategorie_values():
    assert BeitragKategorie.erwachsene.value == "erwachsene"
    assert BeitragKategorie.jugend.value == "jugend"
    assert BeitragKategorie.familie.value == "familie"
    assert BeitragKategorie.passiv.value == "passiv"
    assert BeitragKategorie.ehrenmitglied.value == "ehrenmitglied"


def test_enums_are_str():
    assert isinstance(MitgliedStatus.aktiv, str)
    assert isinstance(BeitragKategorie.erwachsene, str)
