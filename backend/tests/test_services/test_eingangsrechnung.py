"""Tests for Eingangsrechnung (incoming e-invoice) parsing and service."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from sportverein.models.finanzen import EingangsrechnungStatus
from sportverein.services.eingangsrechnung import EingangsrechnungService

# ---------------------------------------------------------------------------
# Sample CII XML (ZUGFeRD BASIC / XRechnung)
# ---------------------------------------------------------------------------

SAMPLE_CII_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<rsm:CrossIndustryInvoice
    xmlns:rsm="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
    xmlns:ram="urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"
    xmlns:udt="urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100"
    xmlns:qdt="urn:un:unece:uncefact:data:standard:QualifiedDataType:100">
  <rsm:ExchangedDocument>
    <ram:ID>RE-2026-001</ram:ID>
    <ram:TypeCode>380</ram:TypeCode>
    <ram:IssueDateTime>
      <udt:DateTimeString format="102">20260315</udt:DateTimeString>
    </ram:IssueDateTime>
  </rsm:ExchangedDocument>
  <rsm:SupplyChainTradeTransaction>
    <ram:ApplicableHeaderTradeAgreement>
      <ram:SellerTradeParty>
        <ram:Name>Sportgeraete Mueller GmbH</ram:Name>
        <ram:PostalTradeAddress>
          <ram:PostcodeCode>80331</ram:PostcodeCode>
          <ram:LineOne>Marienplatz 1</ram:LineOne>
          <ram:CityName>Muenchen</ram:CityName>
        </ram:PostalTradeAddress>
        <ram:SpecifiedTaxRegistration>
          <ram:ID schemeID="VA">DE123456789</ram:ID>
        </ram:SpecifiedTaxRegistration>
        <ram:SpecifiedTaxRegistration>
          <ram:ID schemeID="FC">143/123/12345</ram:ID>
        </ram:SpecifiedTaxRegistration>
      </ram:SellerTradeParty>
      <ram:BuyerTradeParty>
        <ram:Name>TV Musterstadt 1900 e.V.</ram:Name>
      </ram:BuyerTradeParty>
    </ram:ApplicableHeaderTradeAgreement>
    <ram:ApplicableHeaderTradeDelivery>
      <ram:ActualDeliverySupplyChainEvent>
        <ram:OccurrenceDateTime>
          <udt:DateTimeString format="102">20260310</udt:DateTimeString>
        </ram:OccurrenceDateTime>
      </ram:ActualDeliverySupplyChainEvent>
    </ram:ApplicableHeaderTradeDelivery>
    <ram:ApplicableHeaderTradeSettlement>
      <ram:InvoiceCurrencyCode>EUR</ram:InvoiceCurrencyCode>
      <ram:SpecifiedTradePaymentTerms>
        <ram:DueDateDateTime>
          <udt:DateTimeString format="102">20260414</udt:DateTimeString>
        </ram:DueDateDateTime>
      </ram:SpecifiedTradePaymentTerms>
      <ram:SpecifiedTradeSettlementHeaderMonetarySummation>
        <ram:TaxBasisTotalAmount>1000.00</ram:TaxBasisTotalAmount>
        <ram:TaxTotalAmount>190.00</ram:TaxTotalAmount>
        <ram:GrandTotalAmount>1190.00</ram:GrandTotalAmount>
        <ram:DuePayableAmount>1190.00</ram:DuePayableAmount>
      </ram:SpecifiedTradeSettlementHeaderMonetarySummation>
    </ram:ApplicableHeaderTradeSettlement>
  </rsm:SupplyChainTradeTransaction>
</rsm:CrossIndustryInvoice>
"""

# ---------------------------------------------------------------------------
# Sample UBL XML
# ---------------------------------------------------------------------------

