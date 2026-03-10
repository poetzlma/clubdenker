from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from sportverein.models.finanzen import (
    Buchung,
    Kostenstelle,
    Rechnung,
    RechnungStatus,
    Sphare,
)
from sportverein.services.datev_export import (
    DatevExportService,
    _format_date_datev,
    _format_decimal,
)


class TestFormatHelpers:
    def test_format_decimal_positive(self):
        assert _format_decimal(Decimal("1234.56")) == "1234,56"

    def test_format_decimal_negative(self):
        # _format_decimal always uses abs()
        assert _format_decimal(Decimal("-99.10")) == "99,10"

    def test_format_decimal_zero(self):
        assert _format_decimal(Decimal("0")) == "0,00"

    def test_format_date_datev(self):
        assert _format_date_datev(date(2026, 3, 5)) == "0503"

    def test_format_date_datev_double_digit(self):
        assert _format_date_datev(date(2026, 12, 25)) == "2512"


class TestExportBuchungenCsv:
    async def test_empty_result(self, session):
        svc = DatevExportService(session)
        csv_bytes = await svc.export_buchungen_csv(2026)
        text = csv_bytes.decode("windows-1252")
        lines = text.strip().split("\r\n")
        # Only header row
        assert len(lines) == 1
        assert "Umsatz (S/H)" in lines[0]
        assert "Konto" in lines[0]

    async def test_exports_buchungen(self, session):
        b1 = Buchung(
            buchungsdatum=date(2026, 3, 1),
            betrag=Decimal("100.00"),
            beschreibung="Mitgliedsbeitrag",
            konto="4000",
            gegenkonto="1200",
            sphare=Sphare.ideell,
        )
        b2 = Buchung(
            buchungsdatum=date(2026, 3, 15),
            betrag=Decimal("-50.00"),
            beschreibung="Sportgeraete",
            konto="4800",
            gegenkonto="1200",
            sphare=Sphare.zweckbetrieb,
        )
        session.add_all([b1, b2])
        await session.flush()

        svc = DatevExportService(session)
        csv_bytes = await svc.export_buchungen_csv(2026, month=3)
        text = csv_bytes.decode("windows-1252")
        lines = text.strip().split("\r\n")

        assert len(lines) == 3  # header + 2 rows

        # Check header
        assert lines[0] == "Umsatz (S/H);Konto;Gegenkonto;BU-Schluessel;Belegdatum;Belegfeld1;Buchungstext;Kostenstelle"

        # Row 1: positive amount -> S
        parts1 = lines[1].split(";")
        assert parts1[0] == "100,00 S"
        assert parts1[1] == "4000"
        assert parts1[2] == "1200"
        assert parts1[4] == "0103"  # 01. Maerz
        assert parts1[6] == "Mitgliedsbeitrag"

        # Row 2: negative amount -> H
        parts2 = lines[2].split(";")
        assert parts2[0] == "50,00 H"
        assert parts2[1] == "4800"
        assert parts2[4] == "1503"

    async def test_month_filter(self, session):
        b_march = Buchung(
            buchungsdatum=date(2026, 3, 1),
            betrag=Decimal("100.00"),
            beschreibung="March entry",
            konto="4000",
            gegenkonto="1200",
            sphare=Sphare.ideell,
        )
        b_april = Buchung(
            buchungsdatum=date(2026, 4, 1),
            betrag=Decimal("200.00"),
            beschreibung="April entry",
            konto="4000",
            gegenkonto="1200",
            sphare=Sphare.ideell,
        )
        session.add_all([b_march, b_april])
        await session.flush()

        svc = DatevExportService(session)
        csv_bytes = await svc.export_buchungen_csv(2026, month=3)
        text = csv_bytes.decode("windows-1252")
        lines = text.strip().split("\r\n")
        assert len(lines) == 2  # header + 1 row (only March)

    async def test_kostenstelle_name_resolved(self, session):
        ks = Kostenstelle(name="Fussball", beschreibung="Fussball-Abteilung")
        session.add(ks)
        await session.flush()

        b = Buchung(
            buchungsdatum=date(2026, 1, 10),
            betrag=Decimal("300.00"),
            beschreibung="Training",
            konto="4000",
            gegenkonto="1200",
            sphare=Sphare.zweckbetrieb,
            kostenstelle_id=ks.id,
        )
        session.add(b)
        await session.flush()

        svc = DatevExportService(session)
        csv_bytes = await svc.export_buchungen_csv(2026)
        text = csv_bytes.decode("windows-1252")
        lines = text.strip().split("\r\n")
        parts = lines[1].split(";")
        assert parts[7] == "Fussball"

    async def test_encoding_windows_1252(self, session):
        b = Buchung(
            buchungsdatum=date(2026, 5, 1),
            betrag=Decimal("10.00"),
            beschreibung="Gebuehr fuer Uebungsleiter",
            konto="4000",
            gegenkonto="1200",
            sphare=Sphare.ideell,
        )
        session.add(b)
        await session.flush()

        svc = DatevExportService(session)
        csv_bytes = await svc.export_buchungen_csv(2026)
        # Should be decodable as windows-1252
        text = csv_bytes.decode("windows-1252")
        assert "Gebuehr" in text


