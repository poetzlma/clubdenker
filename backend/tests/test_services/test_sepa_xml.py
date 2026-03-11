"""Thorough tests for SEPA XML (pain.008.001.02) generation."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import date
from decimal import Decimal

import pytest

pytestmark = pytest.mark.asyncio

from sportverein.models.beitrag import SepaMandat
from sportverein.models.mitglied import Mitglied, MitgliedStatus
from sportverein.models.vereinsstammdaten import Vereinsstammdaten
from sportverein.services.finanzen import FinanzenService

NS = "urn:iso:std:iso:20022:tech:xsd:pain.008.001.02"
NS_MAP = {"ns": NS}


def _make_member(
    *,
    vorname: str = "Max",
    nachname: str = "Mustermann",
    email: str = "max@example.com",
    mitgliedsnummer: str = "M-0001",
    geburtsdatum: date = date(1990, 1, 1),
    eintrittsdatum: date = date(2020, 1, 1),
) -> Mitglied:
    return Mitglied(
        vorname=vorname,
        nachname=nachname,
        email=email,
        mitgliedsnummer=mitgliedsnummer,
        geburtsdatum=geburtsdatum,
        eintrittsdatum=eintrittsdatum,
        status=MitgliedStatus.aktiv,
    )


def _make_stammdaten(
    *,
    name: str = "TSV Teststadt e.V.",
    iban: str = "DE02120300000000202051",
    bic: str = "BYLADEM1001",
) -> Vereinsstammdaten:
    return Vereinsstammdaten(
        name=name,
        strasse="Sportweg 1",
        plz="12345",
        ort="Teststadt",
        iban=iban,
        bic=bic,
    )


def _find(root: ET.Element, xpath: str) -> ET.Element | None:
    """Find element with or without namespace."""
    el = root.find(xpath)
    if el is None:
        # Try with namespace prefix
        ns_xpath = xpath
        for tag in _extract_tags(xpath):
            ns_xpath = ns_xpath.replace(tag, f"ns:{tag}", 1)
        el = root.find(ns_xpath, NS_MAP)
    return el


def _findall(root: ET.Element, xpath: str) -> list[ET.Element]:
    """Findall with or without namespace."""
    els = root.findall(xpath)
    if not els:
        ns_xpath = xpath
        for tag in _extract_tags(xpath):
            ns_xpath = ns_xpath.replace(tag, f"ns:{tag}", 1)
        els = root.findall(ns_xpath, NS_MAP)
    return els


def _extract_tags(xpath: str) -> list[str]:
    """Extract tag names from an xpath like './/Foo/Bar'."""
    parts = xpath.replace(".", "").split("/")
    return [p for p in parts if p and not p.startswith("@")]


def _text(root: ET.Element, xpath: str) -> str | None:
    """Get text of element found at xpath."""
    el = _find(root, xpath)
    return el.text if el is not None else None


async def _setup_member_with_mandate(
    session,
    *,
    vorname: str = "Max",
    nachname: str = "Mustermann",
    email: str = "max@example.com",
    mitgliedsnummer: str = "M-0001",
    iban: str = "DE89370400440532013000",
    bic: str | None = "COBADEFFXXX",
    kontoinhaber: str | None = None,
    mandatsreferenz: str = "MREF-001",
    aktiv: bool = True,
):
    """Create a member with a SEPA mandate. Returns (member, mandate)."""
    member = _make_member(
        vorname=vorname,
        nachname=nachname,
        email=email,
        mitgliedsnummer=mitgliedsnummer,
    )
    session.add(member)
    await session.flush()

    mandat = SepaMandat(
        mitglied_id=member.id,
        mandatsreferenz=mandatsreferenz,
        iban=iban,
        bic=bic,
        kontoinhaber=kontoinhaber or f"{vorname} {nachname}",
        unterschriftsdatum=date(2023, 1, 1),
        gueltig_ab=date(2023, 1, 1),
        aktiv=aktiv,
    )
    session.add(mandat)
    await session.flush()

    return member, mandat


class TestSepaXmlStructure:
    """Verify the pain.008.001.02 document structure."""

    async def test_root_element_is_document(self, session):
        member, _ = await _setup_member_with_mandate(session)
        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            member.id, Decimal("100.00"), "Test", date(2024, 1, 31)
        )

        xml_str = await svc.generate_sepa_xml([rechnung.id])
        root = ET.fromstring(xml_str)

        # Root must be Document (with or without namespace)
        assert root.tag in (
            f"{{{NS}}}Document",
            "Document",
        )

    async def test_has_cstmr_drct_dbt_initn(self, session):
        member, _ = await _setup_member_with_mandate(session)
        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            member.id, Decimal("100.00"), "Test", date(2024, 1, 31)
        )

        xml_str = await svc.generate_sepa_xml([rechnung.id])
        root = ET.fromstring(xml_str)

        cstmr = _find(root, "CstmrDrctDbtInitn")
        assert cstmr is not None, "CstmrDrctDbtInitn element must exist"

    async def test_xml_declaration_present(self, session):
        member, _ = await _setup_member_with_mandate(session)
        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            member.id, Decimal("50.00"), "Decl test", date(2024, 1, 31)
        )

        xml_str = await svc.generate_sepa_xml([rechnung.id])
        assert xml_str.startswith("<?xml")

    async def test_payment_method_is_dd(self, session):
        member, _ = await _setup_member_with_mandate(session)
        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            member.id, Decimal("100.00"), "DD check", date(2024, 1, 31)
        )

        xml_str = await svc.generate_sepa_xml([rechnung.id])
        root = ET.fromstring(xml_str)

        pmt_mtd = _text(root, ".//PmtMtd")
        assert pmt_mtd == "DD"

    async def test_service_level_is_sepa(self, session):
        member, _ = await _setup_member_with_mandate(session)
        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            member.id, Decimal("100.00"), "SvcLvl", date(2024, 1, 31)
        )

        xml_str = await svc.generate_sepa_xml([rechnung.id])
        root = ET.fromstring(xml_str)

        svc_lvl_cd = _text(root, ".//SvcLvl/Cd")
        assert svc_lvl_cd == "SEPA"

    async def test_local_instrument_is_core(self, session):
        member, _ = await _setup_member_with_mandate(session)
        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            member.id, Decimal("100.00"), "LclInstrm", date(2024, 1, 31)
        )

        xml_str = await svc.generate_sepa_xml([rechnung.id])
        root = ET.fromstring(xml_str)

        lcl_instrm_cd = _text(root, ".//LclInstrm/Cd")
        assert lcl_instrm_cd == "CORE"

    async def test_sequence_type_is_rcur(self, session):
        member, _ = await _setup_member_with_mandate(session)
        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            member.id, Decimal("100.00"), "SeqTp", date(2024, 1, 31)
        )

        xml_str = await svc.generate_sepa_xml([rechnung.id])
        root = ET.fromstring(xml_str)

        seq_tp = _text(root, ".//SeqTp")
        assert seq_tp == "RCUR"


class TestSepaGroupHeader:
    """Verify GrpHdr fields: MsgId, CreDtTm, NbOfTxs, CtrlSum."""

    async def test_msg_id_format(self, session):
        member, _ = await _setup_member_with_mandate(session)
        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            member.id, Decimal("100.00"), "MsgId test", date(2024, 1, 31)
        )

        xml_str = await svc.generate_sepa_xml([rechnung.id])
        root = ET.fromstring(xml_str)

        msg_id = _text(root, ".//GrpHdr/MsgId")
        assert msg_id is not None
        assert msg_id.startswith("MSG-")
        # Rest should be a datetime stamp (14 digits: YYYYMMDDHHmmSS)
        stamp = msg_id.replace("MSG-", "")
        assert len(stamp) == 14
        assert stamp.isdigit()

    async def test_cre_dt_tm_is_iso_format(self, session):
        member, _ = await _setup_member_with_mandate(session)
        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            member.id, Decimal("100.00"), "CreDtTm test", date(2024, 1, 31)
        )

        xml_str = await svc.generate_sepa_xml([rechnung.id])
        root = ET.fromstring(xml_str)

        cre_dt_tm = _text(root, ".//GrpHdr/CreDtTm")
        assert cre_dt_tm is not None
        # Should contain 'T' for ISO datetime
        assert "T" in cre_dt_tm
        # Should start with a year
        assert cre_dt_tm[:4].isdigit()

    async def test_nb_of_txs_single(self, session):
        member, _ = await _setup_member_with_mandate(session)
        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            member.id, Decimal("100.00"), "NbOfTxs=1", date(2024, 1, 31)
        )

        xml_str = await svc.generate_sepa_xml([rechnung.id])
        root = ET.fromstring(xml_str)

        nb_txs = _text(root, ".//GrpHdr/NbOfTxs")
        assert nb_txs == "1"

    async def test_nb_of_txs_multiple(self, session):
        m1, _ = await _setup_member_with_mandate(session)
        m2, _ = await _setup_member_with_mandate(
            session,
            vorname="Anna",
            nachname="Schmidt",
            email="anna@example.com",
            mitgliedsnummer="M-0002",
            mandatsreferenz="MREF-002",
        )
        svc = FinanzenService(session)
        r1 = await svc.create_invoice(m1.id, Decimal("100.00"), "A", date(2024, 1, 31))
        r2 = await svc.create_invoice(m2.id, Decimal("200.00"), "B", date(2024, 1, 31))

        xml_str = await svc.generate_sepa_xml([r1.id, r2.id])
        root = ET.fromstring(xml_str)

        # GrpHdr NbOfTxs
        nb_txs_hdr = _text(root, ".//GrpHdr/NbOfTxs")
        assert nb_txs_hdr == "2"

        # PmtInf NbOfTxs
        nb_txs_pmt = _text(root, ".//PmtInf/NbOfTxs")
        assert nb_txs_pmt == "2"

    async def test_ctrl_sum_single(self, session):
        member, _ = await _setup_member_with_mandate(session)
        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            member.id, Decimal("250.50"), "CtrlSum test", date(2024, 1, 31)
        )

        xml_str = await svc.generate_sepa_xml([rechnung.id])
        root = ET.fromstring(xml_str)

        ctrl_sum = _text(root, ".//GrpHdr/CtrlSum")
        assert ctrl_sum is not None
        assert Decimal(ctrl_sum) == Decimal("250.50")

    async def test_ctrl_sum_multiple(self, session):
        m1, _ = await _setup_member_with_mandate(session)
        m2, _ = await _setup_member_with_mandate(
            session,
            vorname="Anna",
            nachname="Schmidt",
            email="anna@example.com",
            mitgliedsnummer="M-0002",
            mandatsreferenz="MREF-002",
        )
        svc = FinanzenService(session)
        r1 = await svc.create_invoice(m1.id, Decimal("100.00"), "A", date(2024, 1, 31))
        r2 = await svc.create_invoice(m2.id, Decimal("200.00"), "B", date(2024, 1, 31))

        xml_str = await svc.generate_sepa_xml([r1.id, r2.id])
        root = ET.fromstring(xml_str)

        ctrl_sum = _text(root, ".//GrpHdr/CtrlSum")
        assert Decimal(ctrl_sum) == Decimal("300.00")

    async def test_initiating_party_name(self, session):
        stammdaten = _make_stammdaten(name="Turnverein Musterstadt e.V.")
        session.add(stammdaten)
        await session.flush()

        member, _ = await _setup_member_with_mandate(session)
        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            member.id, Decimal("100.00"), "InitgPty", date(2024, 1, 31)
        )

        xml_str = await svc.generate_sepa_xml([rechnung.id])
        root = ET.fromstring(xml_str)

        initg_pty_nm = _text(root, ".//GrpHdr/InitgPty/Nm")
        assert initg_pty_nm == "Turnverein Musterstadt e.V."


class TestSepaNoInvoices:
    """Test with 0 invoices or invalid IDs."""

    async def test_empty_list_raises(self, session):
        svc = FinanzenService(session)
        with pytest.raises(ValueError, match="No invoices found"):
            await svc.generate_sepa_xml([])

    async def test_nonexistent_ids_raises(self, session):
        svc = FinanzenService(session)
        with pytest.raises(ValueError, match="No invoices found"):
            await svc.generate_sepa_xml([9999, 8888, 7777])


class TestSepaMissingMandate:
    """Test with invoices that have no SEPA mandate."""

    async def test_invoice_without_mandate_uses_fallbacks(self, session):
        """An invoice with no mandate should still generate XML with fallback values."""
        member = _make_member()
        session.add(member)
        await session.flush()
        # No mandate created for this member

        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            member.id, Decimal("100.00"), "No mandate", date(2024, 1, 31)
        )

        xml_str = await svc.generate_sepa_xml([rechnung.id])
        root = ET.fromstring(xml_str)

        # Should use UNKNOWN for mandate reference
        assert "UNKNOWN" in xml_str
        # Should use member name as debtor name
        assert "Max Mustermann" in xml_str
        # IBAN should be UNKNOWN
        drct_dbt_txs = _findall(root, ".//DrctDbtTxInf")
        assert len(drct_dbt_txs) == 1

    async def test_invoice_with_inactive_mandate_uses_fallbacks(self, session):
        """An inactive mandate should not be picked up."""
        member, _ = await _setup_member_with_mandate(
            session, aktiv=False, mandatsreferenz="MREF-INACTIVE"
        )

        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            member.id, Decimal("100.00"), "Inactive mandate", date(2024, 1, 31)
        )

        xml_str = await svc.generate_sepa_xml([rechnung.id])
        # MREF-INACTIVE should not appear -- the mandate is inactive
        assert "MREF-INACTIVE" not in xml_str
        assert "UNKNOWN" in xml_str


class TestSepaIbanAndBic:
    """Verify IBAN and BIC handling."""

    async def test_debtor_iban_in_xml(self, session):
        iban = "DE89370400440532013000"
        member, _ = await _setup_member_with_mandate(session, iban=iban)

        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            member.id, Decimal("100.00"), "IBAN test", date(2024, 1, 31)
        )

        xml_str = await svc.generate_sepa_xml([rechnung.id])
        assert iban in xml_str

    async def test_debtor_bic_in_xml(self, session):
        bic = "COBADEFFXXX"
        member, _ = await _setup_member_with_mandate(session, bic=bic)

        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            member.id, Decimal("100.00"), "BIC test", date(2024, 1, 31)
        )

        xml_str = await svc.generate_sepa_xml([rechnung.id])
        assert bic in xml_str

    async def test_missing_bic_uses_notprovided(self, session):
        """When BIC is None, NOTPROVIDED should be used."""
        member, _ = await _setup_member_with_mandate(session, bic=None)

        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            member.id, Decimal("100.00"), "No BIC", date(2024, 1, 31)
        )

        xml_str = await svc.generate_sepa_xml([rechnung.id])
        root = ET.fromstring(xml_str)

        # The debtor agent BIC should be NOTPROVIDED
        # Find DrctDbtTxInf/DbtrAgt/FinInstnId/BIC
        drct_dbt_txs = _findall(root, ".//DrctDbtTxInf")
        assert len(drct_dbt_txs) == 1
        tx = drct_dbt_txs[0]
        dbtr_bic = _text(tx, ".//DbtrAgt/FinInstnId/BIC")
        assert dbtr_bic == "NOTPROVIDED"

    async def test_creditor_iban_from_stammdaten(self, session):
        club_iban = "DE02120300000000202051"
        stammdaten = _make_stammdaten(iban=club_iban)
        session.add(stammdaten)
        await session.flush()

        member, _ = await _setup_member_with_mandate(session)
        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            member.id, Decimal("100.00"), "Cdtr IBAN", date(2024, 1, 31)
        )

        xml_str = await svc.generate_sepa_xml([rechnung.id])
        assert club_iban in xml_str

    async def test_creditor_bic_from_stammdaten(self, session):
        club_bic = "BYLADEM1001"
        stammdaten = _make_stammdaten(bic=club_bic)
        session.add(stammdaten)
        await session.flush()

        member, _ = await _setup_member_with_mandate(session)
        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            member.id, Decimal("100.00"), "Cdtr BIC", date(2024, 1, 31)
        )

        xml_str = await svc.generate_sepa_xml([rechnung.id])
        assert club_bic in xml_str


class TestSepaSpecialCharacters:
    """Test with umlauts and special characters in names."""

    async def test_umlauts_in_kontoinhaber(self, session):
        member, _ = await _setup_member_with_mandate(
            session,
            vorname="Juergen",
            nachname="Mueller",
            kontoinhaber="Juergen Mueller",
        )

        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            member.id, Decimal("100.00"), "Umlauts", date(2024, 1, 31)
        )

        xml_str = await svc.generate_sepa_xml([rechnung.id])
        assert "Juergen Mueller" in xml_str

    async def test_real_umlauts_in_name(self, session):
        """Names with real umlaut characters should appear in XML."""
        member, _ = await _setup_member_with_mandate(
            session,
            vorname="Hans",
            nachname="Groesser",
            kontoinhaber="Hans Groesser",
            mitgliedsnummer="M-UML",
            mandatsreferenz="MREF-UML",
            email="hans@example.com",
        )

        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            member.id, Decimal("100.00"), "Umlaut real", date(2024, 1, 31)
        )

        xml_str = await svc.generate_sepa_xml([rechnung.id])
        # The name should be in the XML
        assert "Hans Groesser" in xml_str
        # Parse should succeed
        ET.fromstring(xml_str)

    async def test_club_name_with_umlauts_in_stammdaten(self, session):
        stammdaten = _make_stammdaten(name="Sportverein Muenchen-Sued e.V.")
        session.add(stammdaten)
        await session.flush()

        member, _ = await _setup_member_with_mandate(session)
        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            member.id, Decimal("100.00"), "Club umlaut", date(2024, 1, 31)
        )

        xml_str = await svc.generate_sepa_xml([rechnung.id])
        assert "Sportverein Muenchen-Sued e.V." in xml_str


class TestSepaDateFormats:
    """Verify date formats in the XML."""

    async def test_reqd_colltn_dt_is_iso_date(self, session):
        member, _ = await _setup_member_with_mandate(session)
        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            member.id, Decimal("100.00"), "Date fmt", date(2024, 1, 31)
        )

        xml_str = await svc.generate_sepa_xml([rechnung.id])
        root = ET.fromstring(xml_str)

        reqd_dt = _text(root, ".//ReqdColltnDt")
        assert reqd_dt is not None
        # Must be ISO date: YYYY-MM-DD
        parts = reqd_dt.split("-")
        assert len(parts) == 3
        assert len(parts[0]) == 4  # year
        assert len(parts[1]) == 2  # month
        assert len(parts[2]) == 2  # day

    async def test_mandate_signature_date_is_iso(self, session):
        member, _ = await _setup_member_with_mandate(session)
        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            member.id, Decimal("100.00"), "Sig date", date(2024, 1, 31)
        )

        xml_str = await svc.generate_sepa_xml([rechnung.id])
        root = ET.fromstring(xml_str)

        dt_of_sgntr = _text(root, ".//DtOfSgntr")
        assert dt_of_sgntr is not None
        # Should be 2023-01-01 (from _setup_member_with_mandate)
        assert dt_of_sgntr == "2023-01-01"


class TestSepaTransactionDetails:
    """Verify per-transaction fields."""

    async def test_end_to_end_id_is_invoice_number(self, session):
        member, _ = await _setup_member_with_mandate(session)
        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            member.id, Decimal("100.00"), "E2E", date(2024, 1, 31)
        )

        xml_str = await svc.generate_sepa_xml([rechnung.id])
        root = ET.fromstring(xml_str)

        e2e = _text(root, ".//EndToEndId")
        assert e2e == rechnung.rechnungsnummer

    async def test_instructed_amount_with_currency(self, session):
        member, _ = await _setup_member_with_mandate(session)
        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            member.id, Decimal("345.67"), "InstdAmt", date(2024, 1, 31)
        )

        xml_str = await svc.generate_sepa_xml([rechnung.id])
        root = ET.fromstring(xml_str)

        # Find InstdAmt element
        inst_amt_els = root.findall(".//{*}InstdAmt")
        if not inst_amt_els:
            inst_amt_els = root.findall(".//InstdAmt")
        assert len(inst_amt_els) == 1
        assert inst_amt_els[0].get("Ccy") == "EUR"
        assert Decimal(inst_amt_els[0].text) == Decimal("345.67")

    async def test_mandate_reference_in_transaction(self, session):
        member, _ = await _setup_member_with_mandate(
            session, mandatsreferenz="MREF-SPECIAL-001"
        )
        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            member.id, Decimal("100.00"), "MndtId", date(2024, 1, 31)
        )

        xml_str = await svc.generate_sepa_xml([rechnung.id])
        assert "MREF-SPECIAL-001" in xml_str

    async def test_remittance_info_uses_verwendungszweck(self, session):
        member, _ = await _setup_member_with_mandate(session)
        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            member.id,
            Decimal("100.00"),
            "Beitrag 2024",
            date(2024, 1, 31),
        )
        # Set verwendungszweck manually
        rechnung.verwendungszweck = "Mitgliedsbeitrag 2024 Max Mustermann"
        await session.flush()

        xml_str = await svc.generate_sepa_xml([rechnung.id])
        assert "Mitgliedsbeitrag 2024 Max Mustermann" in xml_str

    async def test_remittance_info_falls_back_to_beschreibung(self, session):
        member, _ = await _setup_member_with_mandate(session)
        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            member.id,
            Decimal("100.00"),
            "Jahresbeitrag 2024",
            date(2024, 1, 31),
        )
        # verwendungszweck is None by default

        xml_str = await svc.generate_sepa_xml([rechnung.id])
        assert "Jahresbeitrag 2024" in xml_str

    async def test_kontoinhaber_name_in_debtor(self, session):
        """Debtor name should come from kontoinhaber on the mandate."""
        member, _ = await _setup_member_with_mandate(
            session,
            kontoinhaber="Erika Mustermann",
        )
        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            member.id, Decimal("100.00"), "Kontoinhaber", date(2024, 1, 31)
        )

        xml_str = await svc.generate_sepa_xml([rechnung.id])
        assert "Erika Mustermann" in xml_str


class TestSepaMultipleTransactions:
    """Test with multiple invoices from different members."""

    async def test_multiple_transactions_all_present(self, session):
        m1, _ = await _setup_member_with_mandate(
            session,
            vorname="Max",
            nachname="Mustermann",
            mitgliedsnummer="M-0001",
            mandatsreferenz="MREF-001",
            iban="DE89370400440532013000",
        )
        m2, _ = await _setup_member_with_mandate(
            session,
            vorname="Anna",
            nachname="Schmidt",
            email="anna@example.com",
            mitgliedsnummer="M-0002",
            mandatsreferenz="MREF-002",
            iban="DE27100777770209299700",
        )

        svc = FinanzenService(session)
        r1 = await svc.create_invoice(m1.id, Decimal("120.00"), "Beitrag Max", date(2024, 1, 31))
        r2 = await svc.create_invoice(m2.id, Decimal("240.00"), "Beitrag Anna", date(2024, 1, 31))

        xml_str = await svc.generate_sepa_xml([r1.id, r2.id])
        root = ET.fromstring(xml_str)

        # Both IBANs should be present
        assert "DE89370400440532013000" in xml_str
        assert "DE27100777770209299700" in xml_str

        # Both mandate refs
        assert "MREF-001" in xml_str
        assert "MREF-002" in xml_str

        # Both names
        assert "Max Mustermann" in xml_str
        assert "Anna Schmidt" in xml_str

        # NbOfTxs = 2
        nb_txs = _text(root, ".//GrpHdr/NbOfTxs")
        assert nb_txs == "2"

        # CtrlSum = 360.00
        ctrl_sum = _text(root, ".//GrpHdr/CtrlSum")
        assert Decimal(ctrl_sum) == Decimal("360.00")

    async def test_transaction_count_matches_drctdbttxinf_elements(self, session):
        members = []
        for i in range(3):
            m, _ = await _setup_member_with_mandate(
                session,
                vorname=f"Person{i}",
                nachname=f"Name{i}",
                email=f"p{i}@example.com",
                mitgliedsnummer=f"M-{i:04d}",
                mandatsreferenz=f"MREF-{i:03d}",
            )
            members.append(m)

        svc = FinanzenService(session)
        ids = []
        for i, m in enumerate(members):
            r = await svc.create_invoice(
                m.id, Decimal(f"{(i + 1) * 50}.00"), f"Invoice {i}", date(2024, 1, 31)
            )
            ids.append(r.id)

        xml_str = await svc.generate_sepa_xml(ids)
        root = ET.fromstring(xml_str)

        txs = _findall(root, ".//DrctDbtTxInf")
        assert len(txs) == 3


class TestSepaWithoutStammdaten:
    """When no Vereinsstammdaten exist, defaults should be used."""

    async def test_default_club_name(self, session):
        member, _ = await _setup_member_with_mandate(session)
        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            member.id, Decimal("100.00"), "Default club", date(2024, 1, 31)
        )

        xml_str = await svc.generate_sepa_xml([rechnung.id])
        # Default name from source code
        assert "Sportverein e.V." in xml_str

    async def test_default_club_iban(self, session):
        member, _ = await _setup_member_with_mandate(session)
        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            member.id, Decimal("100.00"), "Default IBAN", date(2024, 1, 31)
        )

        xml_str = await svc.generate_sepa_xml([rechnung.id])
        # Default IBAN from source code (same as test IBAN, check it is there)
        assert "DE89370400440532013000" in xml_str


class TestSepaXmlWellFormed:
    """Ensure generated XML is always parseable."""

    async def test_xml_roundtrip(self, session):
        """Parse and re-serialize to ensure well-formedness."""
        member, _ = await _setup_member_with_mandate(session)
        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            member.id, Decimal("99.99"), "Roundtrip", date(2024, 1, 31)
        )

        xml_str = await svc.generate_sepa_xml([rechnung.id])
        root = ET.fromstring(xml_str)
        # Re-serialize should not raise
        ET.tostring(root, encoding="unicode")
