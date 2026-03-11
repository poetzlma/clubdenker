"""Dashboard aggregation service for Sportverein."""

from __future__ import annotations

import hashlib
import random
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sportverein.models.beitrag import SepaMandat
from sportverein.models.finanzen import (
    Buchung,
    Kostenstelle,
    Rechnung,
    RechnungStatus,
    Sphare,
)
from sportverein.models.mitglied import (
    Abteilung,
    Mitglied,
    MitgliedAbteilung,
    MitgliedStatus,
)


class DashboardService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # -----------------------------------------------------------------------
    # Vorstand Dashboard
    # -----------------------------------------------------------------------

    async def get_vorstand_dashboard(self) -> dict[str, Any]:
        """Strategic overview for the board (Vorstand)."""
        kpis = await self._vorstand_kpis()
        member_trend = await self._member_trend()
        cashflow = await self._cashflow(months=6)
        open_actions = await self._open_actions()

        return {
            "kpis": kpis,
            "member_trend": member_trend,
            "cashflow": cashflow,
            "open_actions": open_actions,
        }

    async def _vorstand_kpis(self) -> dict[str, Any]:
        # Active members
        active_result = await self.session.execute(
            select(func.count())
            .select_from(Mitglied)
            .where(Mitglied.status == MitgliedStatus.aktiv)
        )
        active_members = active_result.scalar_one()

        # Total balance
        balance_result = await self.session.execute(select(func.sum(Buchung.betrag)))
        total_balance = float(balance_result.scalar_one() or Decimal("0.00"))

        # Open fees
        open_result = await self.session.execute(
            select(
                func.count(),
                func.coalesce(func.sum(Rechnung.betrag), Decimal("0.00")),
            ).where(
                Rechnung.status.in_(
                    [
                        RechnungStatus.entwurf,
                        RechnungStatus.gestellt,
                        RechnungStatus.faellig,
                        RechnungStatus.teilbezahlt,
                        RechnungStatus.mahnung_1,
                        RechnungStatus.mahnung_2,
                        RechnungStatus.mahnung_3,
                    ]
                )
            )
        )
        row = open_result.one()
        open_fees_count = row[0]
        open_fees_amount = float(row[1])

        # Compliance score: % of active members with active SEPA mandate
        mandate_result = await self.session.execute(
            select(func.count(func.distinct(SepaMandat.mitglied_id))).where(
                SepaMandat.aktiv == True,  # noqa: E712
            )
        )
        mandates_count = mandate_result.scalar_one()
        compliance_score = (
            round(mandates_count / active_members * 100, 1) if active_members > 0 else 0.0
        )

        return {
            "active_members": active_members,
            "total_balance": total_balance,
            "open_fees_count": open_fees_count,
            "open_fees_amount": open_fees_amount,
            "compliance_score": compliance_score,
        }

    async def _member_trend(self) -> list[dict[str, Any]]:
        """12 monthly data points with totals per Abteilung."""
        today = date.today()
        # Get all departments
        dept_result = await self.session.execute(
            select(Abteilung.id, Abteilung.name).order_by(Abteilung.name)
        )
        departments = {row[0]: row[1] for row in dept_result.all()}

        trend: list[dict[str, Any]] = []
        for i in range(11, -1, -1):
            # Calculate the month
            month_offset = today.month - i
            year = today.year
            while month_offset <= 0:
                month_offset += 12
                year -= 1
            m = month_offset
            month_label = f"{year}-{m:02d}"
            end_of_month = date(
                year + (1 if m == 12 else 0),
                1 if m == 12 else m + 1,
                1,
            ) - timedelta(days=1)

            # Total members active as of end of that month
            total_result = await self.session.execute(
                select(func.count())
                .select_from(Mitglied)
                .where(
                    Mitglied.eintrittsdatum <= end_of_month,
                    (Mitglied.austrittsdatum.is_(None)) | (Mitglied.austrittsdatum > end_of_month),
                )
            )
            total = total_result.scalar_one()

            # Per department
            by_dept: dict[str, int] = {}
            for dept_id, dept_name in departments.items():
                dept_count_result = await self.session.execute(
                    select(func.count())
                    .select_from(MitgliedAbteilung)
                    .join(Mitglied)
                    .where(
                        MitgliedAbteilung.abteilung_id == dept_id,
                        MitgliedAbteilung.beitrittsdatum <= end_of_month,
                        Mitglied.eintrittsdatum <= end_of_month,
                        (Mitglied.austrittsdatum.is_(None))
                        | (Mitglied.austrittsdatum > end_of_month),
                    )
                )
                by_dept[dept_name] = dept_count_result.scalar_one()

            trend.append(
                {
                    "month": month_label,
                    "total": total,
                    "by_department": by_dept,
                }
            )

        return trend

    async def _cashflow(self, months: int = 6) -> list[dict[str, Any]]:
        """Monthly income/expenses from Buchungen."""
        today = date.today()
        cashflow: list[dict[str, Any]] = []

        for i in range(months - 1, -1, -1):
            month_offset = today.month - i
            year = today.year
            while month_offset <= 0:
                month_offset += 12
                year -= 1
            m = month_offset
            month_label = f"{year}-{m:02d}"

            # Income: positive bookings
            income_result = await self.session.execute(
                select(func.coalesce(func.sum(Buchung.betrag), Decimal("0.00"))).where(
                    extract("year", Buchung.buchungsdatum) == year,
                    extract("month", Buchung.buchungsdatum) == m,
                    Buchung.betrag > 0,
                )
            )
            income = float(income_result.scalar_one())

            # Expenses: negative bookings (absolute value)
            expense_result = await self.session.execute(
                select(func.coalesce(func.sum(Buchung.betrag), Decimal("0.00"))).where(
                    extract("year", Buchung.buchungsdatum) == year,
                    extract("month", Buchung.buchungsdatum) == m,
                    Buchung.betrag < 0,
                )
            )
            expenses = abs(float(expense_result.scalar_one()))

            cashflow.append(
                {
                    "month": month_label,
                    "income": income,
                    "expenses": expenses,
                }
            )

        return cashflow

    async def _open_actions(self) -> list[dict[str, Any]]:
        """Actionable items: overdue fees, expiring mandates, budget warnings."""
        actions: list[dict[str, Any]] = []
        today = date.today()

        # Overdue invoices
        overdue_result = await self.session.execute(
            select(Rechnung).where(
                Rechnung.status.in_(
                    [
                        RechnungStatus.entwurf,
                        RechnungStatus.gestellt,
                        RechnungStatus.faellig,
                        RechnungStatus.teilbezahlt,
                        RechnungStatus.mahnung_1,
                        RechnungStatus.mahnung_2,
                        RechnungStatus.mahnung_3,
                    ]
                ),
                Rechnung.faelligkeitsdatum < today,
            )
        )
        overdue = overdue_result.scalars().all()
        if overdue:
            total_overdue = sum(float(r.betrag) for r in overdue)
            actions.append(
                {
                    "type": "overdue_fees",
                    "title": "Überfällige Beiträge",
                    "detail": f"{len(overdue)} Rechnungen, gesamt {total_overdue:.2f} EUR",
                    "severity": "high" if len(overdue) > 5 else "medium",
                }
            )

        # Expiring SEPA mandates (within 30 days)
        soon = today + timedelta(days=30)
        mandate_result = await self.session.execute(
            select(func.count())
            .select_from(SepaMandat)
            .where(
                SepaMandat.aktiv == True,  # noqa: E712
                SepaMandat.gueltig_bis.is_not(None),
                SepaMandat.gueltig_bis <= soon,
            )
        )
        expiring = mandate_result.scalar_one()
        if expiring > 0:
            actions.append(
                {
                    "type": "expiring_mandates",
                    "title": "Ablaufende SEPA-Mandate",
                    "detail": f"{expiring} Mandate laufen in 30 Tagen ab",
                    "severity": "medium",
                }
            )

        # Budget warnings: cost centers >90% spent
        ks_result = await self.session.execute(
            select(Kostenstelle).where(Kostenstelle.budget.is_not(None))
        )
        for ks in ks_result.scalars().all():
            spent_result = await self.session.execute(
                select(func.coalesce(func.sum(Buchung.betrag), Decimal("0.00"))).where(
                    Buchung.kostenstelle_id == ks.id
                )
            )
            spent = abs(float(spent_result.scalar_one()))
            budget = float(ks.budget) if ks.budget else 0.0
            if budget > 0 and spent / budget > 0.9:
                actions.append(
                    {
                        "type": "budget_warning",
                        "title": f"Budgetwarnung: {ks.name}",
                        "detail": f"{spent:.0f}/{budget:.0f} EUR ({spent / budget * 100:.0f}%)",
                        "severity": "high" if spent / budget > 1.0 else "medium",
                    }
                )

        return actions

    # -----------------------------------------------------------------------
    # Schatzmeister Dashboard
    # -----------------------------------------------------------------------

    async def get_schatzmeister_dashboard(self) -> dict[str, Any]:
        """Financial operations overview for the treasurer."""
        sepa_hero = await self._sepa_hero()
        kpis = await self._finance_kpis()
        open_items = await self._open_items()
        budget_burn = await self._budget_burn()
        liquidity = await self._cashflow(months=6)

        return {
            "sepa_hero": sepa_hero,
            "kpis": kpis,
            "open_items": open_items,
            "budget_burn": budget_burn,
            "liquidity": liquidity,
        }

    async def _sepa_hero(self) -> dict[str, Any]:
        """Current SEPA collection status."""
        # Total open invoices
        total_result = await self.session.execute(
            select(
                func.count(),
                func.coalesce(func.sum(Rechnung.betrag), Decimal("0.00")),
            ).where(
                Rechnung.status.in_(
                    [
                        RechnungStatus.entwurf,
                        RechnungStatus.gestellt,
                        RechnungStatus.faellig,
                        RechnungStatus.teilbezahlt,
                        RechnungStatus.mahnung_1,
                        RechnungStatus.mahnung_2,
                        RechnungStatus.mahnung_3,
                    ]
                )
            )
        )
        row = total_result.one()
        total_count = row[0]
        total_amount = float(row[1])

        # Members with active SEPA mandates who have open invoices
        ready_result = await self.session.execute(
            select(func.count())
            .select_from(Rechnung)
            .join(
                SepaMandat,
                (SepaMandat.mitglied_id == Rechnung.mitglied_id) & (SepaMandat.aktiv == True),  # noqa: E712
            )
            .where(
                Rechnung.status.in_(
                    [
                        RechnungStatus.entwurf,
                        RechnungStatus.gestellt,
                        RechnungStatus.faellig,
                        RechnungStatus.teilbezahlt,
                        RechnungStatus.mahnung_1,
                        RechnungStatus.mahnung_2,
                        RechnungStatus.mahnung_3,
                    ]
                )
            )
        )
        ready_count = ready_result.scalar_one()
        exceptions = total_count - ready_count

        return {
            "ready_count": ready_count,
            "total_count": total_count,
            "total_amount": total_amount,
            "exceptions": exceptions,
        }

    async def _finance_kpis(self) -> dict[str, Any]:
        """Balance per sphere and other KPIs."""
        # Balance by sphere
        sphere_result = await self.session.execute(
            select(Buchung.sphare, func.sum(Buchung.betrag)).group_by(Buchung.sphare)
        )
        balances: dict[str, float] = {}
        for row in sphere_result.all():
            key = row[0].value if isinstance(row[0], Sphare) else row[0]
            balances[key] = float(row[1] or Decimal("0.00"))

        # Open receivables (sum of open invoices)
        recv_result = await self.session.execute(
            select(func.coalesce(func.sum(Rechnung.betrag), Decimal("0.00"))).where(
                Rechnung.status.in_(
                    [
                        RechnungStatus.entwurf,
                        RechnungStatus.gestellt,
                        RechnungStatus.faellig,
                        RechnungStatus.teilbezahlt,
                        RechnungStatus.mahnung_1,
                        RechnungStatus.mahnung_2,
                        RechnungStatus.mahnung_3,
                    ]
                )
            )
        )
        open_receivables = float(recv_result.scalar_one())

        # Pending transfers: count of open invoices without SEPA mandate
        pending_result = await self.session.execute(
            select(func.count())
            .select_from(Rechnung)
            .where(
                Rechnung.status.in_(
                    [
                        RechnungStatus.entwurf,
                        RechnungStatus.gestellt,
                        RechnungStatus.faellig,
                        RechnungStatus.teilbezahlt,
                        RechnungStatus.mahnung_1,
                        RechnungStatus.mahnung_2,
                        RechnungStatus.mahnung_3,
                    ]
                ),
                ~Rechnung.mitglied_id.in_(
                    select(SepaMandat.mitglied_id).where(
                        SepaMandat.aktiv == True  # noqa: E712
                    )
                ),
            )
        )
        pending_transfers = pending_result.scalar_one()

        return {
            "balance_ideell": balances.get("ideell", 0.0),
            "balance_zweckbetrieb": balances.get("zweckbetrieb", 0.0),
            "balance_vermoegensverwaltung": balances.get("vermoegensverwaltung", 0.0),
            "balance_wirtschaftlich": balances.get("wirtschaftlich", 0.0),
            "open_receivables": open_receivables,
            "pending_transfers": pending_transfers,
        }

    async def _open_items(self) -> list[dict[str, Any]]:
        """Overdue invoices with member and department info."""
        today = date.today()

        result = await self.session.execute(
            select(Rechnung).where(
                Rechnung.status.in_(
                    [
                        RechnungStatus.entwurf,
                        RechnungStatus.gestellt,
                        RechnungStatus.faellig,
                        RechnungStatus.teilbezahlt,
                        RechnungStatus.mahnung_1,
                        RechnungStatus.mahnung_2,
                        RechnungStatus.mahnung_3,
                    ]
                ),
                Rechnung.faelligkeitsdatum < today,
            )
        )
        overdue = result.scalars().all()

        items: list[dict[str, Any]] = []
        for rechnung in overdue:
            days_overdue = (today - rechnung.faelligkeitsdatum).days
            if days_overdue >= 42:
                dunning_level = 3
            elif days_overdue >= 28:
                dunning_level = 2
            elif days_overdue >= 14:
                dunning_level = 1
            else:
                dunning_level = 0

            # Get member name
            member_result = await self.session.execute(
                select(Mitglied.vorname, Mitglied.nachname).where(
                    Mitglied.id == rechnung.mitglied_id
                )
            )
            m_row = member_result.one_or_none()
            member_name = f"{m_row[0]} {m_row[1]}" if m_row else f"ID {rechnung.mitglied_id}"

            # Get department (first one)
            dept_result = await self.session.execute(
                select(Abteilung.name)
                .join(MitgliedAbteilung)
                .where(MitgliedAbteilung.mitglied_id == rechnung.mitglied_id)
                .limit(1)
            )
            dept_row = dept_result.scalar_one_or_none()
            department = dept_row if dept_row else "Keine Abteilung"

            items.append(
                {
                    "member_name": member_name,
                    "department": department,
                    "amount": float(rechnung.betrag),
                    "days_overdue": days_overdue,
                    "dunning_level": dunning_level,
                }
            )

        return items

    async def _budget_burn(self) -> list[dict[str, Any]]:
        """Budget utilization per Kostenstelle."""
        # Department colors for display
        dept_colors = [
            "#3b82f6",
            "#ef4444",
            "#10b981",
            "#f59e0b",
            "#8b5cf6",
            "#ec4899",
            "#06b6d4",
            "#84cc16",
        ]

        ks_result = await self.session.execute(select(Kostenstelle).order_by(Kostenstelle.name))
        items: list[dict[str, Any]] = []
        for idx, ks in enumerate(ks_result.scalars().all()):
            budget = float(ks.budget) if ks.budget else 0.0

            spent_result = await self.session.execute(
                select(func.coalesce(func.sum(Buchung.betrag), Decimal("0.00"))).where(
                    Buchung.kostenstelle_id == ks.id
                )
            )
            spent = abs(float(spent_result.scalar_one()))

            percentage = round(spent / budget * 100, 1) if budget > 0 else 0.0
            color = dept_colors[idx % len(dept_colors)]

            items.append(
                {
                    "name": ks.name,
                    "budget": budget,
                    "spent": spent,
                    "percentage": percentage,
                    "department_color": color,
                }
            )

        return items

    # -----------------------------------------------------------------------
    # Spartenleiter Dashboard
    # -----------------------------------------------------------------------

    async def get_spartenleiter_dashboard(self, abteilung_name: str) -> dict[str, Any]:
        """Department leader dashboard."""
        # Find the department
        dept_result = await self.session.execute(
            select(Abteilung).where(Abteilung.name == abteilung_name)
        )
        abteilung = dept_result.scalar_one_or_none()
        if abteilung is None:
            raise ValueError(f"Abteilung '{abteilung_name}' nicht gefunden")

        kpis = await self._spartenleiter_kpis(abteilung)
        attendance_heatmap = self._mock_attendance_heatmap(abteilung_name)
        training_schedule = self._mock_training_schedule(abteilung_name)
        risk_members = await self._risk_members(abteilung)
        budget_donut = await self._budget_donut(abteilung)

        return {
            "kpis": kpis,
            "attendance_heatmap": attendance_heatmap,
            "training_schedule": training_schedule,
            "risk_members": risk_members,
            "budget_donut": budget_donut,
        }

    async def _spartenleiter_kpis(self, abteilung: Abteilung) -> dict[str, Any]:
        """KPIs for a department."""
        # Member count in department
        member_result = await self.session.execute(
            select(func.count())
            .select_from(MitgliedAbteilung)
            .join(Mitglied)
            .where(
                MitgliedAbteilung.abteilung_id == abteilung.id,
                Mitglied.status == MitgliedStatus.aktiv,
            )
        )
        member_count = member_result.scalar_one()

        # Budget utilization
        ks_result = await self.session.execute(
            select(Kostenstelle).where(Kostenstelle.abteilung_id == abteilung.id)
        )
        kostenstellen = ks_result.scalars().all()
        total_budget = sum(float(ks.budget) for ks in kostenstellen if ks.budget)
        total_spent = 0.0
        for ks in kostenstellen:
            spent_result = await self.session.execute(
                select(func.coalesce(func.sum(Buchung.betrag), Decimal("0.00"))).where(
                    Buchung.kostenstelle_id == ks.id
                )
            )
            total_spent += abs(float(spent_result.scalar_one()))

        budget_utilization = round(total_spent / total_budget * 100, 1) if total_budget > 0 else 0.0

        # Risk count: members with open invoices in this department
        risk_result = await self.session.execute(
            select(func.count(func.distinct(Rechnung.mitglied_id)))
            .join(
                MitgliedAbteilung,
                MitgliedAbteilung.mitglied_id == Rechnung.mitglied_id,
            )
            .where(
                MitgliedAbteilung.abteilung_id == abteilung.id,
                Rechnung.status.in_(
                    [
                        RechnungStatus.entwurf,
                        RechnungStatus.gestellt,
                        RechnungStatus.faellig,
                        RechnungStatus.teilbezahlt,
                        RechnungStatus.mahnung_1,
                        RechnungStatus.mahnung_2,
                        RechnungStatus.mahnung_3,
                    ]
                ),
                Rechnung.faelligkeitsdatum < date.today(),
            )
        )
        risk_count = risk_result.scalar_one()

        # Mock attendance - deterministic based on department name
        seed = int(hashlib.md5(abteilung.name.encode()).hexdigest()[:8], 16)
        rng = random.Random(seed)
        avg_attendance = round(rng.uniform(60.0, 95.0), 1)

        return {
            "member_count": member_count,
            "avg_attendance_pct": avg_attendance,
            "budget_utilization_pct": budget_utilization,
            "risk_count": risk_count,
        }

    def _mock_attendance_heatmap(self, abteilung_name: str) -> list[dict[str, Any]]:
        """Generate deterministic mock attendance heatmap: 7 days x 12 weeks."""
        seed = int(hashlib.md5(abteilung_name.encode()).hexdigest()[:8], 16)
        rng = random.Random(seed)

        heatmap: list[dict[str, Any]] = []
        for day in range(7):
            cells: list[int] = []
            for _week in range(12):
                # Training typically on weekdays, less on weekends
                if day < 5:
                    intensity = rng.choices([0, 1, 2, 3], weights=[10, 20, 40, 30])[0]
                else:
                    intensity = rng.choices([0, 1, 2, 3], weights=[50, 30, 15, 5])[0]
                cells.append(intensity)
            heatmap.append({"day": day, "cells": cells})

        return heatmap

    def _mock_training_schedule(self, abteilung_name: str) -> list[dict[str, Any]]:
        """Generate deterministic mock training schedule."""
        seed = int(hashlib.md5(abteilung_name.encode()).hexdigest()[:8], 16)
        rng = random.Random(seed)

        weekdays = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag"]
        times = ["16:00", "17:00", "18:00", "19:00", "20:00"]
        groups = ["Anfaenger", "Fortgeschrittene", "Wettkampf", "Kinder", "Senioren"]
        trainers = ["M. Mueller", "S. Schmidt", "K. Klein", "A. Becker", "T. Wagner"]

        count = rng.randint(3, 6)
        schedule: list[dict[str, Any]] = []
        for i in range(count):
            max_p = rng.choice([12, 16, 20, 24])
            schedule.append(
                {
                    "group": rng.choice(groups),
                    "trainer": rng.choice(trainers),
                    "registered": rng.randint(4, max_p),
                    "max_participants": max_p,
                    "weekday": rng.choice(weekdays),
                    "time": rng.choice(times),
                }
            )

        return schedule

    async def _risk_members(self, abteilung: Abteilung) -> list[dict[str, Any]]:
        """Members with overdue fees in this department."""
        today = date.today()

        result = await self.session.execute(
            select(Mitglied.id, Mitglied.vorname, Mitglied.nachname)
            .join(MitgliedAbteilung)
            .join(
                Rechnung,
                Rechnung.mitglied_id == Mitglied.id,
            )
            .where(
                MitgliedAbteilung.abteilung_id == abteilung.id,
                Rechnung.status.in_(
                    [
                        RechnungStatus.entwurf,
                        RechnungStatus.gestellt,
                        RechnungStatus.faellig,
                        RechnungStatus.teilbezahlt,
                        RechnungStatus.mahnung_1,
                        RechnungStatus.mahnung_2,
                        RechnungStatus.mahnung_3,
                    ]
                ),
                Rechnung.faelligkeitsdatum < today,
                Mitglied.status == MitgliedStatus.aktiv,
            )
            .distinct()
        )
        members = result.all()

        risk: list[dict[str, Any]] = []
        for row in members:
            risk.append(
                {
                    "member_id": row[0],
                    "name": f"{row[1]} {row[2]}",
                    "reason": "Offene Beitraege ueberfaellig",
                }
            )

        return risk

    async def _budget_donut(self, abteilung: Abteilung) -> dict[str, Any]:
        """Budget breakdown for a department."""
        ks_result = await self.session.execute(
            select(Kostenstelle).where(Kostenstelle.abteilung_id == abteilung.id)
        )
        kostenstellen = ks_result.scalars().all()

        total_budget = sum(float(ks.budget) for ks in kostenstellen if ks.budget)
        total_spent = 0.0
        for ks in kostenstellen:
            spent_result = await self.session.execute(
                select(func.coalesce(func.sum(Buchung.betrag), Decimal("0.00"))).where(
                    Buchung.kostenstelle_id == ks.id
                )
            )
            total_spent += abs(float(spent_result.scalar_one()))

        # committed = 10% of remaining budget (mock)
        remaining = max(total_budget - total_spent, 0.0)
        committed = round(remaining * 0.1, 2)
        free = round(remaining - committed, 2)

        return {
            "used": round(total_spent, 2),
            "committed": committed,
            "free": free,
        }
