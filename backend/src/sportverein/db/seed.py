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
from sportverein.models.finanzen import (
    Kostenstelle,
    Rechnung,
    RechnungStatus,
    RechnungTyp,
    Rechnungsposition,
    EmpfaengerTyp,
    RechnungFormat,
)
from sportverein.models.vereinsstammdaten import Vereinsstammdaten
from sportverein.models.audit import AuditLog
from sportverein.models.ehrenamt import Aufwandsentschaedigung, AufwandTyp
from sportverein.models.training import Anwesenheit, Trainingsgruppe, Wochentag
from sportverein.auth.models import AdminUser, ApiToken

VORNAMEN = [
    "Hans",
    "Klaus",
    "Peter",
    "Thomas",
    "Michael",
    "Stefan",
    "Andreas",
    "Markus",
    "Frank",
    "Wolfgang",
    "Juergen",
    "Uwe",
    "Bernd",
    "Dieter",
    "Ralf",
    "Anna",
    "Maria",
    "Petra",
    "Sabine",
    "Monika",
    "Claudia",
    "Susanne",
    "Andrea",
    "Birgit",
    "Karin",
    "Heike",
    "Nicole",
    "Martina",
    "Stefanie",
    "Julia",
    "Lena",
    "Finn",
    "Lukas",
    "Maximilian",
    "Tim",
    "Laura",
    "Sophie",
    "Lea",
    "Emma",
    "Jonas",
    "Ben",
    "Paul",
    "Leon",
    "Felix",
    "Max",
    "Erik",
    "Jan",
    "Lisa",
    "Sarah",
    "Katrin",
]

NACHNAMEN = [
    "Mueller",
    "Schmidt",
    "Schneider",
    "Fischer",
    "Weber",
    "Meyer",
    "Wagner",
    "Becker",
    "Schulz",
    "Hoffmann",
    "Schafer",
    "Koch",
    "Bauer",
    "Richter",
    "Klein",
    "Wolf",
    "Schroeder",
    "Neumann",
    "Schwarz",
    "Zimmermann",
    "Braun",
    "Krueger",
    "Hofmann",
    "Hartmann",
    "Lange",
    "Schmitt",
    "Werner",
    "Schmitz",
    "Krause",
    "Meier",
    "Lehmann",
    "Schmid",
    "Schulze",
    "Maier",
    "Koehler",
    "Herrmann",
    "Koenig",
    "Walter",
    "Mayer",
    "Huber",
    "Kaiser",
    "Fuchs",
    "Peters",
    "Lang",
    "Scholz",
    "Moeller",
    "Weiss",
    "Jung",
    "Hahn",
    "Vogel",
]

STRASSEN = [
    "Hauptstrasse",
    "Bahnhofstrasse",
    "Schulstrasse",
    "Gartenstrasse",
    "Kirchstrasse",
    "Bergstrasse",
    "Waldstrasse",
    "Ringstrasse",
    "Lindenstrasse",
    "Parkstrasse",
    "Muehlenweg",
    "Am Markt",
]

