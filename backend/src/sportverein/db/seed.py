"""Seed script for development. Run via: python -m sportverein.db.seed"""

from __future__ import annotations

import asyncio
import hashlib
import random
from datetime import date, timedelta
from decimal import Decimal

import bcrypt as _bcrypt
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from sportverein.config import settings
from sportverein.models.base import Base
from sportverein.models.mitglied import (
    Abteilung,
    BeitragKategorie,
    Mitglied,
    MitgliedAbteilung,
    MitgliedStatus,
)
from sportverein.models.beitrag import BeitragsKategorie, SepaMandat
from sportverein.models.finanzen import Kostenstelle
from sportverein.models.audit import AuditLog
from sportverein.models.ehrenamt import Aufwandsentschaedigung, AufwandTyp
from sportverein.auth.models import AdminUser, ApiToken

VORNAMEN = [
    "Hans", "Klaus", "Peter", "Thomas", "Michael", "Stefan", "Andreas",
    "Markus", "Frank", "Wolfgang", "Juergen", "Uwe", "Bernd", "Dieter",
    "Ralf", "Anna", "Maria", "Petra", "Sabine", "Monika", "Claudia",
    "Susanne", "Andrea", "Birgit", "Karin", "Heike", "Nicole", "Martina",
    "Stefanie", "Julia", "Lena", "Finn", "Lukas", "Maximilian", "Tim",
    "Laura", "Sophie", "Lea", "Emma", "Jonas", "Ben", "Paul", "Leon",
    "Felix", "Max", "Erik", "Jan", "Lisa", "Sarah", "Katrin",
]

NACHNAMEN = [
    "Mueller", "Schmidt", "Schneider", "Fischer", "Weber", "Meyer",
    "Wagner", "Becker", "Schulz", "Hoffmann", "Schafer", "Koch",
    "Bauer", "Richter", "Klein", "Wolf", "Schroeder", "Neumann",
    "Schwarz", "Zimmermann", "Braun", "Krueger", "Hofmann", "Hartmann",
    "Lange", "Schmitt", "Werner", "Schmitz", "Krause", "Meier",
    "Lehmann", "Schmid", "Schulze", "Maier", "Koehler", "Herrmann",
    "Koenig", "Walter", "Mayer", "Huber", "Kaiser", "Fuchs",
    "Peters", "Lang", "Scholz", "Moeller", "Weiss", "Jung", "Hahn", "Vogel",
]

STRASSEN = [
    "Hauptstrasse", "Bahnhofstrasse", "Schulstrasse", "Gartenstrasse",
    "Kirchstrasse", "Bergstrasse", "Waldstrasse", "Ringstrasse",
    "Lindenstrasse", "Parkstrasse", "Muehlenweg", "Am Markt",
]

ORTE = [
    ("70173", "Stuttgart"), ("80331", "Muenchen"), ("50667", "Koeln"),
    ("60311", "Frankfurt"), ("40213", "Duesseldorf"), ("22767", "Hamburg"),
    ("10115", "Berlin"), ("01067", "Dresden"), ("04109", "Leipzig"),
    ("30159", "Hannover"),
]


def _random_date(start_year: int, end_year: int) -> date:
    start = date(start_year, 1, 1)
    end = date(end_year, 12, 31)
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def _generate_iban() -> str:
    return f"DE{random.randint(10, 99)}{random.randint(10000000, 99999999)}{random.randint(1000000000, 9999999999)}"


