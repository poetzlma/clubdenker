"""ZUGFeRD 2.1 / Factur-X BASIC profile XML generation.

Generates UN/CEFACT Cross Industry Invoice (CII) XML that conforms to
the ZUGFeRD 2.1 BASIC profile (urn:factur-x.eu:1p0:basic).
"""

from __future__ import annotations

from decimal import Decimal

from lxml import etree
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sportverein.models.finanzen import Rechnung, RechnungTyp, Rechnungsposition
from sportverein.models.vereinsstammdaten import Vereinsstammdaten

# CII namespaces
_NS_RSM = "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
_NS_RAM = "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"
_NS_UDT = "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100"

_NSMAP = {
    "rsm": _NS_RSM,
    "ram": _NS_RAM,
    "udt": _NS_UDT,
}

# UN/ECE Rec 20 unit code mapping
_UNIT_CODE_MAP: dict[str, str] = {
    "x": "C62",
    "h": "HUR",
    "Monat": "MON",
    "Stk": "C62",
    "Stück": "C62",
    "Kurs": "C62",
}

# TypeCode mapping: 380=Invoice, 381=Credit Note (Storno), 389=Self-billed
_TYPE_CODE_MAP: dict[RechnungTyp, str] = {
    RechnungTyp.storno: "381",
}
_DEFAULT_TYPE_CODE = "380"


def _rsm(tag: str) -> str:
    return f"{{{_NS_RSM}}}{tag}"


def _ram(tag: str) -> str:
    return f"{{{_NS_RAM}}}{tag}"


def _udt(tag: str) -> str:
    return f"{{{_NS_UDT}}}{tag}"


def _fmt_date_102(d) -> str:
    """Format date as YYYYMMDD (format='102')."""
    return d.strftime("%Y%m%d")


def _fmt_amount(value: Decimal) -> str:
    """Format a Decimal as string with 2 decimal places."""
    return f"{value:.2f}"


def _fmt_quantity(value: Decimal) -> str:
    """Format a quantity, removing unnecessary trailing zeros."""
    # Normalize to remove trailing zeros, then convert to string
    normalized = value.normalize()
    # Ensure at least no scientific notation
    return f"{normalized:f}"


def _unit_code(einheit: str) -> str:
    """Map German unit strings to UN/ECE Rec 20 codes."""
    return _UNIT_CODE_MAP.get(einheit, "C62")


def _tax_category_code(steuersatz: Decimal) -> str:
    """E=Exempt (0%), S=Standard (>0%)."""
    return "E" if steuersatz == 0 else "S"


