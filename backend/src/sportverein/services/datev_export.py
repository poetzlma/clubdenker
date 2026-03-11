"""DATEV CSV export service for Buchungen and Rechnungen.

Produces CSV files compatible with DATEV import:
- Encoding: Windows-1252
- Separator: semicolon (;)
- Decimal separator: comma (,)
- Date format: DDMM (4 digits, no separator)
"""

from __future__ import annotations

import csv
import io
from datetime import date
from decimal import Decimal

from sqlalchemy import extract, select
from sqlalchemy.ext.asyncio import AsyncSession

from sportverein.models.finanzen import Buchung, Kostenstelle, Rechnung


def _format_decimal(value: Decimal) -> str:
    """Format a Decimal for DATEV: two decimal places, comma separator."""
    formatted = f"{abs(value):.2f}"
    return formatted.replace(".", ",")


def _format_date_datev(d: date) -> str:
    """Format a date as DDMM (4 digits, no separator)."""
    return f"{d.day:02d}{d.month:02d}"


class DatevExportService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def export_buchungen_csv(self, year: int, month: int | None = None) -> bytes:
        """Export bookings in DATEV Buchungsstapel format.

        Returns CSV as bytes encoded in Windows-1252.
        """
        stmt = select(Buchung).where(extract("year", Buchung.buchungsdatum) == year)
        if month is not None:
            stmt = stmt.where(extract("month", Buchung.buchungsdatum) == month)
        stmt = stmt.order_by(Buchung.buchungsdatum, Buchung.id)

        result = await self.session.execute(stmt)
        buchungen = result.scalars().all()

        # Build a kostenstelle lookup for IDs -> names
        ks_ids = {b.kostenstelle_id for b in buchungen if b.kostenstelle_id}
        ks_map: dict[int, str] = {}
        if ks_ids:
            ks_result = await self.session.execute(
                select(Kostenstelle).where(Kostenstelle.id.in_(ks_ids))
            )
            for ks in ks_result.scalars().all():
                ks_map[ks.id] = ks.name

        columns = [
            "Umsatz (S/H)",
            "Konto",
            "Gegenkonto",
            "BU-Schluessel",
            "Belegdatum",
            "Belegfeld1",
            "Buchungstext",
            "Kostenstelle",
        ]

        buf = io.StringIO()
        writer = csv.writer(buf, delimiter=";", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(columns)

        for b in buchungen:
            # S = Soll (debit), H = Haben (credit)
            if b.betrag >= 0:
                umsatz = _format_decimal(b.betrag)
                s_h = "S"
            else:
                umsatz = _format_decimal(b.betrag)
                s_h = "H"
            umsatz_sh = f"{umsatz} {s_h}"

            belegdatum = _format_date_datev(b.buchungsdatum)
            belegfeld1 = str(b.id)
            buchungstext = b.beschreibung[:60]  # DATEV limit
            kostenstelle = ks_map.get(b.kostenstelle_id, "") if b.kostenstelle_id else ""

            writer.writerow(
                [
                    umsatz_sh,
                    b.konto,
                    b.gegenkonto,
                    "",  # BU-Schluessel (tax key) -- left empty for nonprofit
                    belegdatum,
                    belegfeld1,
                    buchungstext,
                    kostenstelle,
                ]
            )

        return buf.getvalue().encode("windows-1252", errors="replace")

    async def export_rechnungen_csv(self, year: int) -> bytes:
        """Export outgoing invoices for DATEV.

        Returns CSV as bytes encoded in Windows-1252.
        """
        stmt = (
            select(Rechnung)
            .where(extract("year", Rechnung.rechnungsdatum) == year)
            .order_by(Rechnung.rechnungsdatum, Rechnung.id)
        )

        result = await self.session.execute(stmt)
        rechnungen = result.scalars().all()

        columns = [
            "Rechnungsnummer",
            "Datum",
            "Kunde",
            "Netto",
            "USt",
            "Brutto",
            "Status",
        ]

        buf = io.StringIO()
        writer = csv.writer(buf, delimiter=";", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(columns)

        for r in rechnungen:
            datum = _format_date_datev(r.rechnungsdatum)
            kunde = r.empfaenger_name or ""
            netto = _format_decimal(r.summe_netto)
            ust = _format_decimal(r.summe_steuer)
            brutto = _format_decimal(r.betrag)
            invoice_status = r.status.value if hasattr(r.status, "value") else str(r.status)

            writer.writerow(
                [
                    r.rechnungsnummer,
                    datum,
                    kunde,
                    netto,
                    ust,
                    brutto,
                    invoice_status,
                ]
            )

        return buf.getvalue().encode("windows-1252", errors="replace")