SAMPLE_UBL_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
  <cbc:ID>UBL-2026-042</cbc:ID>
  <cbc:IssueDate>2026-02-20</cbc:IssueDate>
  <cbc:DueDate>2026-03-20</cbc:DueDate>
  <cbc:DocumentCurrencyCode>EUR</cbc:DocumentCurrencyCode>
  <cac:AccountingSupplierParty>
    <cac:Party>
      <cac:PartyName>
        <cbc:Name>Reinigungsservice Sauber KG</cbc:Name>
      </cac:PartyName>
      <cac:PostalAddress>
        <cbc:StreetName>Hauptstrasse 42</cbc:StreetName>
        <cbc:PostalZone>60311</cbc:PostalZone>
        <cbc:CityName>Frankfurt</cbc:CityName>
      </cac:PostalAddress>
      <cac:PartyTaxScheme>
        <cbc:CompanyID>DE987654321</cbc:CompanyID>
        <cac:TaxScheme>
          <cbc:ID>VAT</cbc:ID>
        </cac:TaxScheme>
      </cac:PartyTaxScheme>
    </cac:Party>
  </cac:AccountingSupplierParty>
  <cac:TaxTotal>
    <cbc:TaxAmount currencyID="EUR">38.00</cbc:TaxAmount>
  </cac:TaxTotal>
  <cac:LegalMonetaryTotal>
    <cbc:TaxExclusiveAmount currencyID="EUR">200.00</cbc:TaxExclusiveAmount>
    <cbc:TaxInclusiveAmount currencyID="EUR">238.00</cbc:TaxInclusiveAmount>
    <cbc:PayableAmount currencyID="EUR">238.00</cbc:PayableAmount>
  </cac:LegalMonetaryTotal>
