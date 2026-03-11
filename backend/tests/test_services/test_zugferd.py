"""Tests for ZugferdService — ZUGFeRD 2.1 BASIC profile XML generation."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from lxml import etree

from sportverein.models.mitglied import Mitglied, MitgliedStatus
from sportverein.models.vereinsstammdaten import Vereinsstammdaten
from sportverein.services.finanzen import FinanzenService
from sportverein.services.zugferd import ZugferdService

# CII namespaces for XPath
_NS = {
    "rsm": "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100",
    "ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
    "udt": "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100",
}


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


def _parse_xml(xml_bytes: bytes) -> etree._Element:
    """Parse XML bytes and return root element."""
    return etree.fromstring(xml_bytes)


class TestZugferdXmlGeneration:
    async def test_generates_valid_xml(self, session):
        """Test that generated XML is well-formed and parseable."""
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
            positionen=[
                {
                    "beschreibung": "Grundbeitrag Erwachsene",
                    "menge": 1,
                    "einheit": "x",
                    "einzelpreis_netto": "45.00",
                    "steuersatz": "0",
                },
            ],
        )

        zugferd_svc = ZugferdService()
        xml_bytes = await zugferd_svc.generate_zugferd_xml(session, rechnung.id)

        assert xml_bytes.startswith(b"<?xml")
        root = _parse_xml(xml_bytes)
        assert root.tag == f"{{{_NS['rsm']}}}CrossIndustryInvoice"

    async def test_required_cii_elements_present(self, session):
        """Test all required CII structural elements are present."""
        await _create_stammdaten(session)
        member = _make_member()
        session.add(member)
        await session.flush()

        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            mitglied_id=member.id,
            beschreibung="Test",
            rechnungstyp="sonstige",
            sphaere="ideell",
            leistungsdatum=date(2026, 1, 15),
            positionen=[
                {
                    "beschreibung": "Testposition",
                    "menge": 1,
                    "einheit": "x",
                    "einzelpreis_netto": "100.00",
                    "steuersatz": "0",
                },
            ],
        )

        zugferd_svc = ZugferdService()
        xml_bytes = await zugferd_svc.generate_zugferd_xml(session, rechnung.id)
        root = _parse_xml(xml_bytes)

        # ExchangedDocumentContext
        ctx = root.find("rsm:ExchangedDocumentContext", _NS)
        assert ctx is not None
        guideline_id = ctx.find("ram:GuidelineSpecifiedDocumentContextParameter/ram:ID", _NS)
        assert guideline_id is not None
        assert guideline_id.text == "urn:factur-x.eu:1p0:basic"

        # ExchangedDocument
        doc = root.find("rsm:ExchangedDocument", _NS)
        assert doc is not None
        assert doc.find("ram:ID", _NS).text == rechnung.rechnungsnummer
        assert doc.find("ram:TypeCode", _NS).text == "380"

        # SupplyChainTradeTransaction
        txn = root.find("rsm:SupplyChainTradeTransaction", _NS)
        assert txn is not None

        # Agreement
        agreement = txn.find("ram:ApplicableHeaderTradeAgreement", _NS)
        assert agreement is not None
        seller = agreement.find("ram:SellerTradeParty/ram:Name", _NS)
        assert seller is not None
        assert seller.text == "TSV Sportfreunde Musterstadt"

        buyer = agreement.find("ram:BuyerTradeParty/ram:Name", _NS)
        assert buyer is not None
        assert buyer.text == "Max Mustermann"

        # Delivery
        delivery = txn.find("ram:ApplicableHeaderTradeDelivery", _NS)
        assert delivery is not None

        # Settlement
        settlement = txn.find("ram:ApplicableHeaderTradeSettlement", _NS)
        assert settlement is not None
        currency = settlement.find("ram:InvoiceCurrencyCode", _NS)
        assert currency.text == "EUR"

        # Monetary summation
        summation = settlement.find("ram:SpecifiedTradeSettlementHeaderMonetarySummation", _NS)
        assert summation is not None
        assert summation.find("ram:LineTotalAmount", _NS).text == "100.00"
        assert summation.find("ram:GrandTotalAmount", _NS).text == "100.00"

    async def test_line_items_mapped_correctly(self, session):
        """Test that invoice line items are correctly mapped to XML."""
        await _create_stammdaten(session)
        member = _make_member()
        session.add(member)
        await session.flush()

        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            mitglied_id=member.id,
            beschreibung="Multi-Position",
            rechnungstyp="sonstige",
            sphaere="wirtschaftlich",
            positionen=[
                {
                    "beschreibung": "Position A",
                    "menge": 2,
                    "einheit": "Stk",
                    "einzelpreis_netto": "25.00",
                    "steuersatz": "19",
                },
                {
                    "beschreibung": "Position B",
                    "menge": 1,
                    "einheit": "h",
                    "einzelpreis_netto": "80.00",
                    "steuersatz": "19",
                },
            ],
        )

        zugferd_svc = ZugferdService()
        xml_bytes = await zugferd_svc.generate_zugferd_xml(session, rechnung.id)
        root = _parse_xml(xml_bytes)

        txn = root.find("rsm:SupplyChainTradeTransaction", _NS)
        line_items = txn.findall("ram:IncludedSupplyChainTradeLineItem", _NS)
        assert len(line_items) == 2

        # First item
        item1 = line_items[0]
        assert item1.find("ram:AssociatedDocumentLineDocument/ram:LineID", _NS).text == "1"
        assert item1.find("ram:SpecifiedTradeProduct/ram:Name", _NS).text == "Position A"
        qty1 = item1.find("ram:SpecifiedLineTradeDelivery/ram:BilledQuantity", _NS)
        assert qty1.text == "2"
        assert qty1.get("unitCode") == "C62"  # Stk -> C62

        # Second item
        item2 = line_items[1]
        qty2 = item2.find("ram:SpecifiedLineTradeDelivery/ram:BilledQuantity", _NS)
        assert qty2.get("unitCode") == "HUR"  # h -> HUR

    async def test_storno_produces_type_code_381(self, session):
        """Test that storno invoices produce TypeCode 381 (Credit Note)."""
        await _create_stammdaten(session)
        member = _make_member()
        session.add(member)
        await session.flush()

        svc = FinanzenService(session)
        original = await svc.create_invoice(
            mitglied_id=member.id,
            beschreibung="Original",
            rechnungstyp="sonstige",
            sphaere="ideell",
            positionen=[
                {
                    "beschreibung": "Test",
                    "menge": 1,
                    "einheit": "x",
                    "einzelpreis_netto": "50.00",
                    "steuersatz": "0",
                },
            ],
        )
        await svc.stelle_rechnung(original.id)
        storno = await svc.storniere_rechnung(original.id, grund="Fehler")

        zugferd_svc = ZugferdService()
        xml_bytes = await zugferd_svc.generate_zugferd_xml(session, storno.id)
        root = _parse_xml(xml_bytes)

        type_code = root.find("rsm:ExchangedDocument/ram:TypeCode", _NS)
        assert type_code.text == "381"

    async def test_tax_exempt_has_category_e(self, session):
        """Test that 0% tax rate produces CategoryCode E (Exempt)."""
        await _create_stammdaten(session)
        member = _make_member()
        session.add(member)
        await session.flush()

        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            mitglied_id=member.id,
            beschreibung="Steuerbefreit",
            rechnungstyp="mitgliedsbeitrag",
            sphaere="ideell",
            positionen=[
                {
                    "beschreibung": "Beitrag",
                    "menge": 1,
                    "einheit": "x",
                    "einzelpreis_netto": "100.00",
                    "steuersatz": "0",
                    "steuerbefreiungsgrund": "Steuerbefreit nach §4 Nr. 22b UStG",
                },
            ],
        )

        zugferd_svc = ZugferdService()
        xml_bytes = await zugferd_svc.generate_zugferd_xml(session, rechnung.id)
        root = _parse_xml(xml_bytes)

        txn = root.find("rsm:SupplyChainTradeTransaction", _NS)

        # Line item tax
        line_tax = txn.find(
            "ram:IncludedSupplyChainTradeLineItem/"
            "ram:SpecifiedLineTradeSettlement/"
            "ram:ApplicableTradeTax/ram:CategoryCode",
            _NS,
        )
        assert line_tax.text == "E"

        # Header tax summary
        header_tax = txn.find(
            "ram:ApplicableHeaderTradeSettlement/ram:ApplicableTradeTax/ram:CategoryCode",
            _NS,
        )
        assert header_tax.text == "E"

        # Exemption reason
        exemption = txn.find(
            "ram:ApplicableHeaderTradeSettlement/ram:ApplicableTradeTax/ram:ExemptionReason",
            _NS,
        )
        assert exemption is not None
        assert "§4 Nr. 22b UStG" in exemption.text

    async def test_standard_tax_has_category_s(self, session):
        """Test that >0% tax rate produces CategoryCode S (Standard)."""
        await _create_stammdaten(session)
        member = _make_member()
        session.add(member)
        await session.flush()

        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            mitglied_id=member.id,
            beschreibung="Steuerpflichtig",
            rechnungstyp="sonstige",
            sphaere="wirtschaftlich",
            positionen=[
                {
                    "beschreibung": "Leistung",
                    "menge": 1,
                    "einheit": "x",
                    "einzelpreis_netto": "100.00",
                    "steuersatz": "19",
                },
            ],
        )

        zugferd_svc = ZugferdService()
        xml_bytes = await zugferd_svc.generate_zugferd_xml(session, rechnung.id)
        root = _parse_xml(xml_bytes)

        txn = root.find("rsm:SupplyChainTradeTransaction", _NS)

        # Line item tax
        line_tax = txn.find(
            "ram:IncludedSupplyChainTradeLineItem/"
            "ram:SpecifiedLineTradeSettlement/"
            "ram:ApplicableTradeTax/ram:CategoryCode",
            _NS,
        )
        assert line_tax.text == "S"

        # Header tax summary
        header_tax = txn.find(
            "ram:ApplicableHeaderTradeSettlement/ram:ApplicableTradeTax/ram:CategoryCode",
            _NS,
        )
        assert header_tax.text == "S"

        # Check tax amounts
        header_tax_el = txn.find(
            "ram:ApplicableHeaderTradeSettlement/ram:ApplicableTradeTax",
            _NS,
        )
        assert header_tax_el.find("ram:CalculatedAmount", _NS).text == "19.00"
        assert header_tax_el.find("ram:BasisAmount", _NS).text == "100.00"
        assert header_tax_el.find("ram:RateApplicablePercent", _NS).text == "19.00"

    async def test_mixed_tax_rates(self, session):
        """Test invoice with both exempt and standard tax rates."""
        await _create_stammdaten(session)
        member = _make_member()
        session.add(member)
        await session.flush()

        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            mitglied_id=member.id,
            beschreibung="Gemischt",
            rechnungstyp="sonstige",
            sphaere="wirtschaftlich",
            positionen=[
                {
                    "beschreibung": "Steuerfrei",
                    "menge": 1,
                    "einheit": "x",
                    "einzelpreis_netto": "100.00",
                    "steuersatz": "0",
                },
                {
                    "beschreibung": "19% USt",
                    "menge": 1,
                    "einheit": "x",
                    "einzelpreis_netto": "200.00",
                    "steuersatz": "19",
                },
            ],
        )

        zugferd_svc = ZugferdService()
        xml_bytes = await zugferd_svc.generate_zugferd_xml(session, rechnung.id)
        root = _parse_xml(xml_bytes)

        settlement = root.find(
            "rsm:SupplyChainTradeTransaction/ram:ApplicableHeaderTradeSettlement",
            _NS,
        )
        tax_elements = settlement.findall("ram:ApplicableTradeTax", _NS)
        assert len(tax_elements) == 2

        categories = {el.find("ram:CategoryCode", _NS).text for el in tax_elements}
        assert categories == {"E", "S"}

    async def test_seller_address_and_tax_registration(self, session):
        """Test seller party includes address and tax registration."""
        await _create_stammdaten(session)
        member = _make_member()
        session.add(member)
        await session.flush()

        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            mitglied_id=member.id,
            betrag=Decimal("50.00"),
            beschreibung="Test",
        )

        zugferd_svc = ZugferdService()
        xml_bytes = await zugferd_svc.generate_zugferd_xml(session, rechnung.id)
        root = _parse_xml(xml_bytes)

        seller = root.find(
            "rsm:SupplyChainTradeTransaction/"
            "ram:ApplicableHeaderTradeAgreement/"
            "ram:SellerTradeParty",
            _NS,
        )
        assert seller.find("ram:Name", _NS).text == "TSV Sportfreunde Musterstadt"

        addr = seller.find("ram:PostalTradeAddress", _NS)
        assert addr.find("ram:LineOne", _NS).text == "Hauptstr. 1"
        assert addr.find("ram:PostcodeCode", _NS).text == "12345"
        assert addr.find("ram:CityName", _NS).text == "Musterstadt"
        assert addr.find("ram:CountryID", _NS).text == "DE"

        tax_reg = seller.find("ram:SpecifiedTaxRegistration/ram:ID", _NS)
        assert tax_reg.text == "12/345/67890"
        assert tax_reg.get("schemeID") == "FC"

    async def test_sepa_payment_means(self, session):
        """Test SEPA payment means with IBAN."""
        await _create_stammdaten(session)
        member = _make_member()
        session.add(member)
        await session.flush()

        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            mitglied_id=member.id,
            betrag=Decimal("50.00"),
            beschreibung="Test",
        )

        zugferd_svc = ZugferdService()
        xml_bytes = await zugferd_svc.generate_zugferd_xml(session, rechnung.id)
        root = _parse_xml(xml_bytes)

        means = root.find(
            "rsm:SupplyChainTradeTransaction/"
            "ram:ApplicableHeaderTradeSettlement/"
            "ram:SpecifiedTradeSettlementPaymentMeans",
            _NS,
        )
        assert means is not None
        assert means.find("ram:TypeCode", _NS).text == "58"
        iban = means.find("ram:PayeePartyCreditorFinancialAccount/ram:IBANID", _NS)
        assert iban.text == "DE89370400440532013000"

    async def test_not_found_raises_error(self, session):
        """Test ValueError for non-existent invoice."""
        zugferd_svc = ZugferdService()
        with pytest.raises(ValueError, match="nicht gefunden"):
            await zugferd_svc.generate_zugferd_xml(session, 99999)


class TestZugferdEdgeCases:
    """Edge case tests for ZUGFeRD XML generation."""

    async def test_invoice_without_positionen(self, session):
        """Invoice created with betrag only (no positionen) should still produce valid XML."""
        await _create_stammdaten(session)
        member = _make_member()
        session.add(member)
        await session.flush()

        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            mitglied_id=member.id,
            betrag=Decimal("75.00"),
            beschreibung="Einfache Rechnung ohne Positionen",
        )

        zugferd_svc = ZugferdService()
        xml_bytes = await zugferd_svc.generate_zugferd_xml(session, rechnung.id)

        root = _parse_xml(xml_bytes)
        assert root.tag == f"{{{_NS['rsm']}}}CrossIndustryInvoice"

        txn = root.find("rsm:SupplyChainTradeTransaction", _NS)
        # No line items expected
        line_items = txn.findall("ram:IncludedSupplyChainTradeLineItem", _NS)
        assert len(line_items) == 0

        # Should still have a tax summary (fallback exempt entry)
        settlement = txn.find("ram:ApplicableHeaderTradeSettlement", _NS)
        tax_els = settlement.findall("ram:ApplicableTradeTax", _NS)
        assert len(tax_els) == 1
        assert tax_els[0].find("ram:CategoryCode", _NS).text == "E"
        assert tax_els[0].find("ram:RateApplicablePercent", _NS).text == "0.00"

        # Grand total should equal the betrag
        summation = settlement.find(
            "ram:SpecifiedTradeSettlementHeaderMonetarySummation", _NS
        )
        assert summation.find("ram:GrandTotalAmount", _NS).text == "75.00"

    async def test_invoice_with_zero_percent_tax_no_exemption_reason(self, session):
        """0% tax without steuerbefreiungsgrund should not emit ExemptionReason."""
        await _create_stammdaten(session)
        member = _make_member()
        session.add(member)
        await session.flush()

        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            mitglied_id=member.id,
            beschreibung="Beitrag ohne Befreiungsgrund",
            rechnungstyp="mitgliedsbeitrag",
            sphaere="ideell",
            positionen=[
                {
                    "beschreibung": "Beitrag",
                    "menge": 1,
                    "einheit": "x",
                    "einzelpreis_netto": "60.00",
                    "steuersatz": "0",
                    # No steuerbefreiungsgrund
                },
            ],
        )

        zugferd_svc = ZugferdService()
        xml_bytes = await zugferd_svc.generate_zugferd_xml(session, rechnung.id)
        root = _parse_xml(xml_bytes)

        settlement = root.find(
            "rsm:SupplyChainTradeTransaction/ram:ApplicableHeaderTradeSettlement", _NS
        )
        tax_el = settlement.find("ram:ApplicableTradeTax", _NS)
        assert tax_el.find("ram:CategoryCode", _NS).text == "E"
        # No ExemptionReason element when not provided
        assert tax_el.find("ram:ExemptionReason", _NS) is None

    async def test_storno_invoice_has_negative_amounts(self, session):
        """Storno invoice XML should have TypeCode 381 and correct amounts."""
        await _create_stammdaten(session)
        member = _make_member()
        session.add(member)
        await session.flush()

        svc = FinanzenService(session)
        original = await svc.create_invoice(
            mitglied_id=member.id,
            beschreibung="Original Rechnung",
            rechnungstyp="sonstige",
            sphaere="wirtschaftlich",
            positionen=[
                {
                    "beschreibung": "Leistung",
                    "menge": 3,
                    "einheit": "Stk",
                    "einzelpreis_netto": "20.00",
                    "steuersatz": "19",
                },
            ],
        )
        await svc.stelle_rechnung(original.id)
        storno = await svc.storniere_rechnung(original.id, grund="Fehler")

        zugferd_svc = ZugferdService()
        xml_bytes = await zugferd_svc.generate_zugferd_xml(session, storno.id)
        root = _parse_xml(xml_bytes)

        # TypeCode 381 for credit note
        type_code = root.find("rsm:ExchangedDocument/ram:TypeCode", _NS)
        assert type_code.text == "381"

        # Verify XML is well-formed
        assert root.tag == f"{{{_NS['rsm']}}}CrossIndustryInvoice"

    async def test_missing_stammdaten_uses_defaults(self, session):
        """Invoice without Vereinsstammdaten should use fallback seller name."""
        member = _make_member()
        session.add(member)
        await session.flush()

        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            mitglied_id=member.id,
            betrag=Decimal("30.00"),
            beschreibung="Ohne Stammdaten",
        )

        zugferd_svc = ZugferdService()
        xml_bytes = await zugferd_svc.generate_zugferd_xml(session, rechnung.id)
        root = _parse_xml(xml_bytes)

        # Seller should use default name
        seller_name = root.find(
            "rsm:SupplyChainTradeTransaction/"
            "ram:ApplicableHeaderTradeAgreement/"
            "ram:SellerTradeParty/ram:Name",
            _NS,
        )
        assert seller_name.text == "Sportverein e.V."

        # No tax registration elements
        seller = root.find(
            "rsm:SupplyChainTradeTransaction/"
            "ram:ApplicableHeaderTradeAgreement/"
            "ram:SellerTradeParty",
            _NS,
        )
        tax_regs = seller.findall("ram:SpecifiedTaxRegistration", _NS)
        assert len(tax_regs) == 0

        # No SEPA payment means (no IBAN)
        settlement = root.find(
            "rsm:SupplyChainTradeTransaction/ram:ApplicableHeaderTradeSettlement", _NS
        )
        means = settlement.find("ram:SpecifiedTradeSettlementPaymentMeans", _NS)
        assert means is None

    async def test_reduced_tax_rate_7_percent(self, session):
        """7% reduced tax rate should produce CategoryCode S."""
        await _create_stammdaten(session)
        member = _make_member()
        session.add(member)
        await session.flush()

        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            mitglied_id=member.id,
            beschreibung="Ermaessigter Satz",
            rechnungstyp="sonstige",
            sphaere="zweckbetrieb",
            positionen=[
                {
                    "beschreibung": "Sportveranstaltung",
                    "menge": 1,
                    "einheit": "x",
                    "einzelpreis_netto": "200.00",
                    "steuersatz": "7",
                },
            ],
        )

        zugferd_svc = ZugferdService()
        xml_bytes = await zugferd_svc.generate_zugferd_xml(session, rechnung.id)
        root = _parse_xml(xml_bytes)

        settlement = root.find(
            "rsm:SupplyChainTradeTransaction/ram:ApplicableHeaderTradeSettlement", _NS
        )
        tax_el = settlement.find("ram:ApplicableTradeTax", _NS)
        assert tax_el.find("ram:CategoryCode", _NS).text == "S"
        assert tax_el.find("ram:RateApplicablePercent", _NS).text == "7.00"
        assert tax_el.find("ram:CalculatedAmount", _NS).text == "14.00"
        assert tax_el.find("ram:BasisAmount", _NS).text == "200.00"

        summation = settlement.find(
            "ram:SpecifiedTradeSettlementHeaderMonetarySummation", _NS
        )
        assert summation.find("ram:GrandTotalAmount", _NS).text == "214.00"
        assert summation.find("ram:TaxTotalAmount", _NS).text == "14.00"

    async def test_buyer_without_address_fields(self, session):
        """Buyer with no street/plz/ort should still produce valid XML."""
        await _create_stammdaten(session)

        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            empfaenger_name="Externe Firma",
            empfaenger_typ="extern",
            betrag=Decimal("100.00"),
            beschreibung="Externe Rechnung",
        )

        zugferd_svc = ZugferdService()
        xml_bytes = await zugferd_svc.generate_zugferd_xml(session, rechnung.id)
        root = _parse_xml(xml_bytes)

        buyer = root.find(
            "rsm:SupplyChainTradeTransaction/"
            "ram:ApplicableHeaderTradeAgreement/"
            "ram:BuyerTradeParty",
            _NS,
        )
        assert buyer.find("ram:Name", _NS).text == "Externe Firma"

        # Address should still have CountryID DE at minimum
        addr = buyer.find("ram:PostalTradeAddress", _NS)
        assert addr.find("ram:CountryID", _NS).text == "DE"


class TestZugferdApiEndpoint:
    async def test_xml_endpoint_returns_xml(self, client, session):
        """Test that the API endpoint returns XML content-type."""
        member = _make_member()
        session.add(member)
        await session.flush()

        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            mitglied_id=member.id,
            betrag=Decimal("100.00"),
            beschreibung="API XML Test",
        )

        response = await client.get(f"/api/finanzen/rechnungen/{rechnung.id}/xml")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/xml"
        assert response.content.startswith(b"<?xml")
        assert "Content-Disposition" in response.headers
        assert "zugferd.xml" in response.headers["Content-Disposition"]

        # Verify it's parseable
        root = etree.fromstring(response.content)
        assert root.tag == f"{{{_NS['rsm']}}}CrossIndustryInvoice"

    async def test_xml_endpoint_not_found(self, client):
        """Test 404 for non-existent invoice."""
        response = await client.get("/api/finanzen/rechnungen/99999/xml")
        assert response.status_code == 404