class ZugferdService:
    """Generate ZUGFeRD 2.1 BASIC profile XML for invoices."""

    def generate_xml(
        self,
        rechnung: Rechnung,
        stammdaten: Vereinsstammdaten | None,
    ) -> bytes:
        """Generate ZUGFeRD 2.1 BASIC profile XML.

        Args:
            rechnung: Invoice with positionen eagerly loaded.
            stammdaten: Club master data (seller info).

        Returns:
            UTF-8 encoded XML bytes.
        """
        root = etree.Element(_rsm("CrossIndustryInvoice"), nsmap=_NSMAP)

        # --- ExchangedDocumentContext ---
        ctx = etree.SubElement(root, _rsm("ExchangedDocumentContext"))
        guideline = etree.SubElement(ctx, _ram("GuidelineSpecifiedDocumentContextParameter"))
        etree.SubElement(guideline, _ram("ID")).text = "urn:factur-x.eu:1p0:basic"

        # --- ExchangedDocument ---
        doc = etree.SubElement(root, _rsm("ExchangedDocument"))
        etree.SubElement(doc, _ram("ID")).text = rechnung.rechnungsnummer
        type_code = _TYPE_CODE_MAP.get(rechnung.rechnungstyp, _DEFAULT_TYPE_CODE)
        etree.SubElement(doc, _ram("TypeCode")).text = type_code
        issue_dt = etree.SubElement(doc, _ram("IssueDateTime"))
        dt_str = etree.SubElement(issue_dt, _udt("DateTimeString"), format="102")
        dt_str.text = _fmt_date_102(rechnung.rechnungsdatum)

        # --- SupplyChainTradeTransaction ---
        transaction = etree.SubElement(root, _rsm("SupplyChainTradeTransaction"))

        # -- Line items (before header sections per CII schema order) --
        positionen = sorted(rechnung.positionen, key=lambda p: p.position_nr)
        for pos in positionen:
            self._build_line_item(transaction, pos)

        # -- ApplicableHeaderTradeAgreement ---
        agreement = etree.SubElement(transaction, _ram("ApplicableHeaderTradeAgreement"))
        self._build_seller(agreement, stammdaten)
        self._build_buyer(agreement, rechnung)

        # -- ApplicableHeaderTradeDelivery ---
        delivery = etree.SubElement(transaction, _ram("ApplicableHeaderTradeDelivery"))
        delivery_event = etree.SubElement(delivery, _ram("ActualDeliverySupplyChainEvent"))
        occ_dt = etree.SubElement(delivery_event, _ram("OccurrenceDateTime"))
        occ_dt_str = etree.SubElement(occ_dt, _udt("DateTimeString"), format="102")
        # Use leistungsdatum, or leistungszeitraum_von, or rechnungsdatum
        leistungsdatum = (
            rechnung.leistungsdatum or rechnung.leistungszeitraum_von or rechnung.rechnungsdatum
        )
        occ_dt_str.text = _fmt_date_102(leistungsdatum)

        # -- ApplicableHeaderTradeSettlement ---
        settlement = etree.SubElement(transaction, _ram("ApplicableHeaderTradeSettlement"))
        etree.SubElement(settlement, _ram("InvoiceCurrencyCode")).text = "EUR"

        # Payment terms (due date)
        terms = etree.SubElement(settlement, _ram("SpecifiedTradePaymentTerms"))
        due_dt = etree.SubElement(terms, _ram("DueDateDateTime"))
        due_dt_str = etree.SubElement(due_dt, _udt("DateTimeString"), format="102")
        due_dt_str.text = _fmt_date_102(rechnung.faelligkeitsdatum)

        # Payment means (SEPA)
        if stammdaten and stammdaten.iban:
            means = etree.SubElement(settlement, _ram("SpecifiedTradeSettlementPaymentMeans"))
            etree.SubElement(means, _ram("TypeCode")).text = "58"  # SEPA
            account = etree.SubElement(means, _ram("PayeePartyCreditorFinancialAccount"))
            etree.SubElement(account, _ram("IBANID")).text = stammdaten.iban

        # Tax summary per rate
        self._build_tax_summary(settlement, positionen, rechnung)

        # Monetary summation
        summation = etree.SubElement(
            settlement, _ram("SpecifiedTradeSettlementHeaderMonetarySummation")
        )
        etree.SubElement(summation, _ram("LineTotalAmount")).text = _fmt_amount(
            rechnung.summe_netto
        )
        etree.SubElement(summation, _ram("TaxBasisTotalAmount")).text = _fmt_amount(
            rechnung.summe_netto
        )
        tax_total = etree.SubElement(summation, _ram("TaxTotalAmount"), currencyID="EUR")
        tax_total.text = _fmt_amount(rechnung.summe_steuer)
        etree.SubElement(summation, _ram("GrandTotalAmount")).text = _fmt_amount(rechnung.betrag)
        etree.SubElement(summation, _ram("DuePayableAmount")).text = _fmt_amount(
            rechnung.offener_betrag
        )

        return etree.tostring(
            root,
            xml_declaration=True,
            encoding="UTF-8",
            pretty_print=True,
        )

    def _build_seller(
        self,
        parent: etree._Element,
        stammdaten: Vereinsstammdaten | None,
    ) -> None:
        seller = etree.SubElement(parent, _ram("SellerTradeParty"))
        name = stammdaten.name if stammdaten else "Sportverein e.V."
        etree.SubElement(seller, _ram("Name")).text = name

        addr = etree.SubElement(seller, _ram("PostalTradeAddress"))
        if stammdaten:
            etree.SubElement(addr, _ram("LineOne")).text = stammdaten.strasse
            etree.SubElement(addr, _ram("PostcodeCode")).text = stammdaten.plz
            etree.SubElement(addr, _ram("CityName")).text = stammdaten.ort
        etree.SubElement(addr, _ram("CountryID")).text = "DE"

        if stammdaten and stammdaten.steuernummer:
            tax_reg = etree.SubElement(seller, _ram("SpecifiedTaxRegistration"))
            tax_id = etree.SubElement(tax_reg, _ram("ID"), schemeID="FC")
            tax_id.text = stammdaten.steuernummer

        if stammdaten and stammdaten.ust_id:
            tax_reg_vat = etree.SubElement(seller, _ram("SpecifiedTaxRegistration"))
            tax_id_vat = etree.SubElement(tax_reg_vat, _ram("ID"), schemeID="VA")
            tax_id_vat.text = stammdaten.ust_id

    def _build_buyer(
        self,
        parent: etree._Element,
        rechnung: Rechnung,
    ) -> None:
        buyer = etree.SubElement(parent, _ram("BuyerTradeParty"))
        etree.SubElement(buyer, _ram("Name")).text = rechnung.empfaenger_name or "Unbekannt"

        addr = etree.SubElement(buyer, _ram("PostalTradeAddress"))
        if rechnung.empfaenger_strasse:
            etree.SubElement(addr, _ram("LineOne")).text = rechnung.empfaenger_strasse
        if rechnung.empfaenger_plz:
            etree.SubElement(addr, _ram("PostcodeCode")).text = rechnung.empfaenger_plz
        if rechnung.empfaenger_ort:
            etree.SubElement(addr, _ram("CityName")).text = rechnung.empfaenger_ort
        etree.SubElement(addr, _ram("CountryID")).text = "DE"

    def _build_line_item(
        self,
        transaction: etree._Element,
        pos: Rechnungsposition,
    ) -> None:
        item = etree.SubElement(transaction, _ram("IncludedSupplyChainTradeLineItem"))

        # Line document
        line_doc = etree.SubElement(item, _ram("AssociatedDocumentLineDocument"))
        etree.SubElement(line_doc, _ram("LineID")).text = str(pos.position_nr)

        # Product
        product = etree.SubElement(item, _ram("SpecifiedTradeProduct"))
        etree.SubElement(product, _ram("Name")).text = pos.beschreibung

        # Line trade agreement
        line_agreement = etree.SubElement(item, _ram("SpecifiedLineTradeAgreement"))
        net_price = etree.SubElement(line_agreement, _ram("NetPriceProductTradePrice"))
        etree.SubElement(net_price, _ram("ChargeAmount")).text = _fmt_amount(pos.einzelpreis_netto)

        # Line trade delivery
        line_delivery = etree.SubElement(item, _ram("SpecifiedLineTradeDelivery"))
        qty = etree.SubElement(
            line_delivery,
            _ram("BilledQuantity"),
            unitCode=_unit_code(pos.einheit),
        )
        qty.text = _fmt_quantity(pos.menge)

        # Line trade settlement
        line_settlement = etree.SubElement(item, _ram("SpecifiedLineTradeSettlement"))
        line_tax = etree.SubElement(line_settlement, _ram("ApplicableTradeTax"))
        etree.SubElement(line_tax, _ram("TypeCode")).text = "VAT"
        etree.SubElement(line_tax, _ram("CategoryCode")).text = _tax_category_code(pos.steuersatz)
        etree.SubElement(line_tax, _ram("RateApplicablePercent")).text = _fmt_amount(pos.steuersatz)

        line_summation = etree.SubElement(
            line_settlement, _ram("SpecifiedTradeSettlementLineMonetarySummation")
        )
        etree.SubElement(line_summation, _ram("LineTotalAmount")).text = _fmt_amount(
            pos.gesamtpreis_netto
        )

    def _build_tax_summary(
        self,
        settlement: etree._Element,
        positionen: list[Rechnungsposition],
        rechnung: Rechnung,
    ) -> None:
        """Build ApplicableTradeTax elements grouped by tax rate."""
        if positionen:
            # Group by steuersatz
            tax_groups: dict[Decimal, dict[str, Decimal | str | None]] = {}
            for pos in positionen:
                rate = pos.steuersatz
                if rate not in tax_groups:
                    tax_groups[rate] = {
                        "basis": Decimal("0"),
                        "tax": Decimal("0"),
                        "exemption_reason": pos.steuerbefreiungsgrund,
                    }
                tax_groups[rate]["basis"] += Decimal(str(pos.gesamtpreis_netto or 0))
                tax_groups[rate]["tax"] += Decimal(str(pos.gesamtpreis_steuer or 0))

            for rate in sorted(tax_groups.keys()):
                group = tax_groups[rate]
                tax_el = etree.SubElement(settlement, _ram("ApplicableTradeTax"))
                etree.SubElement(tax_el, _ram("CalculatedAmount")).text = _fmt_amount(
                    Decimal(str(group["tax"]))
                )
                etree.SubElement(tax_el, _ram("TypeCode")).text = "VAT"
                if rate == 0 and group.get("exemption_reason"):
                    etree.SubElement(tax_el, _ram("ExemptionReason")).text = str(
                        group["exemption_reason"]
                    )
                etree.SubElement(tax_el, _ram("BasisAmount")).text = _fmt_amount(
                    Decimal(str(group["basis"]))
                )
                etree.SubElement(tax_el, _ram("CategoryCode")).text = _tax_category_code(rate)
                etree.SubElement(tax_el, _ram("RateApplicablePercent")).text = _fmt_amount(rate)
        else:
            # No line items: single exempt tax entry
            tax_el = etree.SubElement(settlement, _ram("ApplicableTradeTax"))
            etree.SubElement(tax_el, _ram("CalculatedAmount")).text = _fmt_amount(
                rechnung.summe_steuer
            )
            etree.SubElement(tax_el, _ram("TypeCode")).text = "VAT"
            etree.SubElement(tax_el, _ram("BasisAmount")).text = _fmt_amount(rechnung.summe_netto)
            etree.SubElement(tax_el, _ram("CategoryCode")).text = "E"
            etree.SubElement(tax_el, _ram("RateApplicablePercent")).text = "0.00"

    async def generate_zugferd_xml(
        self,
        session: AsyncSession,
        rechnung_id: int,
    ) -> bytes:
        """Load invoice + stammdaten from DB and generate ZUGFeRD XML.

        Args:
            session: Async database session.
            rechnung_id: ID of the invoice.

        Returns:
            UTF-8 encoded XML bytes.

        Raises:
            ValueError: If invoice not found.
        """
        result = await session.execute(
            select(Rechnung)
            .where(Rechnung.id == rechnung_id)
            .options(selectinload(Rechnung.positionen))
        )
        rechnung = result.scalar_one_or_none()
        if rechnung is None:
            raise ValueError(f"Rechnung {rechnung_id} nicht gefunden")

        stamm_result = await session.execute(select(Vereinsstammdaten).limit(1))
        stammdaten = stamm_result.scalar_one_or_none()

        return self.generate_xml(rechnung, stammdaten)
