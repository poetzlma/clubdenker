from __future__ import annotations

from datetime import date
from decimal import Decimal

from sportverein.models.finanzen import Buchung, Rechnung, RechnungStatus, Sphare


class TestDatevBuchungenEndpoint:
    async def test_export_buchungen_csv(self, client, session):
        b = Buchung(
            buchungsdatum=date(2026, 3, 1),
            betrag=Decimal("100.00"),
            beschreibung="Testbuchung",
            konto="4000",
            gegenkonto="1200",
            sphare=Sphare.ideell,
        )
        session.add(b)
        await session.commit()

        resp = await client.get("/api/finanzen/export/datev/buchungen?jahr=2026")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        assert "DATEV_Buchungen_2026.csv" in resp.headers["content-disposition"]

        text = resp.content.decode("windows-1252")
        lines = text.strip().split("\r\n")
        assert len(lines) == 2
        assert "100,00 S" in lines[1]

    async def test_export_buchungen_with_month(self, client, session):
        b = Buchung(
            buchungsdatum=date(2026, 5, 15),
            betrag=Decimal("50.00"),
            beschreibung="Mai",
            konto="4000",
            gegenkonto="1200",
            sphare=Sphare.ideell,
        )
        session.add(b)
        await session.commit()

        resp = await client.get("/api/finanzen/export/datev/buchungen?jahr=2026&monat=5")
        assert resp.status_code == 200
        assert "DATEV_Buchungen_2026_05.csv" in resp.headers["content-disposition"]

    async def test_export_buchungen_empty(self, client):
        resp = await client.get("/api/finanzen/export/datev/buchungen?jahr=2099")
        assert resp.status_code == 200
        text = resp.content.decode("windows-1252")
        lines = text.strip().split("\r\n")
        assert len(lines) == 1  # header only

    async def test_export_buchungen_requires_jahr(self, client):
        resp = await client.get("/api/finanzen/export/datev/buchungen")
        assert resp.status_code == 422

    async def test_export_buchungen_content_type_charset(self, client):
        """Content-Type must specify windows-1252 charset."""
        resp = await client.get("/api/finanzen/export/datev/buchungen?jahr=2026")
        assert resp.status_code == 200
        assert "windows-1252" in resp.headers["content-type"]

    async def test_export_buchungen_content_disposition_attachment(self, client):
        """Response must be an attachment download."""
        resp = await client.get("/api/finanzen/export/datev/buchungen?jahr=2026")
        assert "attachment" in resp.headers["content-disposition"]

    async def test_export_buchungen_with_special_chars(self, client, session):
        """Umlauts and special chars must survive the HTTP response."""
        b = Buchung(
            buchungsdatum=date(2026, 3, 1),
            betrag=Decimal("10.00"),
            beschreibung="Ubungsleitergebuhr",
            konto="4000",
            gegenkonto="1200",
            sphare=Sphare.ideell,
        )
        session.add(b)
        await session.commit()

        resp = await client.get("/api/finanzen/export/datev/buchungen?jahr=2026")
        text = resp.content.decode("windows-1252")
        assert "Ubungsleitergebuhr" in text

    async def test_export_buchungen_negative_amount(self, client, session):
        """Negative amounts should appear with H (Haben) indicator."""
        b = Buchung(
            buchungsdatum=date(2026, 3, 1),
            betrag=Decimal("-250.00"),
            beschreibung="Erstattung",
            konto="4800",
            gegenkonto="1200",
            sphare=Sphare.ideell,
        )
        session.add(b)
        await session.commit()

        resp = await client.get("/api/finanzen/export/datev/buchungen?jahr=2026")
        text = resp.content.decode("windows-1252")
        assert "250,00 H" in text

    async def test_export_buchungen_month_filename(self, client):
        """Filename should include month suffix when monat is provided."""
        resp = await client.get("/api/finanzen/export/datev/buchungen?jahr=2026&monat=11")
        assert "DATEV_Buchungen_2026_11.csv" in resp.headers["content-disposition"]

    async def test_export_buchungen_no_month_filename(self, client):
        """Filename should NOT include month suffix when monat is omitted."""
        resp = await client.get("/api/finanzen/export/datev/buchungen?jahr=2026")
        disp = resp.headers["content-disposition"]
        assert "DATEV_Buchungen_2026.csv" in disp
        # Make sure no extra underscore
        assert "_0" not in disp.split("2026")[1].split(".csv")[0] or "2026.csv" in disp


class TestDatevRechnungenEndpoint:
    async def test_export_rechnungen_csv(self, client, session):
        r = Rechnung(
            rechnungsnummer="RE-2026-001",
            rechnungsdatum=date(2026, 6, 1),
            faelligkeitsdatum=date(2026, 6, 15),
            betrag=Decimal("119.00"),
            summe_netto=Decimal("100.00"),
            summe_steuer=Decimal("19.00"),
            beschreibung="Test",
            empfaenger_name="Firma GmbH",
            status=RechnungStatus.gestellt,
        )
        session.add(r)
        await session.commit()

        resp = await client.get("/api/finanzen/export/datev/rechnungen?jahr=2026")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        assert "DATEV_Rechnungen_2026.csv" in resp.headers["content-disposition"]

        text = resp.content.decode("windows-1252")
        lines = text.strip().split("\r\n")
        assert len(lines) == 2
        assert "RE-2026-001" in lines[1]
        assert "Firma GmbH" in lines[1]

    async def test_export_rechnungen_requires_jahr(self, client):
        resp = await client.get("/api/finanzen/export/datev/rechnungen")
        assert resp.status_code == 422

    async def test_export_rechnungen_empty_year(self, client):
        """Empty year should return 200 with header-only CSV."""
        resp = await client.get("/api/finanzen/export/datev/rechnungen?jahr=1999")
        assert resp.status_code == 200
        text = resp.content.decode("windows-1252")
        lines = text.strip().split("\r\n")
        assert len(lines) == 1
        assert "Rechnungsnummer" in lines[0]

    async def test_export_rechnungen_content_type_charset(self, client):
        """Content-Type must specify windows-1252 charset."""
        resp = await client.get("/api/finanzen/export/datev/rechnungen?jahr=2026")
        assert "windows-1252" in resp.headers["content-type"]

    async def test_export_rechnungen_filename(self, client):
        """Filename should follow DATEV_Rechnungen_{year}.csv pattern."""
        resp = await client.get("/api/finanzen/export/datev/rechnungen?jahr=2026")
        assert "DATEV_Rechnungen_2026.csv" in resp.headers["content-disposition"]

    async def test_export_rechnungen_semicolon_encoding(self, client, session):
        """Verify output uses semicolons and comma decimals through the HTTP layer."""
        r = Rechnung(
            rechnungsnummer="RE-2026-099",
            rechnungsdatum=date(2026, 3, 1),
            faelligkeitsdatum=date(2026, 3, 15),
            betrag=Decimal("1234.56"),
            summe_netto=Decimal("1037.45"),
            summe_steuer=Decimal("197.11"),
            beschreibung="Test",
            empfaenger_name="Verein",
            status=RechnungStatus.gestellt,
        )
        session.add(r)
        await session.commit()

        resp = await client.get("/api/finanzen/export/datev/rechnungen?jahr=2026")
        text = resp.content.decode("windows-1252")
        lines = text.strip().split("\r\n")
        assert len(lines) == 2
        parts = lines[1].split(";")
        # Amounts use comma as decimal separator
        assert parts[3] == "1037,45"
        assert parts[4] == "197,11"
        assert parts[5] == "1234,56"