</Invoice>
"""


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------


class TestFormatDetection:
    def test_detect_cii(self):
        svc = EingangsrechnungService()
        assert svc.detect_format(SAMPLE_CII_XML) == "cii"

    def test_detect_ubl(self):
        svc = EingangsrechnungService()
        assert svc.detect_format(SAMPLE_UBL_XML) == "ubl"

    def test_detect_invalid_xml(self):
        svc = EingangsrechnungService()
        with pytest.raises(ValueError, match="Ungültiges XML"):
            svc.detect_format("<not valid xml")

    def test_detect_unknown_root(self):
        svc = EingangsrechnungService()
        with pytest.raises(ValueError, match="Unbekanntes XML-Root-Element"):
            svc.detect_format("<SomeOtherElement/>")


class TestCIIParsing:
    def test_parse_cii_rechnungsnummer(self):
        svc = EingangsrechnungService()
        result = svc.parse_xml(SAMPLE_CII_XML)
        assert result["rechnungsnummer"] == "RE-2026-001"

    def test_parse_cii_rechnungsdatum(self):
        svc = EingangsrechnungService()
        result = svc.parse_xml(SAMPLE_CII_XML)
        assert result["rechnungsdatum"] == date(2026, 3, 15)

    def test_parse_cii_seller(self):
        svc = EingangsrechnungService()
        result = svc.parse_xml(SAMPLE_CII_XML)
        assert result["aussteller_name"] == "Sportgeraete Mueller GmbH"
        assert result["aussteller_strasse"] == "Marienplatz 1"
        assert result["aussteller_plz"] == "80331"
        assert result["aussteller_ort"] == "Muenchen"

    def test_parse_cii_tax_registration(self):
        svc = EingangsrechnungService()
        result = svc.parse_xml(SAMPLE_CII_XML)
        assert result["aussteller_ust_id"] == "DE123456789"
        assert result["aussteller_steuernr"] == "143/123/12345"

    def test_parse_cii_amounts(self):
        svc = EingangsrechnungService()
        result = svc.parse_xml(SAMPLE_CII_XML)
        assert result["summe_netto"] == Decimal("1000.00")
        assert result["summe_steuer"] == Decimal("190.00")
        assert result["summe_brutto"] == Decimal("1190.00")

    def test_parse_cii_dates(self):
        svc = EingangsrechnungService()
        result = svc.parse_xml(SAMPLE_CII_XML)
        assert result["faelligkeitsdatum"] == date(2026, 4, 14)
        assert result["leistungsdatum"] == date(2026, 3, 10)

    def test_parse_cii_currency(self):
        svc = EingangsrechnungService()
        result = svc.parse_xml(SAMPLE_CII_XML)
        assert result["waehrung"] == "EUR"

    def test_parse_cii_stores_original_xml(self):
        svc = EingangsrechnungService()
        result = svc.parse_xml(SAMPLE_CII_XML)
        assert result["quell_xml"] is not None
        assert "CrossIndustryInvoice" in result["quell_xml"]


class TestUBLParsing:
    def test_parse_ubl_rechnungsnummer(self):
        svc = EingangsrechnungService()
        result = svc.parse_xml(SAMPLE_UBL_XML)
        assert result["rechnungsnummer"] == "UBL-2026-042"

    def test_parse_ubl_dates(self):
        svc = EingangsrechnungService()
        result = svc.parse_xml(SAMPLE_UBL_XML)
        assert result["rechnungsdatum"] == date(2026, 2, 20)
        assert result["faelligkeitsdatum"] == date(2026, 3, 20)

    def test_parse_ubl_seller(self):
        svc = EingangsrechnungService()
        result = svc.parse_xml(SAMPLE_UBL_XML)
        assert result["aussteller_name"] == "Reinigungsservice Sauber KG"
        assert result["aussteller_strasse"] == "Hauptstrasse 42"
        assert result["aussteller_plz"] == "60311"
        assert result["aussteller_ort"] == "Frankfurt"
        assert result["aussteller_ust_id"] == "DE987654321"

    def test_parse_ubl_amounts(self):
        svc = EingangsrechnungService()
        result = svc.parse_xml(SAMPLE_UBL_XML)
        assert result["summe_netto"] == Decimal("200.00")
        assert result["summe_steuer"] == Decimal("38.00")
        assert result["summe_brutto"] == Decimal("238.00")


class TestValidation:
    async def test_all_pflichtfelder_present(self):
        svc = EingangsrechnungService()
        parsed = svc.parse_xml(SAMPLE_CII_XML)
        missing = await svc.validate_pflichtfelder(parsed)
        assert missing == []

    async def test_missing_pflichtfelder(self):
        svc = EingangsrechnungService()
        parsed = {
            "rechnungsnummer": "",
            "aussteller_name": None,
            "rechnungsdatum": None,
            "summe_netto": None,
            "summe_brutto": None,
        }
        missing = await svc.validate_pflichtfelder(parsed)
        assert len(missing) == 5
        assert "Rechnungsnummer" in missing
        assert "Name des Ausstellers" in missing
        assert "Rechnungsdatum" in missing
        assert "Nettobetrag" in missing
        assert "Bruttobetrag" in missing

    async def test_partial_missing(self):
        svc = EingangsrechnungService()
        parsed = svc.parse_xml(SAMPLE_CII_XML)
        # Remove one field
        parsed["rechnungsnummer"] = ""
        missing = await svc.validate_pflichtfelder(parsed)
        assert len(missing) == 1
        assert "Rechnungsnummer" in missing


# ---------------------------------------------------------------------------
# Database / service tests
# ---------------------------------------------------------------------------


class TestCreateFromXml:
    async def test_create_from_cii_xml(self, session):
        svc = EingangsrechnungService(session)
        rechnung, warnings = await svc.create_from_xml(session, SAMPLE_CII_XML)

        assert rechnung.id is not None
        assert rechnung.rechnungsnummer == "RE-2026-001"
        assert rechnung.aussteller_name == "Sportgeraete Mueller GmbH"
        assert rechnung.rechnungsdatum == date(2026, 3, 15)
        assert rechnung.summe_netto == Decimal("1000.00")
        assert rechnung.summe_steuer == Decimal("190.00")
        assert rechnung.summe_brutto == Decimal("1190.00")
        assert rechnung.status == EingangsrechnungStatus.eingegangen
        assert rechnung.quell_format == "xrechnung"
        assert warnings == []

    async def test_create_from_ubl_xml(self, session):
        svc = EingangsrechnungService(session)
        rechnung, warnings = await svc.create_from_xml(session, SAMPLE_UBL_XML)

        assert rechnung.id is not None
        assert rechnung.rechnungsnummer == "UBL-2026-042"
        assert rechnung.aussteller_name == "Reinigungsservice Sauber KG"
        assert rechnung.summe_brutto == Decimal("238.00")
        assert warnings == []


class TestListEingangsrechnungen:
    async def test_list_empty(self, session):
        svc = EingangsrechnungService(session)
        items, total = await svc.list_eingangsrechnungen(session)
        assert items == []
        assert total == 0

    async def test_list_after_create(self, session):
        svc = EingangsrechnungService(session)
        await svc.create_from_xml(session, SAMPLE_CII_XML)
        await svc.create_from_xml(session, SAMPLE_UBL_XML)

        items, total = await svc.list_eingangsrechnungen(session)
        assert total == 2
        assert len(items) == 2

    async def test_filter_by_status(self, session):
        svc = EingangsrechnungService(session)
        rechnung, _ = await svc.create_from_xml(session, SAMPLE_CII_XML)
        await svc.create_from_xml(session, SAMPLE_UBL_XML)

        # Update one to geprueft
        await svc.update_status(session, rechnung.id, "geprueft")

        items, total = await svc.list_eingangsrechnungen(session, filters={"status": "geprueft"})
        assert total == 1
        assert items[0].rechnungsnummer == "RE-2026-001"


class TestUpdateStatus:
    async def test_update_to_geprueft(self, session):
        svc = EingangsrechnungService(session)
        rechnung, _ = await svc.create_from_xml(session, SAMPLE_CII_XML)

        updated = await svc.update_status(session, rechnung.id, "geprueft")
        assert updated.status == EingangsrechnungStatus.geprueft

    async def test_update_with_notiz(self, session):
        svc = EingangsrechnungService(session)
        rechnung, _ = await svc.create_from_xml(session, SAMPLE_CII_XML)

        updated = await svc.update_status(
            session, rechnung.id, "freigegeben", notiz="Vom Vorstand freigegeben"
        )
        assert updated.status == EingangsrechnungStatus.freigegeben
        assert updated.notiz == "Vom Vorstand freigegeben"

    async def test_invalid_status(self, session):
        svc = EingangsrechnungService(session)
        rechnung, _ = await svc.create_from_xml(session, SAMPLE_CII_XML)

        with pytest.raises(ValueError, match="Ungültiger Status"):
            await svc.update_status(session, rechnung.id, "ungueltig")

    async def test_not_found(self, session):
        svc = EingangsrechnungService(session)
        with pytest.raises(ValueError, match="nicht gefunden"):
            await svc.update_status(session, 9999, "geprueft")


# ---------------------------------------------------------------------------
# API tests
# ---------------------------------------------------------------------------


class TestApiUpload:
    async def test_upload_cii_xml(self, client):
        response = await client.post(
            "/api/finanzen/eingangsrechnungen/upload",
            files={"file": ("invoice.xml", SAMPLE_CII_XML.encode(), "application/xml")},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["rechnung"]["rechnungsnummer"] == "RE-2026-001"
        assert data["rechnung"]["aussteller_name"] == "Sportgeraete Mueller GmbH"
        assert data["warnungen"] == []

    async def test_upload_invalid_xml(self, client):
        response = await client.post(
            "/api/finanzen/eingangsrechnungen/upload",
            files={"file": ("bad.xml", b"<not valid xml", "application/xml")},
        )
        assert response.status_code == 400


class TestApiList:
    async def test_list_empty(self, client):
        response = await client.get("/api/finanzen/eingangsrechnungen")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    async def test_list_after_upload(self, client):
        # Upload first
        await client.post(
            "/api/finanzen/eingangsrechnungen/upload",
            files={"file": ("invoice.xml", SAMPLE_CII_XML.encode(), "application/xml")},
        )
        response = await client.get("/api/finanzen/eingangsrechnungen")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1


class TestApiDetail:
    async def test_get_detail(self, client):
        upload = await client.post(
            "/api/finanzen/eingangsrechnungen/upload",
            files={"file": ("invoice.xml", SAMPLE_CII_XML.encode(), "application/xml")},
        )
        rechnung_id = upload.json()["rechnung"]["id"]

        response = await client.get(f"/api/finanzen/eingangsrechnungen/{rechnung_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["rechnungsnummer"] == "RE-2026-001"
        assert data["quell_xml"] is not None

    async def test_get_not_found(self, client):
        response = await client.get("/api/finanzen/eingangsrechnungen/9999")
        assert response.status_code == 404


class TestApiStatusUpdate:
    async def test_update_status(self, client):
        upload = await client.post(
            "/api/finanzen/eingangsrechnungen/upload",
            files={"file": ("invoice.xml", SAMPLE_CII_XML.encode(), "application/xml")},
        )
        rechnung_id = upload.json()["rechnung"]["id"]

        response = await client.put(
            f"/api/finanzen/eingangsrechnungen/{rechnung_id}/status",
            json={"status": "geprueft", "notiz": "Sieht gut aus"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "geprueft"

    async def test_update_invalid_status(self, client):
        upload = await client.post(
            "/api/finanzen/eingangsrechnungen/upload",
            files={"file": ("invoice.xml", SAMPLE_CII_XML.encode(), "application/xml")},
        )
        rechnung_id = upload.json()["rechnung"]["id"]

        response = await client.put(
            f"/api/finanzen/eingangsrechnungen/{rechnung_id}/status",
            json={"status": "ungueltig"},
        )
        assert response.status_code == 400
