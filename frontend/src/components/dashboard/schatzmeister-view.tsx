import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { KpiCard } from "./kpi-card";
import { SectionHeader } from "./section-header";
import { MahnstufenBadge } from "./mahnstufen-badge";
import { SpartenChip } from "./sparten-chip";
import { ChartTooltip } from "./chart-tooltip";
import { ProgressBar } from "./progress-bar";
import { ClickableRow } from "./clickable-row";
import { SPARTEN_COLORS, CHART, SEMANTIC_COLORS } from "@/constants/design";
import api from "@/lib/api";
import type { SchatzmeisterDashboard, OffenerPosten } from "@/types/dashboard";

// Backend API response types
interface ApiSepaHero {
  ready_count: number;
  total_count: number;
  total_amount: number;
  exceptions: number;
}

interface ApiFinanceKPIs {
  balance_ideell: number;
  balance_zweckbetrieb: number;
  balance_vermoegensverwaltung: number;
  balance_wirtschaftlich: number;
  open_receivables: number;
  pending_transfers: number;
}

interface ApiOffenerPosten {
  member_name: string;
  department: string;
  amount: number;
  days_overdue: number;
  dunning_level: number;
}

interface ApiBudgetBurnItem {
  name: string;
  budget: number;
  spent: number;
  percentage: number;
  department_color: string;
}

interface ApiLiquidityPoint {
  month: string;
  income: number;
  expenses: number;
}

interface ApiSchatzmeisterResponse {
  sepa_hero: ApiSepaHero;
  kpis: ApiFinanceKPIs;
  open_items: ApiOffenerPosten[];
  budget_burn: ApiBudgetBurnItem[];
  liquidity: ApiLiquidityPoint[];
}

const MONTH_LABELS: Record<string, string> = {
  "01": "Jan", "02": "Feb", "03": "Mär", "04": "Apr",
  "05": "Mai", "06": "Jun", "07": "Jul", "08": "Aug",
  "09": "Sep", "10": "Okt", "11": "Nov", "12": "Dez",
};

function mapApiToSchatzmeisterDashboard(resp: ApiSchatzmeisterResponse): SchatzmeisterDashboard {
  const readiness = resp.sepa_hero.total_count > 0
    ? Math.round((resp.sepa_hero.ready_count / resp.sepa_hero.total_count) * 100)
    : 0;

  const sepa = {
    betrag: resp.sepa_hero.total_amount,
    anzahl: resp.sepa_hero.total_count,
    readiness,
    naechsterEinzug: "n/a",
  };

  const kpis = {
    ideell: resp.kpis.balance_ideell,
    zweckbetrieb: resp.kpis.balance_zweckbetrieb,
    offeneForderungen: resp.kpis.open_receivables,
    offeneForderungenTrend: 0,
    ueberweisungen: resp.kpis.pending_transfers,
  };

  const offenePosten: OffenerPosten[] = resp.open_items.map((item, idx) => ({
    id: String(idx + 1),
    mitglied: item.member_name,
    sparte: item.department,
    betrag: item.amount,
    tageUeberfaellig: item.days_overdue,
    mahnstufe: Math.min(item.dunning_level, 3) as 0 | 1 | 2 | 3,
  }));

  const budgetBurn = resp.budget_burn.map((b) => ({
    name: b.name,
    budget: b.budget,
    used: b.spent,
  }));

  const liquiditaet = resp.liquidity.map((pt) => {
    const monthKey = pt.month.split("-")[1] || pt.month;
    return {
      month: MONTH_LABELS[monthKey] || pt.month,
      einnahmen: pt.income,
      ausgaben: pt.expenses,
    };
  });

  return { kpis, sepa, offenePosten, budgetBurn, liquiditaet };
}

interface SchatzmeisterViewProps {
  data?: SchatzmeisterDashboard | null;
}

