"""Service for parsing and managing incoming e-invoices (XRechnung / ZUGFeRD)."""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from lxml import etree
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sportverein.models.finanzen import (
    Eingangsrechnung,
    EingangsrechnungStatus,
)

# ---------------------------------------------------------------------------
# XML namespace maps
# ---------------------------------------------------------------------------

CII_NS = {
    "rsm": "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100",
    "ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
    "udt": "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100",
    "qdt": "urn:un:unece:uncefact:data:standard:QualifiedDataType:100",
}

UBL_NS = {
    "inv": "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
}

# Pflichtfelder according to section 14 UStG
PFLICHTFELDER = [
    "rechnungsnummer",
    "aussteller_name",
    "rechnungsdatum",
    "summe_netto",
    "summe_brutto",
]


def _text(element: etree._Element | None) -> str | None:
    """Extract text from an lxml element, or None."""
    if element is not None and element.text:
        return element.text.strip()
    return None


def _decimal(element: etree._Element | None) -> Decimal | None:
    """Extract Decimal from an lxml element, or None."""
    txt = _text(element)
    if txt is None:
        return None
    try:
        return Decimal(txt)
    except InvalidOperation:
        return None


def _parse_date_102(element: etree._Element | None) -> date | None:
    """Parse CII date format 102 (YYYYMMDD)."""
    if element is None:
        return None
    # Look for <udt:DateTimeString format="102">YYYYMMDD</udt:DateTimeString>
    dt_str = element.find("udt:DateTimeString", CII_NS)
    if dt_str is not None and dt_str.text:
        txt = dt_str.text.strip()
        if len(txt) == 8:
            try:
                return datetime.strptime(txt, "%Y%m%d").date()
            except ValueError:
                pass
    # Also try plain text (YYYY-MM-DD)
    txt = _text(element)
    if txt:
        for fmt in ("%Y-%m-%d", "%Y%m%d"):
            try:
                return datetime.strptime(txt, fmt).date()
            except ValueError:
                continue
    return None


def _parse_ubl_date(element: etree._Element | None) -> date | None:
    """Parse UBL date (YYYY-MM-DD)."""
    txt = _text(element)
    if txt:
        try:
            return datetime.strptime(txt, "%Y-%m-%d").date()
        except ValueError:
            pass
    return None


