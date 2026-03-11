"""Tests for MCP incoming invoice tools (Eingangsrechnung)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from sportverein.models.base import Base

# Register all models
import sportverein.models  # noqa: F401

from sportverein.mcp.session import set_session_factory
from sportverein.mcp.tools_beitraege import (
    eingangsrechnung_status_aendern,
    eingangsrechnungen_auflisten,
)
from sportverein.mcp.tools_eingangsrechnung import eingangsrechnung_pruefen
from sportverein.models.finanzen import Eingangsrechnung, EingangsrechnungStatus


# ---------------------------------------------------------------------------
# XML fixtures
# ---------------------------------------------------------------------------

VALID_CII_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<rsm:CrossIndustryInvoice
  xmlns:rsm="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
  xmlns:ram="urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"
  xmlns:udt="urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100">
  <rsm:ExchangedDocument>
    <ram:ID>RE-2026-0001</ram:ID>
    <ram:IssueDateTime>
      <udt:DateTimeString format="102">20260301</udt:DateTimeString>
    </ram:IssueDateTime>
  </rsm:ExchangedDocument>
  <rsm:SupplyChainTradeTransaction>
    <ram:ApplicableHeaderTradeAgreement>
      <ram:SellerTradeParty>
        <ram:Name>Sportartikel GmbH</ram:Name>
        <ram:PostalTradeAddress>
          <ram:LineOne>Hauptstr. 1</ram:LineOne>
          <ram:PostcodeCode>10115</ram:PostcodeCode>
          <ram:CityName>Berlin</ram:CityName>
        </ram:PostalTradeAddress>
        <ram:SpecifiedTaxRegistration>
          <ram:ID schemeID="VA">DE123456789</ram:ID>
        </ram:SpecifiedTaxRegistration>
      </ram:SellerTradeParty>
    </ram:ApplicableHeaderTradeAgreement>
    <ram:ApplicableHeaderTradeSettlement>
      <ram:InvoiceCurrencyCode>EUR</ram:InvoiceCurrencyCode>
      <ram:SpecifiedTradeSettlementHeaderMonetarySummation>
        <ram:TaxBasisTotalAmount>100.00</ram:TaxBasisTotalAmount>
        <ram:TaxTotalAmount>19.00</ram:TaxTotalAmount>
        <ram:GrandTotalAmount>119.00</ram:GrandTotalAmount>
      </ram:SpecifiedTradeSettlementHeaderMonetarySummation>
    </ram:ApplicableHeaderTradeSettlement>
  </rsm:SupplyChainTradeTransaction>
</rsm:CrossIndustryInvoice>
"""

VALID_UBL_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
  <cbc:ID>UBL-2026-0042</cbc:ID>
  <cbc:IssueDate>2026-02-15</cbc:IssueDate>
  <cbc:DueDate>2026-03-15</cbc:DueDate>
  <cbc:DocumentCurrencyCode>EUR</cbc:DocumentCurrencyCode>
  <cac:AccountingSupplierParty>
    <cac:Party>
      <cac:PartyName>
        <cbc:Name>Buero-Service AG</cbc:Name>
      </cac:PartyName>
      <cac:PostalAddress>
        <cbc:StreetName>Musterweg 5</cbc:StreetName>
        <cbc:PostalZone>80331</cbc:PostalZone>
        <cbc:CityName>Muenchen</cbc:CityName>
      </cac:PostalAddress>
      <cac:PartyTaxScheme>
        <cbc:CompanyID>DE987654321</cbc:CompanyID>
      </cac:PartyTaxScheme>
    </cac:Party>
  </cac:AccountingSupplierParty>
  <cac:LegalMonetaryTotal>
    <cbc:TaxExclusiveAmount currencyID="EUR">200.00</cbc:TaxExclusiveAmount>
    <cbc:TaxInclusiveAmount currencyID="EUR">238.00</cbc:TaxInclusiveAmount>
  </cac:LegalMonetaryTotal>
  <cac:TaxTotal>
    <cbc:TaxAmount currencyID="EUR">38.00</cbc:TaxAmount>
  </cac:TaxTotal>
