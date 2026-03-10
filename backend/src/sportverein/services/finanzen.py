from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sportverein.models.beitrag import SepaMandat
from sportverein.models.finanzen import (
    Buchung,
    Kostenstelle,
    Rechnung,
    RechnungStatus,
    Sphare,
    Spendenbescheinigung,
    Zahlung,
    Zahlungsart,
)
from sportverein.models.mitglied import Mitglied


class FinanzenService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # -- Bookings ------------------------------------------------------------

    async def create_booking(self, data: dict[str, Any]) -> Buchung:
        """Create a booking with sphere validation."""
        sphare_value = data.get("sphare")
        if isinstance(sphare_value, str):
            try:
                sphare_value = Sphare(sphare_value)
            except ValueError:
                raise ValueError(
                    f"Invalid sphere: {sphare_value}. "
                    f"Must be one of: {[s.value for s in Sphare]}"
                )
        elif isinstance(sphare_value, Sphare):
            pass
        else:
            raise ValueError("Sphere (sphare) is required")

        buchung = Buchung(
            buchungsdatum=data["buchungsdatum"],
            betrag=data["betrag"],
            beschreibung=data["beschreibung"],
            konto=data["konto"],
            gegenkonto=data["gegenkonto"],
            sphare=sphare_value,
            mitglied_id=data.get("mitglied_id"),
        )
        self.session.add(buchung)
        await self.session.flush()
        await self.session.refresh(buchung)
        return buchung

    async def get_bookings(
        self,
        filters: dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Buchung], int]:
        """List bookings with optional filters and pagination."""
        query = select(Buchung)
        count_query = select(func.count()).select_from(Buchung)

        conditions = []
        if filters:
            if filters.get("date_from"):
                conditions.append(Buchung.buchungsdatum >= filters["date_from"])
            if filters.get("date_to"):
                conditions.append(Buchung.buchungsdatum <= filters["date_to"])
            if filters.get("sphare"):
                sph = filters["sphare"]
                if isinstance(sph, str):
                    sph = Sphare(sph)
                conditions.append(Buchung.sphare == sph)
            if filters.get("mitglied_id"):
                conditions.append(Buchung.mitglied_id == filters["mitglied_id"])

        if conditions:
            query = query.where(*conditions)
            count_query = count_query.where(*conditions)

        total_result = await self.session.execute(count_query)
        total = total_result.scalar_one()

        query = query.order_by(Buchung.buchungsdatum.desc())
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.session.execute(query)
        bookings = list(result.scalars().all())
        return bookings, total

    async def get_balance_by_sphere(self) -> dict[str, Decimal]:
        """Sum of bookings grouped by sphere."""
        result = await self.session.execute(
            select(Buchung.sphare, func.sum(Buchung.betrag)).group_by(Buchung.sphare)
        )
        return {row[0].value if isinstance(row[0], Sphare) else row[0]: row[1] or Decimal("0.00") for row in result.all()}

    async def get_total_balance(self) -> Decimal:
        """Overall balance (sum of all bookings)."""
        result = await self.session.execute(select(func.sum(Buchung.betrag)))
        return result.scalar_one() or Decimal("0.00")

    # -- Invoices ------------------------------------------------------------

    async def _next_rechnungsnummer(self) -> str:
        result = await self.session.execute(
            select(Rechnung.rechnungsnummer)
            .order_by(Rechnung.rechnungsnummer.desc())
            .limit(1)
        )
        last = result.scalar_one_or_none()
        if last is not None:
            num = int(last.split("-")[1])
            return f"R-{num + 1:04d}"
        return "R-0001"

    async def create_invoice(
        self,
        mitglied_id: int,
        betrag: Decimal,
        beschreibung: str,
        faelligkeitsdatum: date,
        rechnungsdatum: date | None = None,
    ) -> Rechnung:
        """Create an invoice with auto-generated number."""
        nummer = await self._next_rechnungsnummer()
        rechnung = Rechnung(
            rechnungsnummer=nummer,
            mitglied_id=mitglied_id,
            betrag=betrag,
            beschreibung=beschreibung,
            rechnungsdatum=rechnungsdatum or date.today(),
            faelligkeitsdatum=faelligkeitsdatum,
            status=RechnungStatus.offen,
        )
        self.session.add(rechnung)
        await self.session.flush()
        await self.session.refresh(rechnung)
        return rechnung

    async def get_invoices(
        self,
        filters: dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Rechnung], int]:
        """List invoices with optional filters and pagination."""
        query = select(Rechnung)
        count_query = select(func.count()).select_from(Rechnung)

        conditions = []
        if filters:
            if filters.get("mitglied_id"):
                conditions.append(Rechnung.mitglied_id == filters["mitglied_id"])
            if filters.get("status"):
                status = filters["status"]
                if isinstance(status, str):
                    status = RechnungStatus(status)
                conditions.append(Rechnung.status == status)

        if conditions:
            query = query.where(*conditions)
            count_query = count_query.where(*conditions)

        total_result = await self.session.execute(count_query)
        total = total_result.scalar_one()

        query = query.order_by(Rechnung.rechnungsdatum.desc())
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.session.execute(query)
        invoices = list(result.scalars().all())
        return invoices, total

    # -- Payments ------------------------------------------------------------

    async def record_payment(
        self,
        rechnung_id: int,
        betrag: Decimal,
        zahlungsart: Zahlungsart | str,
        referenz: str | None = None,
    ) -> Zahlung:
        """Record a payment against an invoice, updating status if fully paid."""
        if isinstance(zahlungsart, str):
            zahlungsart = Zahlungsart(zahlungsart)

        result = await self.session.execute(
            select(Rechnung).where(Rechnung.id == rechnung_id)
        )
        rechnung = result.scalar_one()

        zahlung = Zahlung(
            rechnung_id=rechnung_id,
            betrag=betrag,
            zahlungsdatum=date.today(),
            zahlungsart=zahlungsart,
            referenz=referenz,
        )
        self.session.add(zahlung)
        await self.session.flush()

        # Check total payments
        pay_result = await self.session.execute(
            select(func.sum(Zahlung.betrag)).where(Zahlung.rechnung_id == rechnung_id)
        )
        total_paid = pay_result.scalar_one() or Decimal("0.00")

        if total_paid >= rechnung.betrag:
            rechnung.status = RechnungStatus.bezahlt
            await self.session.flush()

        await self.session.refresh(zahlung)
        return zahlung

    # -- Overdue invoices ----------------------------------------------------

    async def get_overdue_invoices(self) -> list[Rechnung]:
        """Invoices past due date that are still open."""
        result = await self.session.execute(
            select(Rechnung).where(
                Rechnung.status == RechnungStatus.offen,
                Rechnung.faelligkeitsdatum < date.today(),
            )
        )
        return list(result.scalars().all())

    # -- SEPA XML generation -------------------------------------------------

    async def generate_sepa_xml(self, rechnungen_ids: list[int]) -> str:
        """Generate SEPA pain.008.001.02 XML for direct debit collection."""
        # Load invoices
        result = await self.session.execute(
            select(Rechnung).where(Rechnung.id.in_(rechnungen_ids))
        )
        rechnungen = list(result.scalars().all())
        if not rechnungen:
            raise ValueError("No invoices found for the given IDs")

        # Load SEPA mandates for all members in these invoices
        mitglied_ids = [r.mitglied_id for r in rechnungen]
        mandate_result = await self.session.execute(
            select(SepaMandat).where(
                SepaMandat.mitglied_id.in_(mitglied_ids),
                SepaMandat.aktiv == True,  # noqa: E712
            )
        )
        mandate_map: dict[int, SepaMandat] = {
            m.mitglied_id: m for m in mandate_result.scalars().all()
        }

        # Load member data
        member_result = await self.session.execute(
            select(Mitglied).where(Mitglied.id.in_(mitglied_ids))
        )
        member_map: dict[int, Mitglied] = {
            m.id: m for m in member_result.scalars().all()
        }

        # Build XML
        ns = "urn:iso:std:iso:20022:tech:xsd:pain.008.001.02"
        root = ET.Element("Document", xmlns=ns)
        cstmr_ddr = ET.SubElement(root, "CstmrDrctDbtInitn")

        # Group Header
        grp_hdr = ET.SubElement(cstmr_ddr, "GrpHdr")
        ET.SubElement(grp_hdr, "MsgId").text = f"MSG-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        ET.SubElement(grp_hdr, "CreDtTm").text = datetime.now().isoformat()
        ET.SubElement(grp_hdr, "NbOfTxs").text = str(len(rechnungen))
        ctrl_sum = sum(r.betrag for r in rechnungen)
        ET.SubElement(grp_hdr, "CtrlSum").text = str(ctrl_sum)
        initg_pty = ET.SubElement(grp_hdr, "InitgPty")
        ET.SubElement(initg_pty, "Nm").text = "Sportverein e.V."

        # Payment Information
        pmt_inf = ET.SubElement(cstmr_ddr, "PmtInf")
        ET.SubElement(pmt_inf, "PmtInfId").text = f"PMT-{datetime.now().strftime('%Y%m%d')}"
        ET.SubElement(pmt_inf, "PmtMtd").text = "DD"
        ET.SubElement(pmt_inf, "NbOfTxs").text = str(len(rechnungen))
        ET.SubElement(pmt_inf, "CtrlSum").text = str(ctrl_sum)

        pmt_tp_inf = ET.SubElement(pmt_inf, "PmtTpInf")
        svc_lvl = ET.SubElement(pmt_tp_inf, "SvcLvl")
        ET.SubElement(svc_lvl, "Cd").text = "SEPA"
        lcl_instrm = ET.SubElement(pmt_tp_inf, "LclInstrm")
        ET.SubElement(lcl_instrm, "Cd").text = "CORE"
        ET.SubElement(pmt_tp_inf, "SeqTp").text = "RCUR"

        ET.SubElement(pmt_inf, "ReqdColltnDt").text = date.today().isoformat()

        cdtr = ET.SubElement(pmt_inf, "Cdtr")
        ET.SubElement(cdtr, "Nm").text = "Sportverein e.V."

        cdtr_acct = ET.SubElement(pmt_inf, "CdtrAcct")
        cdtr_id = ET.SubElement(cdtr_acct, "Id")
        ET.SubElement(cdtr_id, "IBAN").text = "DE89370400440532013000"

        cdtr_agt = ET.SubElement(pmt_inf, "CdtrAgt")
        fin_instn = ET.SubElement(cdtr_agt, "FinInstnId")
        ET.SubElement(fin_instn, "BIC").text = "COBADEFFXXX"

        # Transactions
        for rechnung in rechnungen:
            mandat = mandate_map.get(rechnung.mitglied_id)
            member = member_map.get(rechnung.mitglied_id)

            drct_dbt_tx = ET.SubElement(pmt_inf, "DrctDbtTxInf")

            pmt_id = ET.SubElement(drct_dbt_tx, "PmtId")
            ET.SubElement(pmt_id, "EndToEndId").text = rechnung.rechnungsnummer

            inst_amt = ET.SubElement(drct_dbt_tx, "InstdAmt", Ccy="EUR")
            inst_amt.text = str(rechnung.betrag)

            ddt = ET.SubElement(drct_dbt_tx, "DrctDbtTx")
            mndt_rltd = ET.SubElement(ddt, "MndtRltdInf")
            ET.SubElement(mndt_rltd, "MndtId").text = (
                mandat.mandatsreferenz if mandat else "UNKNOWN"
            )
            ET.SubElement(mndt_rltd, "DtOfSgntr").text = (
                mandat.unterschriftsdatum.isoformat() if mandat else "2024-01-01"
            )

            dbtr_agt = ET.SubElement(drct_dbt_tx, "DbtrAgt")
            dbtr_fin = ET.SubElement(dbtr_agt, "FinInstnId")
            ET.SubElement(dbtr_fin, "BIC").text = (
                mandat.bic if mandat and mandat.bic else "NOTPROVIDED"
            )

            dbtr = ET.SubElement(drct_dbt_tx, "Dbtr")
            ET.SubElement(dbtr, "Nm").text = (
                mandat.kontoinhaber
                if mandat
                else (f"{member.vorname} {member.nachname}" if member else "Unknown")
            )

            dbtr_acct = ET.SubElement(drct_dbt_tx, "DbtrAcct")
            dbtr_acct_id = ET.SubElement(dbtr_acct, "Id")
            ET.SubElement(dbtr_acct_id, "IBAN").text = (
                mandat.iban if mandat else "UNKNOWN"
            )

            rmt_inf = ET.SubElement(drct_dbt_tx, "RmtInf")
            ET.SubElement(rmt_inf, "Ustrd").text = rechnung.beschreibung

        return ET.tostring(root, encoding="unicode", xml_declaration=True)

    # -- Cost centers --------------------------------------------------------

    async def get_cost_centers(self) -> list[Kostenstelle]:
        """List all cost centers."""
        result = await self.session.execute(
            select(Kostenstelle).order_by(Kostenstelle.name)
        )
        return list(result.scalars().all())

    async def get_budget_status(self, kostenstelle_id: int) -> dict:
        """Get budget status for a cost center."""
        result = await self.session.execute(
            select(Kostenstelle).where(Kostenstelle.id == kostenstelle_id)
        )
        ks = result.scalar_one_or_none()
        if ks is None:
            raise ValueError(f"Kostenstelle {kostenstelle_id} not found")

        spent_result = await self.session.execute(
            select(func.sum(Buchung.betrag)).where(
                Buchung.kostenstelle_id == kostenstelle_id
            )
        )
        spent = spent_result.scalar_one() or Decimal("0.00")
        budget = ks.budget or Decimal("0.00")
        remaining = budget - spent

        return {
            "kostenstelle_id": ks.id,
            "name": ks.name,
            "budget": budget,
            "spent": spent,
            "remaining": remaining,
        }

    # -- Donation receipts ---------------------------------------------------

    async def create_donation_receipt(
        self,
        mitglied_id: int,
        betrag: Decimal,
        zweck: str,
    ) -> Spendenbescheinigung:
        """Create a donation receipt."""
        bescheinigung = Spendenbescheinigung(
            mitglied_id=mitglied_id,
            betrag=betrag,
            ausstellungsdatum=date.today(),
            zweck=zweck,
        )
        self.session.add(bescheinigung)
        await self.session.flush()
        await self.session.refresh(bescheinigung)
        return bescheinigung
