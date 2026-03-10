"""Agent workflow services for automated club management tasks."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sportverein.models.beitrag import SepaMandat
from sportverein.services.beitraege import BeitraegeService
from sportverein.services.ehrenamt import EhrenamtService
from sportverein.services.finanzen import FinanzenService


class BeitragseinzugAgent:
    """Orchestrates the fee collection process."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def run(self, year: int, month: int) -> dict[str, Any]:
        """Run the fee collection workflow.

        1. Calculate fees for all active members
        2. Identify members without SEPA mandate
        3. Generate SEPA XML for members with mandates
        4. Return summary
        """
        beitraege_svc = BeitraegeService(self.session)
        finanzen_svc = FinanzenService(self.session)

        # Step 1: Calculate fees
        fees = await beitraege_svc.calculate_all_fees(year)

        # Step 2: Load all active SEPA mandates
        mandate_result = await self.session.execute(
            select(SepaMandat).where(SepaMandat.aktiv == True)  # noqa: E712
        )
        mandate_map: dict[int, SepaMandat] = {
            m.mitglied_id: m for m in mandate_result.scalars().all()
        }

        # Step 3: Create invoices and separate by mandate status
        sepa_invoice_ids: list[int] = []
        missing_mandate_members: list[dict[str, Any]] = []

        for fee in fees:
            if fee["prorata_betrag"] <= Decimal("0.00"):
                continue

            rechnung = await finanzen_svc.create_invoice(
                mitglied_id=fee["member_id"],
                betrag=fee["prorata_betrag"],
                beschreibung=f"Mitgliedsbeitrag {year}/{month:02d}",
                faelligkeitsdatum=date(year, month, 28),
                rechnungsdatum=date(year, month, 1),
            )

            if fee["member_id"] in mandate_map:
                sepa_invoice_ids.append(rechnung.id)
            else:
                missing_mandate_members.append({
                    "member_id": fee["member_id"],
                    "name": fee["name"],
                    "betrag": float(fee["prorata_betrag"]),
                    "rechnung_id": rechnung.id,
                })

        # Step 4: Generate SEPA XML if there are mandated invoices
        sepa_xml: str | None = None
        if sepa_invoice_ids:
            sepa_xml = await finanzen_svc.generate_sepa_xml(sepa_invoice_ids)

        return {
            "year": year,
            "month": month,
            "fees_calculated": len(fees),
            "invoices_created": len(sepa_invoice_ids) + len(missing_mandate_members),
            "sepa_ready": len(sepa_invoice_ids),
            "missing_mandate": missing_mandate_members,
            "sepa_xml": sepa_xml,
        }


class MahnwesenAgent:
    """Orchestrates the dunning (Mahnwesen) process."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def run(self) -> dict[str, Any]:
        """Run the dunning workflow.

        1. Get overdue invoices
        2. Categorize by dunning level (1: 30d, 2: 60d, 3: 90d)
        3. Return structured report with recommended actions
        """
        finanzen_svc = FinanzenService(self.session)
        overdue = await finanzen_svc.get_overdue_invoices()
        today = date.today()

        levels: dict[int, list[dict[str, Any]]] = {1: [], 2: [], 3: []}
        actions: dict[int, str] = {
            1: "Zahlungserinnerung versenden",
            2: "Zweite Mahnung mit Mahngebühr versenden",
            3: "Letzte Mahnung — Inkasso/Vereinsausschluss prüfen",
        }

        for rechnung in overdue:
            days_overdue = (today - rechnung.faelligkeitsdatum).days
            if days_overdue >= 90:
                level = 3
            elif days_overdue >= 60:
                level = 2
            elif days_overdue >= 30:
                level = 1
            else:
                continue

            levels[level].append({
                "rechnung_id": rechnung.id,
                "rechnungsnummer": rechnung.rechnungsnummer,
                "mitglied_id": rechnung.mitglied_id,
                "betrag": float(rechnung.betrag),
                "faelligkeitsdatum": rechnung.faelligkeitsdatum.isoformat(),
                "days_overdue": days_overdue,
            })

        total_overdue = sum(len(v) for v in levels.values())
        report: list[dict[str, Any]] = []
        for level_num in (1, 2, 3):
            if levels[level_num]:
                report.append({
                    "mahnstufe": level_num,
                    "action": actions[level_num],
                    "count": len(levels[level_num]),
                    "rechnungen": levels[level_num],
                })

        return {
            "total_overdue": total_overdue,
            "report": report,
        }


class AufwandMonitorAgent:
    """Monitors volunteer compensation limits."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def run(self) -> dict[str, Any]:
        """Run the compensation monitor.

        1. Get warnings from EhrenamtService
        2. Return list of members approaching limits with projections
        """
        svc = EhrenamtService(self.session)
        year = date.today().year
        warnings = await svc.get_warnings(year)

        # Add projections: estimate year-end total based on current pace
        today = date.today()
        day_of_year = today.timetuple().tm_yday
        days_in_year = 366 if (today.year % 4 == 0 and (today.year % 100 != 0 or today.year % 400 == 0)) else 365
        fraction_elapsed = Decimal(str(day_of_year)) / Decimal(str(days_in_year))

        for w in warnings:
            total = w["total"]
            if fraction_elapsed > Decimal("0"):
                projected = (total / fraction_elapsed).quantize(Decimal("0.01"))
            else:
                projected = total
            w["projected_year_end"] = float(projected)
            w["total"] = float(total)
            w["limit"] = float(w["limit"])

        return {
            "year": year,
            "warnings": warnings,
            "count": len(warnings),
        }
