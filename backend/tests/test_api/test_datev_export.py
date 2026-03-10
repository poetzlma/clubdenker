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
