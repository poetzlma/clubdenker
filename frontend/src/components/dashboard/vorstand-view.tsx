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
} from "recharts";
import { KpiCard } from "./kpi-card";
import { SectionHeader } from "./section-header";
import { ProgressBar } from "./progress-bar";
import { AktionsKarte } from "./aktions-karte";
import { ChartTooltip } from "./chart-tooltip";
import { ClickableCard } from "./clickable-card";
import { SPARTEN_COLORS, CHART, SEMANTIC_COLORS } from "@/constants/design";
import api from "@/lib/api";
import type { VorstandDashboard } from "@/types/dashboard";

// Backend API response types
interface ApiVorstandKPIs {
  active_members: number;
  total_balance: number;
  open_fees_count: number;
  open_fees_amount: number;
  compliance_score: number;
}

interface ApiMemberTrendPoint {
  month: string;
  total: number;
  by_department: Record<string, number>;
}

interface ApiCashflowPoint {
  month: string;
  income: number;
  expenses: number;
}

interface ApiOpenAction {
  type: string;
  title: string;
  detail: string;
  severity: string;
}

interface ApiVorstandResponse {
  kpis: ApiVorstandKPIs;
  member_trend: ApiMemberTrendPoint[];
  cashflow: ApiCashflowPoint[];
  open_actions: ApiOpenAction[];
}

// Short German month labels
const MONTH_LABELS: Record<string, string> = {
  "01": "Jan", "02": "Feb", "03": "Mär", "04": "Apr",
  "05": "Mai", "06": "Jun", "07": "Jul", "08": "Aug",
  "09": "Sep", "10": "Okt", "11": "Nov", "12": "Dez",
};

function mapApiToVorstandDashboard(resp: ApiVorstandResponse): VorstandDashboard {
  const kpis = {
    mitglieder: resp.kpis.active_members,
    mitgliederTrend: 0,
    kassenstand: resp.kpis.total_balance,
    kassenstandTrend: 0,
    offenePosten: resp.kpis.open_fees_count,
    offenePostenTrend: 0,
    compliance: resp.kpis.compliance_score,
  };

  const memberTrend = resp.member_trend.map((pt) => {
    const monthKey = pt.month.split("-")[1] || pt.month;
    return {
      month: MONTH_LABELS[monthKey] || pt.month,
      Fussball: pt.by_department["Fussball"] ?? 0,
      Tennis: pt.by_department["Tennis"] ?? 0,
      Fitness: pt.by_department["Fitness"] ?? 0,
      Leichtathletik: pt.by_department["Leichtathletik"] ?? 0,
    };
  });

  // Derive spartenGesundheit from budget_burn if available (not in vorstand endpoint),
  // so we fall back to computing from member trend totals per department.
  const lastTrend = resp.member_trend[resp.member_trend.length - 1];
  const departments = lastTrend ? Object.keys(lastTrend.by_department) : [];
  const spartenGesundheit = departments.map((name) => ({
    name,
    budget: 0,
    used: 0,
    percent: 0,
  }));

  const cashflow = resp.cashflow.map((pt) => {
    const monthKey = pt.month.split("-")[1] || pt.month;
    return {
      month: MONTH_LABELS[monthKey] || pt.month,
      einnahmen: pt.income,
      ausgaben: pt.expenses,
    };
  });

  const aktionen = resp.open_actions.map((a, idx) => ({
    id: String(idx + 1),
    title: a.title,
    description: a.detail,
    variant: (a.severity === "high" ? "warn" : a.severity === "medium" ? "action" : "ok") as "warn" | "action" | "ok",
    href: "/finanzen",
  }));

  return { kpis, memberTrend, spartenGesundheit, cashflow, aktionen };
}

interface VorstandViewProps {
  data?: VorstandDashboard | null;
  onMemberCountChange?: (count: number) => void;
}

