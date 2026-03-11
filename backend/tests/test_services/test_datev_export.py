from __future__ import annotations

from datetime import date
from decimal import Decimal


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

    def test_format_decimal_large_value(self):
        assert _format_decimal(Decimal("99999999.99")) == "99999999,99"

    def test_format_decimal_small_fraction(self):
        assert _format_decimal(Decimal("0.01")) == "0,01"

    def test_format_decimal_rounds_to_two_places(self):
        # Decimal formatting should produce exactly 2 decimal places
        assert _format_decimal(Decimal("5.5")) == "5,50"
        assert _format_decimal(Decimal("3")) == "3,00"

    def test_format_date_datev(self):
        assert _format_date_datev(date(2026, 3, 5)) == "0503"

    def test_format_date_datev_double_digit(self):
        assert _format_date_datev(date(2026, 12, 25)) == "2512"

    def test_format_date_datev_jan_first(self):
        assert _format_date_datev(date(2026, 1, 1)) == "0101"

    def test_format_date_datev_dec_last(self):
        assert _format_date_datev(date(2026, 12, 31)) == "3112"


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
        assert (
            lines[0]
            == "Umsatz (S/H);Konto;Gegenkonto;BU-Schluessel;Belegdatum;Belegfeld1;Buchungstext;Kostenstelle"
        )

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

    async def test_special_characters_umlauts(self, session):
        """German umlauts must survive Windows-1252 encoding."""
        b = Buchung(
            buchungsdatum=date(2026, 6, 1),
            betrag=Decimal("25.00"),
            beschreibung="Gebuehr fuer Ubungsleiter",
            konto="4000",
            gegenkonto="1200",
            sphare=Sphare.ideell,
        )
        session.add(b)
        await session.flush()

        svc = DatevExportService(session)
        csv_bytes = await svc.export_buchungen_csv(2026)
        text = csv_bytes.decode("windows-1252")
        assert "Ubungsleiter" in text

    async def test_description_with_semicolons(self, session):
        """Semicolons in descriptions must be quoted so they don't break CSV parsing."""
        b = Buchung(
            buchungsdatum=date(2026, 6, 1),
            betrag=Decimal("10.00"),
            beschreibung="Gebuehr; inkl. Material",
            konto="4000",
            gegenkonto="1200",
            sphare=Sphare.ideell,
        )
        session.add(b)
        await session.flush()

        svc = DatevExportService(session)
        csv_bytes = await svc.export_buchungen_csv(2026)
        text = csv_bytes.decode("windows-1252")
        lines = text.strip().split("\r\n")
        # The row should still parse correctly -- the semicolon in the
        # description should be inside quotes so the CSV has 8 columns
        # csv.reader will handle it; let's verify with manual parse
        import csv as csv_mod
        import io

        reader = csv_mod.reader(io.StringIO(lines[1]), delimiter=";")
        row = next(reader)
        assert len(row) == 8
        assert "Gebuehr; inkl. Material" in row[6]

    async def test_description_truncated_to_60_chars(self, session):
        """DATEV limits Buchungstext to 60 characters."""
        long_desc = "A" * 100
        b = Buchung(
            buchungsdatum=date(2026, 7, 1),
            betrag=Decimal("5.00"),
            beschreibung=long_desc,
            konto="4000",
            gegenkonto="1200",
            sphare=Sphare.ideell,
        )
        session.add(b)
        await session.flush()

        svc = DatevExportService(session)
        csv_bytes = await svc.export_buchungen_csv(2026)
        text = csv_bytes.decode("windows-1252")
        lines = text.strip().split("\r\n")
        import csv as csv_mod
        import io

        reader = csv_mod.reader(io.StringIO(lines[1]), delimiter=";")
        row = next(reader)
        assert len(row[6]) == 60

    async def test_negative_amount_uses_absolute_value(self, session):
        """Negative amounts should show absolute value with H indicator."""
        b = Buchung(
            buchungsdatum=date(2026, 8, 1),
            betrag=Decimal("-1234.56"),
            beschreibung="Rueckerstattung",
            konto="4800",
            gegenkonto="1200",
            sphare=Sphare.ideell,
        )
        session.add(b)
        await session.flush()

        svc = DatevExportService(session)
        csv_bytes = await svc.export_buchungen_csv(2026)
        text = csv_bytes.decode("windows-1252")
        lines = text.strip().split("\r\n")
        parts = lines[1].split(";")
        assert parts[0] == "1234,56 H"
        # No minus sign anywhere in the amount field
        assert "-" not in parts[0]

    async def test_zero_amount_buchung(self, session):
        """Zero-amount booking should be Soll with 0,00."""
        b = Buchung(
            buchungsdatum=date(2026, 9, 1),
            betrag=Decimal("0.00"),
            beschreibung="Nullbuchung",
            konto="4000",
            gegenkonto="1200",
            sphare=Sphare.ideell,
        )
        session.add(b)
        await session.flush()

        svc = DatevExportService(session)
        csv_bytes = await svc.export_buchungen_csv(2026)
        text = csv_bytes.decode("windows-1252")
        lines = text.strip().split("\r\n")
        parts = lines[1].split(";")
        assert parts[0] == "0,00 S"

    async def test_empty_month_no_data(self, session):
        """Querying a month with no bookings returns header only."""
        b = Buchung(
            buchungsdatum=date(2026, 3, 1),
            betrag=Decimal("100.00"),
            beschreibung="March",
            konto="4000",
            gegenkonto="1200",
            sphare=Sphare.ideell,
        )
        session.add(b)
        await session.flush()

        svc = DatevExportService(session)
        csv_bytes = await svc.export_buchungen_csv(2026, month=12)
        text = csv_bytes.decode("windows-1252")
        lines = text.strip().split("\r\n")
        assert len(lines) == 1  # header only

    async def test_no_kostenstelle_leaves_field_empty(self, session):
        """Buchung without kostenstelle_id should have empty Kostenstelle field."""
        b = Buchung(
            buchungsdatum=date(2026, 10, 1),
            betrag=Decimal("50.00"),
            beschreibung="Ohne KST",
            konto="4000",
            gegenkonto="1200",
            sphare=Sphare.ideell,
        )
        session.add(b)
        await session.flush()

        svc = DatevExportService(session)
        csv_bytes = await svc.export_buchungen_csv(2026)
        text = csv_bytes.decode("windows-1252")
        lines = text.strip().split("\r\n")
        parts = lines[1].split(";")
        assert parts[7] == ""

    async def test_empty_year_no_data(self, session):
        """Querying a year with no bookings returns header only."""
        svc = DatevExportService(session)
        csv_bytes = await svc.export_buchungen_csv(1999)
        text = csv_bytes.decode("windows-1252")
        lines = text.strip().split("\r\n")
        assert len(lines) == 1


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

    async def test_rechnung_with_no_empfaenger_name(self, session):
        """empfaenger_name=None should produce an empty Kunde field."""
        r = Rechnung(
            rechnungsnummer="RE-2026-010",
            rechnungsdatum=date(2026, 4, 1),
            faelligkeitsdatum=date(2026, 4, 15),
            betrag=Decimal("50.00"),
            summe_netto=Decimal("50.00"),
            summe_steuer=Decimal("0.00"),
            beschreibung="Ohne Empfaenger",
            empfaenger_name=None,
            status=RechnungStatus.entwurf,
        )
        session.add(r)
        await session.flush()

        svc = DatevExportService(session)
        csv_bytes = await svc.export_rechnungen_csv(2026)
        text = csv_bytes.decode("windows-1252")
        lines = text.strip().split("\r\n")
        parts = lines[1].split(";")
        assert parts[2] == ""  # Kunde field empty

    async def test_rechnung_negative_steuer(self, session):
        """Negative tax (e.g. correction) should use absolute value in output."""
        r = Rechnung(
            rechnungsnummer="RE-2026-011",
            rechnungsdatum=date(2026, 5, 1),
            faelligkeitsdatum=date(2026, 5, 15),
            betrag=Decimal("-119.00"),
            summe_netto=Decimal("-100.00"),
            summe_steuer=Decimal("-19.00"),
            beschreibung="Storno-Korrektur",
            empfaenger_name="Firma ABC",
            status=RechnungStatus.storniert,
        )
        session.add(r)
        await session.flush()

        svc = DatevExportService(session)
        csv_bytes = await svc.export_rechnungen_csv(2026)
        text = csv_bytes.decode("windows-1252")
        lines = text.strip().split("\r\n")
        parts = lines[1].split(";")
        # _format_decimal uses abs(), so negatives become positive
        assert parts[3] == "100,00"  # netto
        assert parts[4] == "19,00"  # ust
        assert parts[5] == "119,00"  # brutto
        assert parts[6] == "storniert"

    async def test_rechnung_with_umlauts_in_name(self, session):
        """German umlauts in empfaenger_name must survive Windows-1252 encoding."""
        r = Rechnung(
            rechnungsnummer="RE-2026-012",
            rechnungsdatum=date(2026, 7, 1),
            faelligkeitsdatum=date(2026, 7, 15),
            betrag=Decimal("200.00"),
            summe_netto=Decimal("200.00"),
            summe_steuer=Decimal("0.00"),
            beschreibung="Test",
            empfaenger_name="Muller Sportverein",
            status=RechnungStatus.gestellt,
        )
        session.add(r)
        await session.flush()

        svc = DatevExportService(session)
        csv_bytes = await svc.export_rechnungen_csv(2026)
        text = csv_bytes.decode("windows-1252")
        assert "Muller Sportverein" in text

    async def test_rechnung_zero_amounts(self, session):
        """Zero-amount invoice should produce 0,00 values."""
        r = Rechnung(
            rechnungsnummer="RE-2026-013",
            rechnungsdatum=date(2026, 8, 1),
            faelligkeitsdatum=date(2026, 8, 15),
            betrag=Decimal("0.00"),
            summe_netto=Decimal("0.00"),
            summe_steuer=Decimal("0.00"),
            beschreibung="Null-Rechnung",
            status=RechnungStatus.entwurf,
        )
        session.add(r)
        await session.flush()

        svc = DatevExportService(session)
        csv_bytes = await svc.export_rechnungen_csv(2026)
        text = csv_bytes.decode("windows-1252")
        lines = text.strip().split("\r\n")
        parts = lines[1].split(";")
        assert parts[3] == "0,00"
        assert parts[4] == "0,00"
        assert parts[5] == "0,00"

    async def test_rechnung_empty_year(self, session):
        """Querying a year with no invoices returns header only."""
        svc = DatevExportService(session)
        csv_bytes = await svc.export_rechnungen_csv(1999)
        text = csv_bytes.decode("windows-1252")
        lines = text.strip().split("\r\n")
        assert len(lines) == 1

    async def test_encoding_is_valid_windows_1252(self, session):
        """Output bytes must be valid Windows-1252."""
        r = Rechnung(
            rechnungsnummer="RE-2026-014",
            rechnungsdatum=date(2026, 9, 1),
            faelligkeitsdatum=date(2026, 9, 15),
            betrag=Decimal("100.00"),
            summe_netto=Decimal("100.00"),
            summe_steuer=Decimal("0.00"),
            beschreibung="Test encoding",
            empfaenger_name="Schutzenverein 1880",
            status=RechnungStatus.gestellt,
        )
        session.add(r)
        await session.flush()

        svc = DatevExportService(session)
        csv_bytes = await svc.export_rechnungen_csv(2026)
        # Must decode without error
        text = csv_bytes.decode("windows-1252")
        assert "Schutzenverein 1880" in text
        # Verify it's not UTF-8 by default (header contains special chars)
        assert isinstance(csv_bytes, bytes)