class EingangsrechnungService:
    """Service for parsing e-invoices and managing Eingangsrechnungen."""

    def __init__(self, session: AsyncSession | None = None) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # Format detection
    # ------------------------------------------------------------------

    def detect_format(self, xml_content: bytes | str) -> str:
        """Detect whether XML is CII (XRechnung/ZUGFeRD) or UBL."""
        if isinstance(xml_content, str):
            xml_content = xml_content.encode("utf-8")

        try:
            root = etree.fromstring(xml_content)
        except etree.XMLSyntaxError as exc:
            raise ValueError(f"Ungültiges XML: {exc}") from exc

        tag = root.tag
        # Remove namespace prefix for comparison
        local = tag.split("}")[-1] if "}" in tag else tag

        if local == "CrossIndustryInvoice":
            return "cii"
        if local == "Invoice":
            return "ubl"
        raise ValueError(
            f"Unbekanntes XML-Root-Element: {local}. "
            "Erwartet: CrossIndustryInvoice (CII) oder Invoice (UBL)."
        )

    # ------------------------------------------------------------------
    # CII parser (XRechnung / ZUGFeRD)
    # ------------------------------------------------------------------

    def _parse_cii(self, root: etree._Element) -> dict[str, Any]:
        """Parse CII (CrossIndustryInvoice) XML."""
        result: dict[str, Any] = {"quell_format": "xrechnung"}

        # -- ExchangedDocument --
        doc = root.find("rsm:ExchangedDocument", CII_NS)
        if doc is not None:
            result["rechnungsnummer"] = _text(doc.find("ram:ID", CII_NS)) or ""
            result["rechnungsdatum"] = _parse_date_102(doc.find("ram:IssueDateTime", CII_NS))

        # -- SupplyChainTradeTransaction --
        txn = root.find("rsm:SupplyChainTradeTransaction", CII_NS)
        if txn is None:
            return result

        # -- Seller (Aussteller) --
        agreement = txn.find("ram:ApplicableHeaderTradeAgreement", CII_NS)
        if agreement is not None:
            seller = agreement.find("ram:SellerTradeParty", CII_NS)
            if seller is not None:
                result["aussteller_name"] = _text(seller.find("ram:Name", CII_NS)) or ""

                addr = seller.find("ram:PostalTradeAddress", CII_NS)
                if addr is not None:
                    result["aussteller_strasse"] = _text(addr.find("ram:LineOne", CII_NS))
                    result["aussteller_plz"] = _text(addr.find("ram:PostcodeCode", CII_NS))
                    result["aussteller_ort"] = _text(addr.find("ram:CityName", CII_NS))

                # Tax registration
                for tax_reg in seller.findall("ram:SpecifiedTaxRegistration", CII_NS):
                    tax_id = tax_reg.find("ram:ID", CII_NS)
                    if tax_id is not None:
                        scheme = tax_id.get("schemeID", "")
                        value = _text(tax_id)
                        if scheme == "VA":
                            result["aussteller_ust_id"] = value
                        elif scheme == "FC":
                            result["aussteller_steuernr"] = value

        # -- Delivery (Leistungsdatum) --
        delivery = txn.find("ram:ApplicableHeaderTradeDelivery", CII_NS)
        if delivery is not None:
            occ = delivery.find("ram:ActualDeliverySupplyChainEvent/ram:OccurrenceDateTime", CII_NS)
            result["leistungsdatum"] = _parse_date_102(occ)

        # -- Settlement (amounts, currency, due date) --
        settlement = txn.find("ram:ApplicableHeaderTradeSettlement", CII_NS)
        if settlement is not None:
            result["waehrung"] = _text(settlement.find("ram:InvoiceCurrencyCode", CII_NS)) or "EUR"

            # Due date from payment terms
            terms = settlement.find("ram:SpecifiedTradePaymentTerms", CII_NS)
            if terms is not None:
                result["faelligkeitsdatum"] = _parse_date_102(
                    terms.find("ram:DueDateDateTime", CII_NS)
                )

            # Monetary summation
            summation = settlement.find(
                "ram:SpecifiedTradeSettlementHeaderMonetarySummation", CII_NS
            )
            if summation is not None:
                result["summe_netto"] = _decimal(summation.find("ram:TaxBasisTotalAmount", CII_NS))
                result["summe_steuer"] = _decimal(summation.find("ram:TaxTotalAmount", CII_NS))
                result["summe_brutto"] = _decimal(summation.find("ram:GrandTotalAmount", CII_NS))
                # DuePayableAmount can also serve as brutto
                if result.get("summe_brutto") is None:
                    result["summe_brutto"] = _decimal(
                        summation.find("ram:DuePayableAmount", CII_NS)
                    )

        # Compute missing totals
        if (
            result.get("summe_netto")
            and result.get("summe_brutto")
            and not result.get("summe_steuer")
        ):
            result["summe_steuer"] = result["summe_brutto"] - result["summe_netto"]
        if (
            result.get("summe_netto")
            and result.get("summe_steuer")
            and not result.get("summe_brutto")
        ):
            result["summe_brutto"] = result["summe_netto"] + result["summe_steuer"]

        return result

    # ------------------------------------------------------------------
    # UBL parser
    # ------------------------------------------------------------------

    def _parse_ubl(self, root: etree._Element) -> dict[str, Any]:
        """Parse UBL 2.1 Invoice XML."""
        result: dict[str, Any] = {"quell_format": "xrechnung"}

        result["rechnungsnummer"] = _text(root.find("cbc:ID", UBL_NS)) or ""
        result["rechnungsdatum"] = _parse_ubl_date(root.find("cbc:IssueDate", UBL_NS))
        result["faelligkeitsdatum"] = _parse_ubl_date(root.find("cbc:DueDate", UBL_NS))

        # Currency
        result["waehrung"] = _text(root.find("cbc:DocumentCurrencyCode", UBL_NS)) or "EUR"

        # Seller
        supplier = root.find("cac:AccountingSupplierParty/cac:Party", UBL_NS)
        if supplier is not None:
            name_el = supplier.find("cac:PartyName/cbc:Name", UBL_NS)
            result["aussteller_name"] = _text(name_el) or ""

            # Try PartyLegalEntity/RegistrationName as fallback
            if not result["aussteller_name"]:
                legal_name = supplier.find("cac:PartyLegalEntity/cbc:RegistrationName", UBL_NS)
                result["aussteller_name"] = _text(legal_name) or ""

            addr = supplier.find("cac:PostalAddress", UBL_NS)
            if addr is not None:
                result["aussteller_strasse"] = _text(addr.find("cbc:StreetName", UBL_NS))
                result["aussteller_plz"] = _text(addr.find("cbc:PostalZone", UBL_NS))
                result["aussteller_ort"] = _text(addr.find("cbc:CityName", UBL_NS))

            # Tax scheme
            tax_scheme = supplier.find("cac:PartyTaxScheme/cbc:CompanyID", UBL_NS)
            if tax_scheme is not None:
                tax_val = _text(tax_scheme)
                if tax_val and tax_val.startswith("DE"):
                    result["aussteller_ust_id"] = tax_val
                else:
                    result["aussteller_steuernr"] = tax_val

        # Monetary totals
        monetary = root.find("cac:LegalMonetaryTotal", UBL_NS)
        if monetary is not None:
            result["summe_netto"] = _decimal(monetary.find("cbc:TaxExclusiveAmount", UBL_NS))
            result["summe_brutto"] = _decimal(monetary.find("cbc:TaxInclusiveAmount", UBL_NS))
            if result.get("summe_brutto") is None:
                result["summe_brutto"] = _decimal(monetary.find("cbc:PayableAmount", UBL_NS))

        # Tax total
        tax_total = root.find("cac:TaxTotal/cbc:TaxAmount", UBL_NS)
        result["summe_steuer"] = _decimal(tax_total)

        # Compute missing
        if (
            result.get("summe_netto")
            and result.get("summe_brutto")
            and not result.get("summe_steuer")
        ):
            result["summe_steuer"] = result["summe_brutto"] - result["summe_netto"]

        # Delivery date
        delivery_date = root.find("cac:Delivery/cbc:ActualDeliveryDate", UBL_NS)
        result["leistungsdatum"] = _parse_ubl_date(delivery_date)

        return result

    # ------------------------------------------------------------------
    # Public parse methods
    # ------------------------------------------------------------------

    def parse_xml(self, xml_content: bytes | str) -> dict[str, Any]:
        """Parse XRechnung/ZUGFeRD XML and extract structured data.

        Supports both CII (CrossIndustryInvoice) and UBL (Invoice) formats.
        Returns dict with extracted fields matching Eingangsrechnung model.
        """
        if isinstance(xml_content, str):
            raw = xml_content.encode("utf-8")
        else:
            raw = xml_content

        try:
            root = etree.fromstring(raw)
        except etree.XMLSyntaxError as exc:
            raise ValueError(f"Ungültiges XML: {exc}") from exc

        fmt = self.detect_format(raw)
        if fmt == "cii":
            parsed = self._parse_cii(root)
        else:
            parsed = self._parse_ubl(root)

        # Store original XML
        if isinstance(xml_content, bytes):
            parsed["quell_xml"] = xml_content.decode("utf-8", errors="replace")
        else:
            parsed["quell_xml"] = xml_content

        return parsed

    def parse_zugferd_pdf(self, pdf_content: bytes) -> dict[str, Any]:
        """Extract embedded XML from ZUGFeRD PDF and parse it.

        Simplified approach: search for XML patterns inside the PDF bytes.
        """
        # ZUGFeRD PDFs embed XML as an attachment. We look for the XML
        # start/end markers in the raw bytes.
        content_str = pdf_content.decode("latin-1", errors="replace")

        # Try to find CII XML
        cii_pattern = re.compile(
            r"(<\?xml[^>]*\?>.*?<rsm:CrossIndustryInvoice.*?</rsm:CrossIndustryInvoice>)",
            re.DOTALL,
        )
        match = cii_pattern.search(content_str)
        if match:
            xml_str = match.group(1)
            result = self.parse_xml(xml_str.encode("utf-8"))
            result["quell_format"] = "zugferd"
            return result

        # Try UBL
        ubl_pattern = re.compile(
            r"(<\?xml[^>]*\?>.*?<Invoice[^>]*>.*?</Invoice>)",
            re.DOTALL,
        )
        match = ubl_pattern.search(content_str)
        if match:
            xml_str = match.group(1)
            result = self.parse_xml(xml_str.encode("utf-8"))
            result["quell_format"] = "zugferd"
            return result

        raise ValueError(
            "Kein eingebettetes XML in der PDF-Datei gefunden. "
            "Bitte stellen Sie sicher, dass es sich um eine ZUGFeRD-PDF handelt."
        )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    async def validate_pflichtfelder(self, parsed: dict[str, Any]) -> list[str]:
        """Check if all section 14 UStG required fields are present.

        Returns list of missing field names (German labels).
        """
        labels = {
            "rechnungsnummer": "Rechnungsnummer",
            "aussteller_name": "Name des Ausstellers",
            "rechnungsdatum": "Rechnungsdatum",
            "summe_netto": "Nettobetrag",
            "summe_brutto": "Bruttobetrag",
        }
        missing: list[str] = []
        for field in PFLICHTFELDER:
            value = parsed.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                missing.append(labels.get(field, field))
        return missing

    # ------------------------------------------------------------------
    # CRUD operations
    # ------------------------------------------------------------------

    async def create_from_xml(
        self, session: AsyncSession | None, xml_content: bytes | str
    ) -> tuple[Eingangsrechnung, list[str]]:
        """Parse XML and create Eingangsrechnung record.

        Returns (record, warnings) where warnings is a list of missing Pflichtfelder.
        """
        sess = session or self.session
        if sess is None:
            raise RuntimeError("No database session provided")

        parsed = self.parse_xml(xml_content)
        warnings = await self.validate_pflichtfelder(parsed)

        rechnung = Eingangsrechnung(
            rechnungsnummer=parsed.get("rechnungsnummer", ""),
            aussteller_name=parsed.get("aussteller_name", ""),
            aussteller_strasse=parsed.get("aussteller_strasse"),
            aussteller_plz=parsed.get("aussteller_plz"),
            aussteller_ort=parsed.get("aussteller_ort"),
            aussteller_steuernr=parsed.get("aussteller_steuernr"),
            aussteller_ust_id=parsed.get("aussteller_ust_id"),
            rechnungsdatum=parsed.get("rechnungsdatum") or date.today(),
            faelligkeitsdatum=parsed.get("faelligkeitsdatum"),
            leistungsdatum=parsed.get("leistungsdatum"),
            summe_netto=parsed.get("summe_netto") or Decimal("0"),
            summe_steuer=parsed.get("summe_steuer") or Decimal("0"),
            summe_brutto=parsed.get("summe_brutto") or Decimal("0"),
            waehrung=parsed.get("waehrung", "EUR"),
            status=EingangsrechnungStatus.eingegangen,
            quell_format=parsed.get("quell_format"),
            quell_xml=parsed.get("quell_xml"),
        )
        sess.add(rechnung)
        await sess.flush()
        await sess.refresh(rechnung)
        return rechnung, warnings

    async def list_eingangsrechnungen(
        self,
        session: AsyncSession | None = None,
        filters: dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Eingangsrechnung], int]:
        """List incoming invoices with pagination."""
        sess = session or self.session
        if sess is None:
            raise RuntimeError("No database session provided")

        query = select(Eingangsrechnung)
        count_query = select(func.count()).select_from(Eingangsrechnung)

        conditions = []
        if filters:
            if filters.get("status"):
                status_val = filters["status"]
                if isinstance(status_val, str):
                    status_val = EingangsrechnungStatus(status_val)
                conditions.append(Eingangsrechnung.status == status_val)
            if filters.get("date_from"):
                conditions.append(Eingangsrechnung.rechnungsdatum >= filters["date_from"])
            if filters.get("date_to"):
                conditions.append(Eingangsrechnung.rechnungsdatum <= filters["date_to"])

        if conditions:
            query = query.where(*conditions)
            count_query = count_query.where(*conditions)

        total_result = await sess.execute(count_query)
        total = total_result.scalar_one()

        query = query.order_by(Eingangsrechnung.rechnungsdatum.desc())
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await sess.execute(query)
        items = list(result.scalars().all())
        return items, total

    async def get_eingangsrechnung(
        self, session: AsyncSession | None, rechnung_id: int
    ) -> Eingangsrechnung | None:
        """Get a single incoming invoice by ID."""
        sess = session or self.session
        if sess is None:
            raise RuntimeError("No database session provided")

        result = await sess.execute(
            select(Eingangsrechnung).where(Eingangsrechnung.id == rechnung_id)
        )
        return result.scalar_one_or_none()

    async def update_status(
        self,
        session: AsyncSession | None,
        rechnung_id: int,
        status: str,
        notiz: str | None = None,
    ) -> Eingangsrechnung:
        """Update status of incoming invoice."""
        sess = session or self.session
        if sess is None:
            raise RuntimeError("No database session provided")

        result = await sess.execute(
            select(Eingangsrechnung).where(Eingangsrechnung.id == rechnung_id)
        )
        rechnung = result.scalar_one_or_none()
        if rechnung is None:
            raise ValueError(f"Eingangsrechnung mit ID {rechnung_id} nicht gefunden")

        valid_statuses = {s.value for s in EingangsrechnungStatus}
        if status not in valid_statuses:
            raise ValueError(
                f"Ungültiger Status: {status}. Erlaubt: {', '.join(sorted(valid_statuses))}"
            )

        # Validate state transitions
        allowed_transitions: dict[str, set[str]] = {
            "eingegangen": {"geprueft", "abgelehnt"},
            "geprueft": {"freigegeben", "abgelehnt"},
            "freigegeben": {"bezahlt", "abgelehnt"},
            "bezahlt": set(),  # terminal state
            "abgelehnt": {"eingegangen"},  # can be re-opened
        }
        current = rechnung.status.value
        if status not in allowed_transitions.get(current, set()):
            raise ValueError(
                f"Ungültiger Statusübergang: {current} -> {status}. "
                f"Erlaubt: {', '.join(sorted(allowed_transitions.get(current, set()))) or 'keine'}"
            )

        rechnung.status = EingangsrechnungStatus(status)
        if notiz is not None:
            rechnung.notiz = notiz

        await sess.flush()
        await sess.refresh(rechnung)
        return rechnung