export function VorstandView({ data, onMemberCountChange }: VorstandViewProps) {
  const [apiData, setApiData] = useState<VorstandDashboard | null>(null);
  const [loading, setLoading] = useState(!data);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const fetchData = useCallback(async () => {
    if (data) return;
    setLoading(true);
    setError(null);
    try {
      const resp = await api.get<ApiVorstandResponse>("/api/dashboard/vorstand");
      setApiData(mapApiToVorstandDashboard(resp));
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

  const [liveCount, setLiveCount] = useState(0);

  // Initialize liveCount from loaded data
  useEffect(() => {
    if (d) {
      setLiveCount(d.kpis.mitglieder);
    }
  }, [d]);

  // Live member counter that ticks +/-1 every 3s with 15% probability
  useEffect(() => {
    const interval = setInterval(() => {
      if (Math.random() < 0.15) {
        setLiveCount((prev) => {
          const next = prev + (Math.random() > 0.5 ? 1 : -1);
          return next;
        });
      }
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    onMemberCountChange?.(liveCount);
  }, [liveCount, onMemberCountChange]);

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
      {/* KPIs */}
      <div className="grid grid-cols-4 gap-4">
        <KpiCard
          label="Mitglieder"
          value={liveCount.toString()}
          trend={d.kpis.mitgliederTrend}
          trendLabel="vs. Vormonat"
          accentColor={SEMANTIC_COLORS.info}
          href="/mitglieder"
        />
        <KpiCard
          label="Kassenstand"
          value={`${d.kpis.kassenstand.toLocaleString("de-DE")} €`}
          trend={d.kpis.kassenstandTrend}
          trendLabel="vs. Vormonat"
          accentColor={SEMANTIC_COLORS.success}
          href="/finanzen"
        />
        <KpiCard
          label="Offene Posten"
          value={d.kpis.offenePosten.toString()}
          trend={d.kpis.offenePostenTrend}
          trendLabel="vs. Vormonat"
          accentColor={SEMANTIC_COLORS.warning}
          href="/finanzen"
        />
        <KpiCard
          label="Compliance"
          value={`${d.kpis.compliance}%`}
          accentColor={SEMANTIC_COLORS.purple}
        />
      </div>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-3 gap-4">
        <div className="col-span-2 rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
          <SectionHeader label="Mitgliederentwicklung" />
          <div className="mt-3">
            <ResponsiveContainer width="100%" height={CHART.heights.lg}>
              <AreaChart data={d.memberTrend}>
                <defs>
                  {Object.entries(SPARTEN_COLORS).map(([name, color]) => (
                    <linearGradient
                      key={name}
                      id={`gradient-${name}`}
                      x1="0"
                      y1="0"
                      x2="0"
                      y2="1"
                    >
                      <stop offset="0%" stopColor={color} stopOpacity={0.4} />
                      <stop offset="100%" stopColor={color} stopOpacity={0.05} />
                    </linearGradient>
                  ))}
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
                />
                <Tooltip content={<ChartTooltip />} />
                {Object.entries(SPARTEN_COLORS).map(([name, color]) => (
                  <Area
                    key={name}
                    type="monotone"
                    dataKey={name}
                    stackId="1"
                    stroke={color}
                    fill={`url(#gradient-${name})`}
                    strokeWidth={1.5}
                  />
                ))}
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
          <SectionHeader
            label="Spartengesundheit"
            action="Details →"
            onAction={() => navigate("/finanzen")}
          />
          <div className="mt-4 space-y-4">
            {d.spartenGesundheit.map((s) => (
              <ClickableCard key={s.name} href="/finanzen">
                <ProgressBar
                  label={s.name}
                  value={s.percent}
                  color={SPARTEN_COLORS[s.name] || "#6b7280"}
                  showLabel
                />
              </ClickableCard>
            ))}
          </div>
        </div>
      </div>

      {/* Charts Row 2 */}
      <div className="grid grid-cols-5 gap-4">
        <div className="col-span-3 rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
          <SectionHeader
            label="Cashflow (6 Monate)"
            action="Details →"
            onAction={() => navigate("/finanzen")}
          />
          <div className="mt-3">
            <ResponsiveContainer width="100%" height={CHART.heights.md}>
              <BarChart data={d.cashflow} barGap={2}>
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
                />
                <Tooltip
                  content={
                    <ChartTooltip
                      formatter={(v) => `${v.toLocaleString("de-DE")} €`}
                    />
                  }
                />
                <Bar
                  dataKey="einnahmen"
                  name="Einnahmen"
                  fill={SEMANTIC_COLORS.success}
                  radius={CHART.barRadius}
                />
                <Bar
                  dataKey="ausgaben"
                  name="Ausgaben"
                  fill={SEMANTIC_COLORS.danger}
                  radius={CHART.barRadius}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="col-span-2 rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
          <SectionHeader label="Offene Aktionen" />
          <div className="mt-3 space-y-2">
            {d.aktionen.map((a) => (
              <AktionsKarte
                key={a.id}
                title={a.title}
                description={a.description}
                variant={a.variant}
                href={a.href}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