</Invoice>
"""

MINIMAL_CII_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<rsm:CrossIndustryInvoice
  xmlns:rsm="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
  xmlns:ram="urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"
  xmlns:udt="urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100">
  <rsm:ExchangedDocument>
    <ram:ID></ram:ID>
  </rsm:ExchangedDocument>
  <rsm:SupplyChainTradeTransaction>
    <ram:ApplicableHeaderTradeAgreement/>
    <ram:ApplicableHeaderTradeSettlement>
      <ram:SpecifiedTradeSettlementHeaderMonetarySummation/>
    </ram:ApplicableHeaderTradeSettlement>
  </rsm:SupplyChainTradeTransaction>
</rsm:CrossIndustryInvoice>
"""

INVALID_XML = "this is not xml at all <<<"

UNKNOWN_ROOT_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<UnknownDocument xmlns="urn:example:unknown">
  <ID>123</ID>
</UnknownDocument>
"""


# ---------------------------------------------------------------------------
# DB fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture()
async def mcp_engine():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture()
async def mcp_session_factory(mcp_engine):
    factory = async_sessionmaker(mcp_engine, class_=AsyncSession, expire_on_commit=False)
    set_session_factory(factory)
    yield factory
    set_session_factory(None)


@pytest_asyncio.fixture()
async def mcp_session(mcp_session_factory):
    async with mcp_session_factory() as session:
        yield session


@pytest_asyncio.fixture()
async def seed_eingangsrechnungen(mcp_session: AsyncSession):
    """Create sample incoming invoices."""
    rechnungen = [
        Eingangsrechnung(
            rechnungsnummer="ER-001",
            aussteller_name="Lieferant A",
            rechnungsdatum=date(2026, 1, 15),
            summe_netto=Decimal("100.00"),
            summe_steuer=Decimal("19.00"),
            summe_brutto=Decimal("119.00"),
            status=EingangsrechnungStatus.eingegangen,
        ),
        Eingangsrechnung(
            rechnungsnummer="ER-002",
            aussteller_name="Lieferant B",
            rechnungsdatum=date(2026, 2, 10),
            summe_netto=Decimal("500.00"),
            summe_steuer=Decimal("95.00"),
            summe_brutto=Decimal("595.00"),
            status=EingangsrechnungStatus.geprueft,
        ),
        Eingangsrechnung(
            rechnungsnummer="ER-003",
            aussteller_name="Lieferant C",
            rechnungsdatum=date(2026, 3, 1),
            summe_netto=Decimal("250.00"),
            summe_steuer=Decimal("47.50"),
            summe_brutto=Decimal("297.50"),
            status=EingangsrechnungStatus.bezahlt,
        ),
    ]
    for r in rechnungen:
        mcp_session.add(r)
    await mcp_session.commit()
    for r in rechnungen:
        await mcp_session.refresh(r)
    return rechnungen


# ===================================================================
# eingangsrechnung_pruefen (XML parsing tool)
# ===================================================================


class TestEingangsrechnungPruefen:
    """Tests for the eingangsrechnung_pruefen MCP tool."""

    @pytest.mark.asyncio
    async def test_valid_cii_invoice(self):
        result = await eingangsrechnung_pruefen(VALID_CII_XML)
        assert result["erfolg"] is True
        assert result["pflichtfelder_vollstaendig"] is True
        assert result["warnungen"] == []
        daten = result["daten"]
        assert daten["rechnungsnummer"] == "RE-2026-0001"
        assert daten["aussteller_name"] == "Sportartikel GmbH"
        assert str(daten["summe_netto"]) == "100.00"
        assert str(daten["summe_brutto"]) == "119.00"
        assert str(daten["summe_steuer"]) == "19.00"

    @pytest.mark.asyncio
    async def test_valid_ubl_invoice(self):
        result = await eingangsrechnung_pruefen(VALID_UBL_XML)
        assert result["erfolg"] is True
        assert result["pflichtfelder_vollstaendig"] is True
        daten = result["daten"]
        assert daten["rechnungsnummer"] == "UBL-2026-0042"
        assert daten["aussteller_name"] == "Buero-Service AG"
        assert str(daten["summe_netto"]) == "200.00"
        assert str(daten["summe_brutto"]) == "238.00"

    @pytest.mark.asyncio
    async def test_invalid_xml(self):
        result = await eingangsrechnung_pruefen(INVALID_XML)
        assert result["erfolg"] is False
        assert "fehler" in result

    @pytest.mark.asyncio
    async def test_unknown_root_element(self):
        result = await eingangsrechnung_pruefen(UNKNOWN_ROOT_XML)
        assert result["erfolg"] is False
        assert "fehler" in result

    @pytest.mark.asyncio
    async def test_minimal_cii_missing_fields(self):
        """Minimal CII XML should parse but report missing Pflichtfelder."""
        result = await eingangsrechnung_pruefen(MINIMAL_CII_XML)
        assert result["erfolg"] is True
        assert result["pflichtfelder_vollstaendig"] is False
        assert len(result["warnungen"]) > 0

    @pytest.mark.asyncio
    async def test_quell_xml_not_in_output(self):
        """The quell_xml field should be stripped from the result."""
        result = await eingangsrechnung_pruefen(VALID_CII_XML)
        assert "quell_xml" not in result.get("daten", {})

    @pytest.mark.asyncio
    async def test_cii_seller_address_extracted(self):
        result = await eingangsrechnung_pruefen(VALID_CII_XML)
        daten = result["daten"]
        assert daten.get("aussteller_strasse") == "Hauptstr. 1"
        assert daten.get("aussteller_plz") == "10115"
        assert daten.get("aussteller_ort") == "Berlin"

    @pytest.mark.asyncio
    async def test_cii_tax_id_extracted(self):
        result = await eingangsrechnung_pruefen(VALID_CII_XML)
        daten = result["daten"]
        assert daten.get("aussteller_ust_id") == "DE123456789"

    @pytest.mark.asyncio
    async def test_ubl_due_date_extracted(self):
        result = await eingangsrechnung_pruefen(VALID_UBL_XML)
        daten = result["daten"]
        assert daten.get("faelligkeitsdatum") == "2026-03-15"

    @pytest.mark.asyncio
    async def test_ubl_supplier_address(self):
        result = await eingangsrechnung_pruefen(VALID_UBL_XML)
        daten = result["daten"]
        assert daten.get("aussteller_strasse") == "Musterweg 5"
        assert daten.get("aussteller_plz") == "80331"
        assert daten.get("aussteller_ort") == "Muenchen"

    @pytest.mark.asyncio
    async def test_ubl_tax_id_with_de_prefix(self):
        result = await eingangsrechnung_pruefen(VALID_UBL_XML)
        daten = result["daten"]
        assert daten.get("aussteller_ust_id") == "DE987654321"

    @pytest.mark.asyncio
    async def test_empty_xml_string(self):
        result = await eingangsrechnung_pruefen("")
        assert result["erfolg"] is False

    @pytest.mark.asyncio
    async def test_date_serialized_as_string(self):
        """Dates in parsed data should be serialized as ISO strings."""
        result = await eingangsrechnung_pruefen(VALID_CII_XML)
        daten = result["daten"]
        # rechnungsdatum should be a string, not a date object
        rd = daten.get("rechnungsdatum")
        assert isinstance(rd, str)
        assert rd == "2026-03-01"

    @pytest.mark.asyncio
    async def test_decimal_serialized_as_string(self):
        """Decimal values in parsed data should be serialized as strings."""
        result = await eingangsrechnung_pruefen(VALID_CII_XML)
        daten = result["daten"]
        netto = daten.get("summe_netto")
        assert isinstance(netto, str)


# ===================================================================
# eingangsrechnungen_auflisten (listing tool)
# ===================================================================


class TestEingangsrechnungenAuflisten:
    """Tests for the eingangsrechnungen_auflisten MCP tool."""

    @pytest.mark.asyncio
    async def test_list_empty(self, mcp_session_factory):
        result = await eingangsrechnungen_auflisten()
        assert result["total"] == 0
        assert result["eingangsrechnungen"] == []
        assert result["page"] == 1

    @pytest.mark.asyncio
    async def test_list_all(self, mcp_session_factory, seed_eingangsrechnungen):
        result = await eingangsrechnungen_auflisten()
        assert result["total"] == 3
        assert len(result["eingangsrechnungen"]) == 3

    @pytest.mark.asyncio
    async def test_list_filter_by_status(self, mcp_session_factory, seed_eingangsrechnungen):
        result = await eingangsrechnungen_auflisten(status="eingegangen")
        assert result["total"] == 1
        assert result["eingangsrechnungen"][0]["rechnungsnummer"] == "ER-001"

    @pytest.mark.asyncio
    async def test_list_filter_bezahlt(self, mcp_session_factory, seed_eingangsrechnungen):
        result = await eingangsrechnungen_auflisten(status="bezahlt")
        assert result["total"] == 1
        assert result["eingangsrechnungen"][0]["status"] == "bezahlt"

    @pytest.mark.asyncio
    async def test_list_filter_no_match(self, mcp_session_factory, seed_eingangsrechnungen):
        result = await eingangsrechnungen_auflisten(status="abgelehnt")
        assert result["total"] == 0
        assert result["eingangsrechnungen"] == []

    @pytest.mark.asyncio
    async def test_list_pagination(self, mcp_session_factory, seed_eingangsrechnungen):
        result_page1 = await eingangsrechnungen_auflisten(page=1)
        assert result_page1["page"] == 1
        assert len(result_page1["eingangsrechnungen"]) == 3

    @pytest.mark.asyncio
    async def test_list_item_fields(self, mcp_session_factory, seed_eingangsrechnungen):
        """Each item should have the expected keys."""
        result = await eingangsrechnungen_auflisten()
        item = result["eingangsrechnungen"][0]
        expected_keys = {"id", "rechnungsnummer", "aussteller_name", "rechnungsdatum", "summe_brutto", "status"}
        assert expected_keys.issubset(item.keys())


# ===================================================================
# eingangsrechnung_status_aendern (status change tool)
# ===================================================================


class TestEingangsrechnungStatusAendern:
    """Tests for the eingangsrechnung_status_aendern MCP tool."""

    @pytest.mark.asyncio
    async def test_change_to_geprueft(self, mcp_session_factory, seed_eingangsrechnungen):
        rechnung = seed_eingangsrechnungen[0]
        result = await eingangsrechnung_status_aendern(
            rechnung_id=rechnung.id,
            status="geprueft",
        )
        assert result["status"] == "geprueft"
        assert result["id"] == rechnung.id

    @pytest.mark.asyncio
    async def test_change_to_freigegeben(self, mcp_session_factory, seed_eingangsrechnungen):
        rechnung = seed_eingangsrechnungen[1]  # already geprueft
        result = await eingangsrechnung_status_aendern(
            rechnung_id=rechnung.id,
            status="freigegeben",
        )
        assert result["status"] == "freigegeben"

    @pytest.mark.asyncio
    async def test_change_with_notiz(self, mcp_session_factory, seed_eingangsrechnungen):
        rechnung = seed_eingangsrechnungen[0]
        result = await eingangsrechnung_status_aendern(
            rechnung_id=rechnung.id,
            status="geprueft",
            notiz="Sachlich und rechnerisch korrekt.",
        )
        assert result["status"] == "geprueft"
        assert result["notiz"] == "Sachlich und rechnerisch korrekt."

    @pytest.mark.asyncio
    async def test_change_invalid_status(self, mcp_session_factory, seed_eingangsrechnungen):
        rechnung = seed_eingangsrechnungen[0]
        result = await eingangsrechnung_status_aendern(
            rechnung_id=rechnung.id,
            status="ungueltig",
        )
        assert "error" in result

    @pytest.mark.asyncio
    async def test_change_nonexistent_rechnung(self, mcp_session_factory):
        result = await eingangsrechnung_status_aendern(
            rechnung_id=99999,
            status="geprueft",
        )
        assert "error" in result

    @pytest.mark.asyncio
    async def test_change_to_bezahlt(self, mcp_session_factory, seed_eingangsrechnungen):
        rechnung = seed_eingangsrechnungen[1]
        result = await eingangsrechnung_status_aendern(
            rechnung_id=rechnung.id,
            status="bezahlt",
        )
        assert result["status"] == "bezahlt"

    @pytest.mark.asyncio
    async def test_change_to_abgelehnt(self, mcp_session_factory, seed_eingangsrechnungen):
        rechnung = seed_eingangsrechnungen[0]
        result = await eingangsrechnung_status_aendern(
            rechnung_id=rechnung.id,
            status="abgelehnt",
            notiz="Rechnung fehlerhaft.",
        )
        assert result["status"] == "abgelehnt"
        assert result["notiz"] == "Rechnung fehlerhaft."
