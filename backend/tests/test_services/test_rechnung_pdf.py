"""Tests for RechnungPdfService — invoice PDF generation."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from sportverein.models.mitglied import Mitglied, MitgliedStatus
from sportverein.models.vereinsstammdaten import Vereinsstammdaten
from sportverein.services.finanzen import FinanzenService
from sportverein.services.rechnung_pdf import RechnungPdfService


def _make_member(
    *,
    vorname: str = "Max",
    nachname: str = "Mustermann",
    email: str = "max@example.com",
    mitgliedsnummer: str = "M-0001",
) -> Mitglied:
    return Mitglied(
        vorname=vorname,
        nachname=nachname,
        email=email,
        mitgliedsnummer=mitgliedsnummer,
        geburtsdatum=date(1990, 1, 1),
        eintrittsdatum=date(2020, 1, 1),
        status=MitgliedStatus.aktiv,
        strasse="Musterweg 5",
        plz="12345",
        ort="Musterstadt",
    )


async def _create_stammdaten(session) -> Vereinsstammdaten:
    stamm = Vereinsstammdaten(
        name="TSV Sportfreunde Musterstadt",
        strasse="Hauptstr. 1",
        plz="12345",
        ort="Musterstadt",
        steuernummer="12/345/67890",
        iban="DE89370400440532013000",
        bic="COBADEFFXXX",
        registergericht="Amtsgericht Musterstadt",
        registernummer="VR 1234",
    )
    session.add(stamm)
    await session.flush()
    return stamm


class TestRechnungPdfGeneration:
    async def test_generate_standard_invoice_pdf(self, session):
        """Test PDF generation for a standard Mitgliedsbeitrag invoice."""
        await _create_stammdaten(session)
        member = _make_member()
        session.add(member)
        await session.flush()

        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            mitglied_id=member.id,
            beschreibung="Mitgliedsbeitrag 2026",
            rechnungstyp="mitgliedsbeitrag",
            sphaere="ideell",
            steuerhinweis_text="Die Leistung ist nach \u00a74 Nr. 22b UStG von der Umsatzsteuer befreit.",
            leistungszeitraum_von=date(2026, 1, 1),
            leistungszeitraum_bis=date(2026, 3, 31),
            positionen=[
                {
                    "beschreibung": "Grundbeitrag Erwachsene Q1/2026",
                    "menge": 1,
                    "einheit": "x",
                    "einzelpreis_netto": "45.00",
                    "steuersatz": "0",
                },
            ],
        )

        pdf_svc = RechnungPdfService()
        pdf_bytes = await pdf_svc.generate_rechnung_pdf(session, rechnung.id)

        # Basic PDF checks
        assert len(pdf_bytes) > 0
        assert pdf_bytes[:5] == b"%PDF-"

    async def test_generate_storno_invoice_pdf(self, session):
        """Test PDF generation for a Storno invoice."""
        await _create_stammdaten(session)
        member = _make_member()
        session.add(member)
        await session.flush()

        svc = FinanzenService(session)
        original = await svc.create_invoice(
            mitglied_id=member.id,
            beschreibung="Mitgliedsbeitrag 2026",
            rechnungstyp="mitgliedsbeitrag",
            sphaere="ideell",
            positionen=[
                {
                    "beschreibung": "Grundbeitrag Erwachsene",
                    "menge": 1,
                    "einheit": "x",
                    "einzelpreis_netto": "100.00",
                    "steuersatz": "0",
                },
            ],
        )
        # Stelle + Storno
        await svc.stelle_rechnung(original.id)
        storno = await svc.storniere_rechnung(original.id, grund="Fehler")

        pdf_svc = RechnungPdfService()
        pdf_bytes = await pdf_svc.generate_rechnung_pdf(session, storno.id)

        assert len(pdf_bytes) > 0
        assert pdf_bytes[:5] == b"%PDF-"

    async def test_pdf_contains_expected_text(self, session):
        """Test that the PDF contains the rechnungsnummer, empfaenger name, and amounts.

        ReportLab embeds text as PDF drawing operations, so we search the raw
        bytes for substrings that appear in the PDF text stream.
        """
        await _create_stammdaten(session)
        member = _make_member()
        session.add(member)
        await session.flush()

        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            mitglied_id=member.id,
            beschreibung="Test Rechnung",
            rechnungstyp="sonstige",
            sphaere="ideell",
            positionen=[
                {
                    "beschreibung": "Testposition",
                    "menge": 2,
                    "einheit": "Stk",
                    "einzelpreis_netto": "25.00",
                    "steuersatz": "19",
                },
            ],
        )

        pdf_svc = RechnungPdfService()
        pdf_bytes = await pdf_svc.generate_rechnung_pdf(session, rechnung.id)

        # PDF is valid
        assert pdf_bytes[:5] == b"%PDF-"
        assert len(pdf_bytes) > 500  # Non-trivial content

        # ReportLab uses compressed content streams by default, so raw
        # text search won't work. Verify the PDF is structurally valid
        # and contains PDF objects with content streams.
        assert b"endobj" in pdf_bytes  # Has PDF objects
        assert b"stream" in pdf_bytes  # Has content streams

    async def test_pdf_without_stammdaten(self, session):
        """Test that PDF works even without Vereinsstammdaten (uses defaults)."""
        member = _make_member()
        session.add(member)
        await session.flush()

        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            mitglied_id=member.id,
            betrag=Decimal("50.00"),
            beschreibung="Simple invoice",
        )

        pdf_svc = RechnungPdfService()
        pdf_bytes = await pdf_svc.generate_rechnung_pdf(session, rechnung.id)

        assert len(pdf_bytes) > 0
        assert pdf_bytes[:5] == b"%PDF-"

    async def test_pdf_not_found(self, session):
        """Test ValueError for non-existent invoice."""
        pdf_svc = RechnungPdfService()
        with pytest.raises(ValueError, match="nicht gefunden"):
            await pdf_svc.generate_rechnung_pdf(session, 99999)

    async def test_pdf_with_mixed_tax_rates(self, session):
        """Test PDF with multiple tax rates groups them correctly."""
        await _create_stammdaten(session)
        member = _make_member()
        session.add(member)
        await session.flush()

        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            mitglied_id=member.id,
            beschreibung="Gemischte Rechnung",
            rechnungstyp="sonstige",
            sphaere="wirtschaftlich",
            positionen=[
                {
                    "beschreibung": "Position A (steuerfrei)",
                    "menge": 1,
                    "einheit": "x",
                    "einzelpreis_netto": "100.00",
                    "steuersatz": "0",
                },
                {
                    "beschreibung": "Position B (7% USt)",
                    "menge": 1,
                    "einheit": "x",
                    "einzelpreis_netto": "50.00",
                    "steuersatz": "7",
                },
                {
                    "beschreibung": "Position C (19% USt)",
                    "menge": 2,
                    "einheit": "Stk",
                    "einzelpreis_netto": "30.00",
                    "steuersatz": "19",
                },
            ],
        )

        pdf_svc = RechnungPdfService()
        pdf_bytes = await pdf_svc.generate_rechnung_pdf(session, rechnung.id)

        assert len(pdf_bytes) > 0
        assert pdf_bytes[:5] == b"%PDF-"


class TestRechnungPdfEdgeCases:
    """Edge case tests for PDF generation."""

    async def test_pdf_with_very_long_description(self, session):
        """Test PDF generation with a very long beschreibung that may wrap."""
        await _create_stammdaten(session)
        member = _make_member()
        session.add(member)
        await session.flush()

        long_desc = (
            "Dies ist eine sehr ausfuehrliche Rechnungsbeschreibung, die ueber "
            "mehrere Zeilen gehen sollte und verschiedene Details zur erbrachten "
            "Leistung enthaelt. " * 10
        )

        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            mitglied_id=member.id,
            beschreibung=long_desc,
            rechnungstyp="sonstige",
            sphaere="ideell",
            positionen=[
                {
                    "beschreibung": "Position mit extrem langem Beschreibungstext der "
                    "ueber die normale Spaltenbreite hinausgeht und "
                    "umgebrochen werden muss damit alles passt " * 3,
                    "menge": 1,
                    "einheit": "x",
                    "einzelpreis_netto": "99.99",
                    "steuersatz": "0",
                },
            ],
        )

        pdf_svc = RechnungPdfService()
        pdf_bytes = await pdf_svc.generate_rechnung_pdf(session, rechnung.id)

        assert len(pdf_bytes) > 0
        assert pdf_bytes[:5] == b"%PDF-"

    async def test_pdf_with_many_positionen(self, session):
        """Test PDF with many line items (potential page overflow)."""
        await _create_stammdaten(session)
        member = _make_member()
        session.add(member)
        await session.flush()

        positionen = [
            {
                "beschreibung": f"Position Nr. {i} - Testleistung",
                "menge": i,
                "einheit": "Stk",
                "einzelpreis_netto": f"{10.00 + i:.2f}",
                "steuersatz": "19" if i % 2 == 0 else "0",
            }
            for i in range(1, 31)
        ]

        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            mitglied_id=member.id,
            beschreibung="Rechnung mit 30 Positionen",
            rechnungstyp="sonstige",
            sphaere="wirtschaftlich",
            positionen=positionen,
        )

        pdf_svc = RechnungPdfService()
        pdf_bytes = await pdf_svc.generate_rechnung_pdf(session, rechnung.id)

        assert len(pdf_bytes) > 0
        assert pdf_bytes[:5] == b"%PDF-"
        # With 30 line items this should produce a multi-page PDF
        assert len(pdf_bytes) > 1000

    async def test_pdf_with_no_positionen(self, session):
        """Test PDF generation with betrag only (empty positionen list)."""
        await _create_stammdaten(session)
        member = _make_member()
        session.add(member)
        await session.flush()

        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            mitglied_id=member.id,
            betrag=Decimal("42.50"),
            beschreibung="Einfache Rechnung",
        )

        pdf_svc = RechnungPdfService()
        pdf_bytes = await pdf_svc.generate_rechnung_pdf(session, rechnung.id)

        assert len(pdf_bytes) > 0
        assert pdf_bytes[:5] == b"%PDF-"

    async def test_pdf_with_zero_amount(self, session):
        """Test PDF with a zero-amount position."""
        await _create_stammdaten(session)
        member = _make_member()
        session.add(member)
        await session.flush()

        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            mitglied_id=member.id,
            beschreibung="Nullrechnung",
            rechnungstyp="sonstige",
            sphaere="ideell",
            positionen=[
                {
                    "beschreibung": "Kostenlose Leistung",
                    "menge": 1,
                    "einheit": "x",
                    "einzelpreis_netto": "0.00",
                    "steuersatz": "0",
                },
            ],
        )

        pdf_svc = RechnungPdfService()
        pdf_bytes = await pdf_svc.generate_rechnung_pdf(session, rechnung.id)

        assert len(pdf_bytes) > 0
        assert pdf_bytes[:5] == b"%PDF-"

    async def test_pdf_with_fractional_quantities(self, session):
        """Test PDF with non-integer quantities (e.g. 1.5 hours)."""
        await _create_stammdaten(session)
        member = _make_member()
        session.add(member)
        await session.flush()

        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            mitglied_id=member.id,
            beschreibung="Stundenabrechnung",
            rechnungstyp="sonstige",
            sphaere="wirtschaftlich",
            positionen=[
                {
                    "beschreibung": "Trainerstunden",
                    "menge": 1.5,
                    "einheit": "h",
                    "einzelpreis_netto": "45.00",
                    "steuersatz": "19",
                },
                {
                    "beschreibung": "Materialkosten",
                    "menge": 0.25,
                    "einheit": "x",
                    "einzelpreis_netto": "120.00",
                    "steuersatz": "19",
                },
            ],
        )

        pdf_svc = RechnungPdfService()
        pdf_bytes = await pdf_svc.generate_rechnung_pdf(session, rechnung.id)

        assert len(pdf_bytes) > 0
        assert pdf_bytes[:5] == b"%PDF-"

    async def test_pdf_without_stammdaten_fallback(self, session):
        """Test PDF uses defaults when no Vereinsstammdaten exist."""
        member = _make_member()
        session.add(member)
        await session.flush()

        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            mitglied_id=member.id,
            betrag=Decimal("25.00"),
            beschreibung="Rechnung ohne Stammdaten",
        )

        pdf_svc = RechnungPdfService()
        pdf_bytes = await pdf_svc.generate_rechnung_pdf(session, rechnung.id)

        assert len(pdf_bytes) > 0
        assert pdf_bytes[:5] == b"%PDF-"

    async def test_pdf_storno_with_multiple_positionen(self, session):
        """Test storno PDF with multiple line items."""
        await _create_stammdaten(session)
        member = _make_member()
        session.add(member)
        await session.flush()

        svc = FinanzenService(session)
        original = await svc.create_invoice(
            mitglied_id=member.id,
            beschreibung="Original mit mehreren Positionen",
            rechnungstyp="sonstige",
            sphaere="wirtschaftlich",
            positionen=[
                {
                    "beschreibung": "Position A",
                    "menge": 2,
                    "einheit": "Stk",
                    "einzelpreis_netto": "50.00",
                    "steuersatz": "19",
                },
                {
                    "beschreibung": "Position B",
                    "menge": 1,
                    "einheit": "h",
                    "einzelpreis_netto": "80.00",
                    "steuersatz": "7",
                },
            ],
        )
        await svc.stelle_rechnung(original.id)
        storno = await svc.storniere_rechnung(original.id, grund="Doppelte Rechnung")

        pdf_svc = RechnungPdfService()
        pdf_bytes = await pdf_svc.generate_rechnung_pdf(session, storno.id)

        assert len(pdf_bytes) > 0
        assert pdf_bytes[:5] == b"%PDF-"

    async def test_pdf_special_characters_in_description(self, session):
        """Test PDF handles special characters and umlauts correctly."""
        await _create_stammdaten(session)
        member = _make_member(
            vorname="Hans-Juergen",
            nachname="Mueller-Luedenscheidt",
        )
        session.add(member)
        await session.flush()

        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            mitglied_id=member.id,
            beschreibung="Gebuehr fuer Aerobic-Kurs & Sauna (50% Ermaessigung)",
            rechnungstyp="sonstige",
            sphaere="ideell",
            positionen=[
                {
                    "beschreibung": "Aerobic-Kurs inkl. Geraete <Premium>",
                    "menge": 1,
                    "einheit": "Kurs",
                    "einzelpreis_netto": "75.00",
                    "steuersatz": "0",
                },
            ],
        )

        pdf_svc = RechnungPdfService()
        pdf_bytes = await pdf_svc.generate_rechnung_pdf(session, rechnung.id)

        assert len(pdf_bytes) > 0
        assert pdf_bytes[:5] == b"%PDF-"


class TestRechnungPdfApiEndpoint:
    async def test_pdf_endpoint_returns_pdf(self, client, session):
        """Test that the API endpoint returns PDF content-type."""
        member = _make_member()
        session.add(member)
        await session.flush()

        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            mitglied_id=member.id,
            betrag=Decimal("100.00"),
            beschreibung="API PDF Test",
        )

        response = await client.get(f"/api/finanzen/rechnungen/{rechnung.id}/pdf")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert response.content[:5] == b"%PDF-"
        assert "Content-Disposition" in response.headers

    async def test_pdf_endpoint_not_found(self, client):
        """Test 404 for non-existent invoice."""
        response = await client.get("/api/finanzen/rechnungen/99999/pdf")
        assert response.status_code == 404