ORTE = [
    ("70173", "Stuttgart"),
    ("80331", "Muenchen"),
    ("50667", "Koeln"),
    ("60311", "Frankfurt"),
    ("40213", "Duesseldorf"),
    ("22767", "Hamburg"),
    ("10115", "Berlin"),
    ("01067", "Dresden"),
    ("04109", "Leipzig"),
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
                email = f"{vorname.lower()}.{nachname.lower()}{i}{random.randint(1, 99)}@example.de"
            used_emails.add(email)

            plz, ort = random.choice(ORTE)
            status = random.choices(statuses, weights=[70, 15, 10, 5], k=1)[0]
            kat = random.choices(beitrag_kats, weights=[50, 20, 15, 10, 5], k=1)[0]

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
                austrittsdatum=_random_date(2024, 2025)
                if status == MitgliedStatus.gekuendigt
                else None,
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

        # --- Aufwandsentschädigungen (2026) ---
        ehrenamt_data = [
            # Uebungsleiterpauschale: Freibetrag 3.000 EUR/Jahr
            (mitglieder[0], Decimal("250.00"), date(2026, 1, 15), AufwandTyp.uebungsleiter,
             "Uebungsleiterverguetung Fussball-Jugendtraining Januar 2026"),
            (mitglieder[0], Decimal("250.00"), date(2026, 2, 15), AufwandTyp.uebungsleiter,
             "Uebungsleiterverguetung Fussball-Jugendtraining Februar 2026"),
            (mitglieder[3], Decimal("200.00"), date(2026, 1, 20), AufwandTyp.uebungsleiter,
             "Uebungsleiterverguetung Schwimmkurs Winter 2026"),
            # Ehrenamtspauschale: Freibetrag 840 EUR/Jahr
            (mitglieder[5], Decimal("70.00"), date(2026, 1, 31), AufwandTyp.ehrenamt,
             "Ehrenamtspauschale Kassenpruefer Januar 2026"),
            (mitglieder[8], Decimal("50.00"), date(2026, 2, 28), AufwandTyp.ehrenamt,
             "Ehrenamtspauschale Platzdienst Februar 2026"),
        ]
        for m, betrag, datum, typ, beschreibung in ehrenamt_data:
            session.add(
                Aufwandsentschaedigung(
                    mitglied_id=m.id,
                    betrag=betrag,
                    datum=datum,
                    typ=typ,
                    beschreibung=beschreibung,
                )
            )
        await session.flush()

        # --- Trainingsgruppen ---
        trainingsgruppen_data = [
            (
                "Herren 1. Mannschaft",
                abteilungen[0],
                "Stefan Mueller",
                Wochentag.dienstag,
                "18:30",
                90,
                22,
                "Sportplatz A",
            ),
            (
                "Herren 2. Mannschaft",
                abteilungen[0],
                "Andreas Weber",
                Wochentag.mittwoch,
                "19:00",
                90,
                22,
                "Sportplatz B",
            ),
            (
                "Jugend U17",
                abteilungen[0],
                "Frank Becker",
                Wochentag.montag,
                "17:00",
                75,
                18,
                "Sportplatz A",
            ),
            (
                "Damen Einzel",
                abteilungen[1],
                "Claudia Schmidt",
                Wochentag.donnerstag,
                "18:00",
                60,
                8,
                "Tennisplatz 1-4",
            ),
            (
                "Herren Doppel",
                abteilungen[1],
                "Peter Wagner",
                Wochentag.freitag,
                "19:00",
                90,
                12,
                "Tennisplatz 1-4",
            ),
            (
                "Schwimmtraining Erwachsene",
                abteilungen[2],
                "Monika Fischer",
                Wochentag.montag,
                "20:00",
                60,
                20,
                "Hallenbad",
            ),
            (
                "Schwimmtraining Jugend",
                abteilungen[2],
                "Heike Braun",
                Wochentag.mittwoch,
                "17:00",
                60,
                15,
                "Hallenbad",
            ),
            (
                "Lauftreff",
                abteilungen[3],
                "Wolfgang Hoffmann",
                Wochentag.samstag,
                "09:00",
                120,
                None,
                "Stadtpark",
            ),
        ]
        trainingsgruppen = []
        for name, abt, trainer, tag, zeit, dauer, max_t, ort_val in trainingsgruppen_data:
            tg = Trainingsgruppe(
                name=name,
                abteilung_id=abt.id,
                trainer=trainer,
                wochentag=tag,
                uhrzeit=zeit,
                dauer_minuten=dauer,
                max_teilnehmer=max_t,
                ort=ort_val,
                aktiv=True,
            )
            session.add(tg)
            trainingsgruppen.append(tg)
        await session.flush()

        # --- Anwesenheiten (last 12 weeks) ---
        today = date.today()
        anwesenheit_count = 0
        for week_offset in range(12):
            for tg in trainingsgruppen:
                # Map wochentag enum to weekday int (0=Monday)
                wochentag_map = {
                    Wochentag.montag: 0,
                    Wochentag.dienstag: 1,
                    Wochentag.mittwoch: 2,
                    Wochentag.donnerstag: 3,
                    Wochentag.freitag: 4,
                    Wochentag.samstag: 5,
                    Wochentag.sonntag: 6,
                }
                target_day = wochentag_map[tg.wochentag]
                # Calculate the date for this training in this past week
                days_back = week_offset * 7
                ref_date = today - timedelta(days=days_back)
                # Adjust to correct weekday
                current_day = ref_date.weekday()
                diff = target_day - current_day
                training_date = ref_date + timedelta(days=diff)
                # Only use dates in the past
                if training_date >= today:
                    continue
                # Pick a random subset of members for this training group
                n_participants = random.randint(4, min(10, len(mitglieder)))
                participants = random.sample(mitglieder, n_participants)
                for m in participants:
                    session.add(
                        Anwesenheit(
                            trainingsgruppe_id=tg.id,
                            mitglied_id=m.id,
                            datum=training_date,
                            anwesend=random.random() < 0.75,
                            notiz=None,
                        )
                    )
                    anwesenheit_count += 1
        await session.flush()

        # --- Vereinsstammdaten ---
        stammdaten = Vereinsstammdaten(
            name="TSV Sportfreunde Musterstadt 1899 e.V.",
            strasse="Am Sportpark 1",
            plz="70173",
            ort="Stuttgart",
            steuernummer="99/815/12345",
            ust_id=None,
            iban="DE89370400440532013000",
            bic="COBADEFFXXX",
            registergericht="Amtsgericht Stuttgart",
            registernummer="VR 12345",
            freistellungsbescheid_datum=date(2024, 3, 15),
            freistellungsbescheid_az="S-51/123/45678",
        )
        session.add(stammdaten)
        await session.flush()

        # --- Rechnungen (invoices with positionen) ---
        rechnungen_data = [
            {
                "nummer": "2026-IB-0001",
                "mitglied": mitglieder[0],
                "typ": RechnungTyp.mitgliedsbeitrag,
                "status": RechnungStatus.gestellt,
                "sphaere": "ideell",
                "beschreibung": "Mitgliedsbeitrag 2026",
                "positionen": [
                    (
                        "Jahresbeitrag Erwachsene 2026",
                        Decimal("1"),
                        Decimal("240.00"),
                        Decimal("0"),
                    ),
                ],
            },
            {
                "nummer": "2026-IB-0002",
                "mitglied": mitglieder[1],
                "typ": RechnungTyp.mitgliedsbeitrag,
                "status": RechnungStatus.bezahlt,
                "sphaere": "ideell",
                "beschreibung": "Mitgliedsbeitrag 2026",
                "positionen": [
                    ("Jahresbeitrag Jugend 2026", Decimal("1"), Decimal("120.00"), Decimal("0")),
                ],
            },
            {
                "nummer": "2026-ZB-0001",
                "mitglied": mitglieder[2],
                "typ": RechnungTyp.kursgebuehr,
                "status": RechnungStatus.entwurf,
                "sphaere": "zweckbetrieb",
                "beschreibung": "Schwimmkurs Fruehling 2026",
                "positionen": [
                    ("Schwimmkurs 10er-Karte", Decimal("10"), Decimal("8.00"), Decimal("19")),
                    ("Leihgebuehr Schwimmhilfe", Decimal("1"), Decimal("5.00"), Decimal("19")),
                ],
            },
            {
                "nummer": "2026-WG-0001",
                "mitglied": None,
                "typ": RechnungTyp.hallenmiete,
                "status": RechnungStatus.gestellt,
                "sphaere": "wirtschaftlich",
                "beschreibung": "Hallenmiete Firma XY",
                "empfaenger_name": "Firma XY GmbH",
                "empfaenger_strasse": "Industriestrasse 10",
                "empfaenger_plz": "70174",
                "empfaenger_ort": "Stuttgart",
                "empfaenger_typ": EmpfaengerTyp.extern,
                "positionen": [
                    ("Hallenmiete Sporthalle A, 3h", Decimal("3"), Decimal("50.00"), Decimal("19")),
                ],
            },
        ]
        for rd in rechnungen_data:
            m = rd.get("mitglied")
            brutto = Decimal("0")
            netto = Decimal("0")
            steuer = Decimal("0")
            pos_objects = []
            for idx, (desc, menge, preis, satz) in enumerate(rd["positionen"], 1):
                gp_netto = (menge * preis).quantize(Decimal("0.01"))
                gp_steuer = (gp_netto * satz / Decimal("100")).quantize(Decimal("0.01"))
                gp_brutto = gp_netto + gp_steuer
                netto += gp_netto
                steuer += gp_steuer
                brutto += gp_brutto
                pos_objects.append((idx, desc, menge, preis, satz, gp_netto, gp_steuer, gp_brutto))

            rechnung = Rechnung(
                rechnungsnummer=rd["nummer"],
                mitglied_id=m.id if m else None,
                rechnungstyp=rd["typ"],
                status=rd["status"],
                empfaenger_typ=rd.get("empfaenger_typ", EmpfaengerTyp.mitglied),
                empfaenger_name=rd.get("empfaenger_name")
                or (f"{m.vorname} {m.nachname}" if m else None),
                empfaenger_strasse=rd.get("empfaenger_strasse") or (m.strasse if m else None),
                empfaenger_plz=rd.get("empfaenger_plz") or (m.plz if m else None),
                empfaenger_ort=rd.get("empfaenger_ort") or (m.ort if m else None),
                betrag=brutto,
                summe_netto=netto,
                summe_steuer=steuer,
                bezahlt_betrag=brutto if rd["status"] == RechnungStatus.bezahlt else Decimal("0"),
                offener_betrag=Decimal("0") if rd["status"] == RechnungStatus.bezahlt else brutto,
                beschreibung=rd["beschreibung"],
                rechnungsdatum=date(2026, 1, 15),
                faelligkeitsdatum=date(2026, 1, 29),
                zahlungsziel_tage=14,
                sphaere=rd["sphaere"],
                steuerhinweis_text=(
                    "Steuerbefreit gemaess Paragraph 4 Nr. 22a UStG (Mitgliedsbeitraege)"
                    if rd["sphaere"] == "ideell"
                    else None
                ),
                verwendungszweck=f"{rd['nummer']} {rd['beschreibung']}"[:140],
                loeschdatum=date(2036, 1, 15),
                format=RechnungFormat.pdf,
            )
            session.add(rechnung)
            await session.flush()

            for pos_nr, desc, menge, preis, satz, gp_n, gp_s, gp_b in pos_objects:
                session.add(
                    Rechnungsposition(
                        rechnung_id=rechnung.id,
                        position_nr=pos_nr,
                        beschreibung=desc,
                        menge=menge,
                        einheit="x",
                        einzelpreis_netto=preis,
                        steuersatz=satz,
                        steuerbefreiungsgrund=(
                            "Paragraph 4 Nr. 22a UStG" if satz == Decimal("0") else None
                        ),
                        gesamtpreis_netto=gp_n,
                        gesamtpreis_steuer=gp_s,
                        gesamtpreis_brutto=gp_b,
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
        print(f"  - {len(trainingsgruppen)} training groups")
        print(f"  - {anwesenheit_count} attendance records")
        print("  - 1 Vereinsstammdaten")
        print(f"  - {len(rechnungen_data)} Rechnungen with Positionen")
        print("  - 5 audit log entries")
        print("  - 1 admin user (admin@sportverein.de / admin123)")
        print(f"  - 1 API token (dev-token: {token_value})")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