async def seed() -> None:
    engine = create_async_engine(settings.database_url, echo=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        # --- Abteilungen ---
        dept_data = [
            ("Fussball", "Fussballabteilung des Vereins"),
            ("Tennis", "Tennisabteilung des Vereins"),
            ("Schwimmen", "Schwimmabteilung des Vereins"),
            ("Leichtathletik", "Leichtathletikabteilung des Vereins"),
        ]
        abteilungen = []
        for name, desc in dept_data:
            a = Abteilung(name=name, beschreibung=desc)
            session.add(a)
            abteilungen.append(a)
        await session.flush()

        # --- BeitragsKategorien ---
        kat_data = [
            ("erwachsene", Decimal("240.00"), "Regulaerer Beitrag fuer Erwachsene"),
            ("jugend", Decimal("120.00"), "Ermaessigter Beitrag fuer Jugendliche"),
            ("familie", Decimal("360.00"), "Familienbeitrag"),
            ("passiv", Decimal("60.00"), "Passivmitgliedschaft"),
            ("ehrenmitglied", Decimal("0.00"), "Beitragsbefreit"),
        ]
        for name, betrag, desc in kat_data:
            session.add(BeitragsKategorie(name=name, jahresbeitrag=betrag, beschreibung=desc))
        await session.flush()

        # --- Mitglieder ---
        statuses = list(MitgliedStatus)
        beitrag_kats = list(BeitragKategorie)
        mitglieder = []
        used_emails: set[str] = set()

        for i in range(1, 51):
            vorname = random.choice(VORNAMEN)
            nachname = random.choice(NACHNAMEN)
            email = f"{vorname.lower()}.{nachname.lower()}{i}@example.de"
            while email in used_emails:
                email = f"{vorname.lower()}.{nachname.lower()}{i}{random.randint(1,99)}@example.de"
            used_emails.add(email)

            plz, ort = random.choice(ORTE)
            status = random.choices(
                statuses, weights=[70, 15, 10, 5], k=1
            )[0]
            kat = random.choices(
                beitrag_kats, weights=[50, 20, 15, 10, 5], k=1
            )[0]

            m = Mitglied(
                mitgliedsnummer=f"M-{i:04d}",
                vorname=vorname,
                nachname=nachname,
                email=email,
                telefon=f"+49 {random.randint(100, 999)} {random.randint(1000000, 9999999)}",
                geburtsdatum=_random_date(1960, 2010),
                strasse=f"{random.choice(STRASSEN)} {random.randint(1, 120)}",
                plz=plz,
                ort=ort,
                eintrittsdatum=_random_date(2015, 2025),
                austrittsdatum=_random_date(2024, 2025) if status == MitgliedStatus.gekuendigt else None,
                status=status,
                beitragskategorie=kat,
                notizen=None,
            )
            session.add(m)
            mitglieder.append(m)
        await session.flush()

        # --- MitgliedAbteilung ---
        for m in mitglieder:
            n_depts = random.randint(1, 2)
            chosen = random.sample(abteilungen, n_depts)
            for a in chosen:
                session.add(
                    MitgliedAbteilung(
                        mitglied_id=m.id,
                        abteilung_id=a.id,
                        beitrittsdatum=m.eintrittsdatum,
                    )
                )
        await session.flush()

        # --- SEPA Mandate (for ~20 members) ---
        sepa_members = random.sample(mitglieder, 20)
        for idx, m in enumerate(sepa_members, 1):
            session.add(
                SepaMandat(
                    mitglied_id=m.id,
                    mandatsreferenz=f"MANDATE-{idx:04d}",
                    iban=_generate_iban(),
                    bic="COBADEFFXXX",
                    kontoinhaber=f"{m.vorname} {m.nachname}",
                    unterschriftsdatum=m.eintrittsdatum,
                    gueltig_ab=m.eintrittsdatum,
                    gueltig_bis=None,
                    aktiv=True,
                )
            )
        await session.flush()

        # --- Kostenstellen ---
        kostenstellen_data = [
            ("Gesamtverein", None, Decimal("50000.00")),
            ("Fussball", abteilungen[0].id, Decimal("20000.00")),
            ("Tennis", abteilungen[1].id, Decimal("15000.00")),
            ("Schwimmen", abteilungen[2].id, Decimal("18000.00")),
            ("Leichtathletik", abteilungen[3].id, Decimal("12000.00")),
        ]
        kostenstellen = []
        for name, abt_id, budget in kostenstellen_data:
            ks = Kostenstelle(name=name, abteilung_id=abt_id, budget=budget)
            session.add(ks)
            kostenstellen.append(ks)
        await session.flush()

        # --- Aufwandsentschädigungen ---
        sample_members = random.sample(mitglieder[:20], 5)
        for idx, m in enumerate(sample_members):
            typ = AufwandTyp.uebungsleiter if idx % 2 == 0 else AufwandTyp.ehrenamt
            session.add(
                Aufwandsentschaedigung(
                    mitglied_id=m.id,
                    betrag=Decimal(str(random.randint(100, 500))),
                    datum=_random_date(2025, 2025),
                    typ=typ,
                    beschreibung=f"Aufwandsentschaedigung {typ.value} fuer {m.vorname} {m.nachname}",
                )
            )
        await session.flush()

        # --- AdminUser ---
        hashed_pw = _bcrypt.hashpw("admin123".encode(), _bcrypt.gensalt()).decode()
        admin = AdminUser(
            email="admin@sportverein.de",
            hashed_password=hashed_pw,
            name="Administrator",
            is_active=True,
        )
        session.add(admin)
        await session.flush()

        # --- ApiToken ---
        token_value = "sk-dev-sportverein-2024"
        token_hash = hashlib.sha256(token_value.encode()).hexdigest()
        session.add(
            ApiToken(
                name="dev-token",
                token_hash=token_hash,
                admin_user_id=admin.id,
                is_active=True,
            )
        )

        # --- Audit Log entries ---
        audit_actions = [
            ("create", "mitglied", mitglieder[0].id, '{"vorname": "Hans"}'),
            ("update", "mitglied", mitglieder[1].id, '{"email": "new@example.de"}'),
            ("login", "admin_user", admin.id, None),
            ("create", "buchung", 1, '{"betrag": "100.00"}'),
            ("export", "mitglied", mitglieder[2].id, '{"type": "dsgvo_auskunft"}'),
        ]
        for action, entity_type, entity_id, details in audit_actions:
            session.add(
                AuditLog(
                    user_id=admin.id,
                    action=action,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    details=details,
                )
            )
        await session.flush()

        await session.commit()
        print("Seed completed successfully!")
        print("  - 4 departments")
        print("  - 5 fee categories")
        print("  - 50 members")
        print("  - 20 SEPA mandates")
        print("  - 5 Kostenstellen")
        print("  - 5 Aufwandsentschaedigungen")
        print("  - 5 audit log entries")
        print("  - 1 admin user (admin@sportverein.de / admin123)")
        print(f"  - 1 API token (dev-token: {token_value})")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