export function SchatzmeisterView({ data }: SchatzmeisterViewProps) {
  const [apiData, setApiData] = useState<SchatzmeisterDashboard | null>(null);
  const [loading, setLoading] = useState(!data);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const fetchData = useCallback(async () => {
    if (data) return;
    setLoading(true);
    setError(null);
    try {
      const resp = await api.get<ApiSchatzmeisterResponse>("/api/dashboard/schatzmeister");
      setApiData(mapApiToSchatzmeisterDashboard(resp));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Fehler beim Laden der Daten");
    } finally {
      setLoading(false);
    }
  }, [data]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const d = data ?? apiData;

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <p className="text-muted-foreground">Laden...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-64 flex-col items-center justify-center gap-2">
        <p className="text-sm text-red-600">{error}</p>
        <button
          onClick={fetchData}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          Erneut versuchen
        </button>
      </div>
    );
  }

  if (!d) {
    return (
      <div className="flex h-64 items-center justify-center">
        <p className="text-muted-foreground">Keine Daten verfügbar</p>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      {/* SEPA Hero */}
      <div className="rounded-xl border border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-950/30 p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-blue-600 dark:text-blue-400">
              SEPA-Lastschrifteinzug
            </p>
            <p className="mt-1 tabular-nums text-3xl font-bold text-foreground">
              {d.sepa.betrag.toLocaleString("de-DE")} €
            </p>
            <p className="mt-0.5 text-xs text-muted-foreground">
              {d.sepa.anzahl} Mitglieder &middot; Nächster Einzug:{" "}
              {d.sepa.naechsterEinzug}
            </p>
          </div>
          <div className="flex items-center gap-4">
            <div className="w-48">
              <ProgressBar
                value={d.sepa.readiness}
                color={SEMANTIC_COLORS.info}
                showLabel
                label="Bereitschaft"
              />
            </div>
            <div className="flex gap-2">
              <button
                className="rounded-md bg-blue-600 px-4 py-2 text-xs font-medium text-white hover:bg-blue-700"
                onClick={() => navigate("/finanzen")}
              >
                Einzug starten
              </button>
              <button
                className="rounded-md border border-border bg-card px-4 py-2 text-xs font-medium text-foreground hover:bg-muted"
                onClick={() => navigate("/finanzen")}
              >
                Vorschau
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-4 gap-4">
        <KpiCard
          label="Sphäre Ideell"
          value={`${d.kpis.ideell.toLocaleString("de-DE")} €`}
          accentColor={SEMANTIC_COLORS.info}
          href="/finanzen"
        />
        <KpiCard
          label="Zweckbetrieb"
          value={`${d.kpis.zweckbetrieb.toLocaleString("de-DE")} €`}
          accentColor={SEMANTIC_COLORS.purple}
          href="/finanzen"
        />
        <KpiCard
          label="Offene Forderungen"
          value={`${d.kpis.offeneForderungen.toLocaleString("de-DE")} €`}
          trend={d.kpis.offeneForderungenTrend}
          trendLabel="vs. Vormonat"
          accentColor={SEMANTIC_COLORS.warning}
          href="/finanzen"
        />
        <KpiCard
          label="Überweisungen"
          value={d.kpis.ueberweisungen.toString()}
          accentColor={SEMANTIC_COLORS.success}
          href="/finanzen"
        />
      </div>

      {/* Middle row */}
      <div className="grid grid-cols-5 gap-4">
        {/* Offene Posten Table */}
        <div className="col-span-3 rounded-xl border border-border bg-card p-4 shadow-sm">
          <SectionHeader
            label="Offene Posten"
            action="Alle anzeigen"
            onAction={() => navigate("/finanzen")}
          />
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="pb-2 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Mitglied
                  </th>
                  <th className="pb-2 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Sparte
                  </th>
                  <th className="pb-2 text-right text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Betrag
                  </th>
                  <th className="pb-2 text-right text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Tage
                  </th>
                  <th className="pb-2 text-right text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Stufe
                  </th>
                </tr>
              </thead>
              <tbody>
                {d.offenePosten.map((p) => (
                  <ClickableRow
                    key={p.id}
                    href="/mitglieder"
                    className="border-b border-border/50 last:border-0"
                  >
                    <td className="py-2.5 text-foreground">
                      {p.mitglied}
                    </td>
                    <td className="py-2.5">
                      <SpartenChip name={p.sparte} />
                    </td>
                    <td className="py-2.5 text-right tabular-nums text-foreground">
                      {p.betrag.toLocaleString("de-DE")} €
                    </td>
                    <td className="py-2.5 text-right tabular-nums text-muted-foreground">
                      {p.tageUeberfaellig}
                    </td>
                    <td className="py-2.5 text-right">
                      <MahnstufenBadge stufe={p.mahnstufe} />
                    </td>
                  </ClickableRow>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Budget Burn */}
        <div className="col-span-2 rounded-xl border border-border bg-card p-4 shadow-sm">
          <SectionHeader label="Budget-Verbrauch" />
          <div className="mt-3">
            <ResponsiveContainer width="100%" height={CHART.heights.md}>
              <BarChart data={d.budgetBurn} layout="vertical" barSize={14}>
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke={CHART.gridStroke}
                  horizontal={false}
                />
                <XAxis
                  type="number"
                  tick={{ fill: CHART.tickFill, fontSize: CHART.tickFontSize }}
                  axisLine={false}
                  tickLine={false}
                  tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
                />
                <YAxis
                  type="category"
                  dataKey="name"
                  tick={{ fill: CHART.tickFill, fontSize: CHART.tickFontSize }}
                  axisLine={false}
                  tickLine={false}
                  width={90}
                />
                <Tooltip
                  content={
                    <ChartTooltip
                      formatter={(v) => `${v.toLocaleString("de-DE")} €`}
                    />
                  }
                />
                <Bar dataKey="used" name="Verbraucht" radius={[0, 3, 3, 0]}>
                  {d.budgetBurn.map((entry) => (
                    <Cell
                      key={entry.name}
                      fill={SPARTEN_COLORS[entry.name] || "#6b7280"}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Liquidity chart - full width */}
      <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
        <SectionHeader label="Liquiditätsentwicklung" />
        <div className="mt-3">
          <ResponsiveContainer width="100%" height={CHART.heights.md}>
            <AreaChart data={d.liquiditaet}>
              <defs>
                <linearGradient id="liq-ein" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={SEMANTIC_COLORS.success} stopOpacity={0.3} />
                  <stop offset="100%" stopColor={SEMANTIC_COLORS.success} stopOpacity={0.02} />
                </linearGradient>
                <linearGradient id="liq-aus" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={SEMANTIC_COLORS.danger} stopOpacity={0.3} />
                  <stop offset="100%" stopColor={SEMANTIC_COLORS.danger} stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid
                strokeDasharray="3 3"
                stroke={CHART.gridStroke}
                vertical={false}
              />
              <XAxis
                dataKey="month"
                tick={{ fill: CHART.tickFill, fontSize: CHART.tickFontSize }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tick={{ fill: CHART.tickFill, fontSize: CHART.tickFontSize }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
              />
              <Tooltip
                content={
                  <ChartTooltip
                    formatter={(v) => `${v.toLocaleString("de-DE")} €`}
                  />
                }
              />
              <Area
                type="monotone"
                dataKey="einnahmen"
                name="Einnahmen"
                stroke={SEMANTIC_COLORS.success}
                fill="url(#liq-ein)"
                strokeWidth={1.5}
              />
              <Area
                type="monotone"
                dataKey="ausgaben"
                name="Ausgaben"
                stroke={SEMANTIC_COLORS.danger}
                fill="url(#liq-aus)"
                strokeWidth={1.5}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
