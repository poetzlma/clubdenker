"""MCP tools for dashboard views."""

from __future__ import annotations

from sportverein.mcp.server import mcp
from sportverein.mcp.session import get_mcp_session
from sportverein.services.dashboard import DashboardService


@mcp.tool(
    description="Strategischer Vereinsueberblick fuer den Vorstand. "
    "Zeigt Mitgliederentwicklung, Kassenstand, offene Aktionen."
)
async def dashboard_vorstand() -> dict:
    async with get_mcp_session() as session:
        svc = DashboardService(session)
        data = await svc.get_vorstand_dashboard()
        await session.commit()

        kpis = data["kpis"]
        lines = [
            "=== Vorstand Dashboard ===",
            f"Aktive Mitglieder: {kpis['active_members']}",
            f"Kassenstand: {kpis['total_balance']:.2f} EUR",
            f"Offene Beitraege: {kpis['open_fees_count']} ({kpis['open_fees_amount']:.2f} EUR)",
            f"SEPA-Compliance: {kpis['compliance_score']:.1f}%",
            "",
            "--- Mitgliederentwicklung (letzte 3 Monate) ---",
        ]
        for point in data["member_trend"][-3:]:
            dept_str = ", ".join(f"{k}: {v}" for k, v in point["by_department"].items())
            lines.append(f"  {point['month']}: {point['total']} gesamt ({dept_str})")

        lines.append("")
        lines.append("--- Cashflow (letzte 3 Monate) ---")
        for point in data["cashflow"][-3:]:
            lines.append(
                f"  {point['month']}: +{point['income']:.2f} / -{point['expenses']:.2f} EUR"
            )

        if data["open_actions"]:
            lines.append("")
            lines.append("--- Offene Aktionen ---")
            for action in data["open_actions"]:
                lines.append(
                    f"  [{action['severity'].upper()}] {action['title']}: {action['detail']}"
                )

        return {"summary": "\n".join(lines), "data": data}


@mcp.tool(
    description="Finanzoperativer Ueberblick fuer den Schatzmeister. "
    "SEPA-Status, offene Posten, Budgetauslastung, Liquiditaet."
)
async def dashboard_schatzmeister() -> dict:
    async with get_mcp_session() as session:
        svc = DashboardService(session)
        data = await svc.get_schatzmeister_dashboard()
        await session.commit()

        sepa = data["sepa_hero"]
        kpis = data["kpis"]
        lines = [
            "=== Schatzmeister Dashboard ===",
            "",
            "--- SEPA-Status ---",
            f"  Bereit: {sepa['ready_count']}/{sepa['total_count']}",
            f"  Gesamtbetrag: {sepa['total_amount']:.2f} EUR",
            f"  Ausnahmen: {sepa['exceptions']}",
            "",
            "--- Kassenstand nach Sphaere ---",
            f"  Ideell: {kpis['balance_ideell']:.2f} EUR",
            f"  Zweckbetrieb: {kpis['balance_zweckbetrieb']:.2f} EUR",
            f"  Vermoegensverwaltung: {kpis['balance_vermoegensverwaltung']:.2f} EUR",
            f"  Wirtschaftlich: {kpis['balance_wirtschaftlich']:.2f} EUR",
            f"  Offene Forderungen: {kpis['open_receivables']:.2f} EUR",
            f"  Offene Ueberweisungen: {kpis['pending_transfers']}",
        ]

        if data["open_items"]:
            lines.append("")
            lines.append("--- Offene Posten ---")
            for item in data["open_items"][:10]:
                lines.append(
                    f"  {item['member_name']} ({item['department']}): "
                    f"{item['amount']:.2f} EUR, {item['days_overdue']} Tage, "
                    f"Mahnstufe {item['dunning_level']}"
                )

        if data["budget_burn"]:
            lines.append("")
            lines.append("--- Budgetauslastung ---")
            for b in data["budget_burn"]:
                lines.append(
                    f"  {b['name']}: {b['spent']:.2f}/{b['budget']:.2f} EUR ({b['percentage']:.1f}%)"
                )

        return {"summary": "\n".join(lines), "data": data}


@mcp.tool(
    description="Dashboard fuer Spartenleiter. "
    "Mitglieder, Anwesenheit, Trainings, Budget einer Abteilung."
)
async def dashboard_spartenleiter(abteilung: str) -> dict:
    async with get_mcp_session() as session:
        svc = DashboardService(session)
        try:
            data = await svc.get_spartenleiter_dashboard(abteilung)
        except ValueError as exc:
            return {"error": str(exc)}
        await session.commit()

        kpis = data["kpis"]
        lines = [
            f"=== Spartenleiter Dashboard: {abteilung} ===",
            f"Mitglieder: {kpis['member_count']}",
            f"Anwesenheit: {kpis['avg_attendance_pct']:.1f}%",
            f"Budgetauslastung: {kpis['budget_utilization_pct']:.1f}%",
            f"Risiko-Mitglieder: {kpis['risk_count']}",
        ]

        if data["training_schedule"]:
            lines.append("")
            lines.append("--- Trainingsplan ---")
            for t in data["training_schedule"]:
                lines.append(
                    f"  {t['weekday']} {t['time']}: {t['group']} "
                    f"({t['trainer']}, {t['registered']}/{t['max_participants']})"
                )

        if data["risk_members"]:
            lines.append("")
            lines.append("--- Risiko-Mitglieder ---")
            for rm in data["risk_members"]:
                lines.append(f"  {rm['name']}: {rm['reason']}")

        donut = data["budget_donut"]
        lines.append("")
        lines.append("--- Budget ---")
        lines.append(f"  Verwendet: {donut['used']:.2f} EUR")
        lines.append(f"  Gebunden: {donut['committed']:.2f} EUR")
        lines.append(f"  Frei: {donut['free']:.2f} EUR")

        return {"summary": "\n".join(lines), "data": data}