class TestExportRechnungenCsv:
    async def test_empty_result(self, session):
        svc = DatevExportService(session)
        csv_bytes = await svc.export_rechnungen_csv(2026)
        text = csv_bytes.decode("windows-1252")
        lines = text.strip().split("\r\n")
        assert len(lines) == 1
        assert "Rechnungsnummer" in lines[0]

    async def test_exports_rechnungen(self, session):
        r = Rechnung(
            rechnungsnummer="RE-2026-001",
            rechnungsdatum=date(2026, 3, 10),
            faelligkeitsdatum=date(2026, 3, 24),
            betrag=Decimal("119.00"),
            summe_netto=Decimal("100.00"),
            summe_steuer=Decimal("19.00"),
            beschreibung="Hallenmiete",
            empfaenger_name="TSV Beispielstadt",
            status=RechnungStatus.gestellt,
        )
        session.add(r)
        await session.flush()

        svc = DatevExportService(session)
        csv_bytes = await svc.export_rechnungen_csv(2026)
        text = csv_bytes.decode("windows-1252")
        lines = text.strip().split("\r\n")

        assert len(lines) == 2
        parts = lines[1].split(";")
        assert parts[0] == "RE-2026-001"
        assert parts[1] == "1003"  # 10. Maerz
        assert parts[2] == "TSV Beispielstadt"
        assert parts[3] == "100,00"
        assert parts[4] == "19,00"
        assert parts[5] == "119,00"
        assert parts[6] == "gestellt"

    async def test_year_filter(self, session):
        r1 = Rechnung(
            rechnungsnummer="RE-2026-001",
            rechnungsdatum=date(2026, 6, 1),
            faelligkeitsdatum=date(2026, 6, 15),
            betrag=Decimal("50.00"),
            summe_netto=Decimal("50.00"),
            summe_steuer=Decimal("0.00"),
            beschreibung="Test",
            status=RechnungStatus.entwurf,
        )
        r2 = Rechnung(
            rechnungsnummer="RE-2025-099",
            rechnungsdatum=date(2025, 12, 1),
            faelligkeitsdatum=date(2025, 12, 15),
            betrag=Decimal("75.00"),
            summe_netto=Decimal("75.00"),
            summe_steuer=Decimal("0.00"),
            beschreibung="Last year",
            status=RechnungStatus.bezahlt,
        )
        session.add_all([r1, r2])
        await session.flush()

        svc = DatevExportService(session)
        csv_bytes = await svc.export_rechnungen_csv(2026)
        text = csv_bytes.decode("windows-1252")
        lines = text.strip().split("\r\n")
        assert len(lines) == 2  # header + 1 (only 2026)

    async def test_semicolon_separator(self, session):
        svc = DatevExportService(session)
        csv_bytes = await svc.export_rechnungen_csv(2026)
        text = csv_bytes.decode("windows-1252")
        header = text.strip().split("\r\n")[0]
        assert ";" in header
        assert "," not in header  # commas only appear in decimal values, not as separator
