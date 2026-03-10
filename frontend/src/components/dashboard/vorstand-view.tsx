import { useState, useEffect } from "react";
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
import type { VorstandDashboard } from "@/types/dashboard";

const MOCK_DATA: VorstandDashboard = {
  kpis: {
    mitglieder: 248,
    mitgliederTrend: 3.2,
    kassenstand: 14520,
    kassenstandTrend: 5.1,
    offenePosten: 23,
    offenePostenTrend: -12.5,
    compliance: 94,
  },
  memberTrend: [
    { month: "Apr", Fussball: 82, Tennis: 45, Fitness: 38, Leichtathletik: 28 },
    { month: "Mai", Fussball: 84, Tennis: 46, Fitness: 40, Leichtathletik: 29 },
    { month: "Jun", Fussball: 85, Tennis: 44, Fitness: 41, Leichtathletik: 29 },
    { month: "Jul", Fussball: 86, Tennis: 47, Fitness: 42, Leichtathletik: 30 },
    { month: "Aug", Fussball: 88, Tennis: 48, Fitness: 43, Leichtathletik: 30 },
    { month: "Sep", Fussball: 89, Tennis: 47, Fitness: 44, Leichtathletik: 31 },
    { month: "Okt", Fussball: 90, Tennis: 49, Fitness: 45, Leichtathletik: 31 },
    { month: "Nov", Fussball: 91, Tennis: 50, Fitness: 46, Leichtathletik: 32 },
    { month: "Dez", Fussball: 92, Tennis: 50, Fitness: 47, Leichtathletik: 32 },
    { month: "Jan", Fussball: 93, Tennis: 51, Fitness: 48, Leichtathletik: 33 },
    { month: "Feb", Fussball: 94, Tennis: 52, Fitness: 48, Leichtathletik: 33 },
    { month: "Mär", Fussball: 95, Tennis: 53, Fitness: 49, Leichtathletik: 34 },
  ],
  spartenGesundheit: [
    { name: "Fussball", budget: 12000, used: 8400, percent: 70 },
    { name: "Tennis", budget: 8000, used: 5200, percent: 65 },
    { name: "Fitness", budget: 6000, used: 5100, percent: 85 },
    { name: "Leichtathletik", budget: 4000, used: 1600, percent: 40 },
  ],
  cashflow: [
    { month: "Okt", einnahmen: 8200, ausgaben: 6100 },
    { month: "Nov", einnahmen: 7800, ausgaben: 5900 },
    { month: "Dez", einnahmen: 9100, ausgaben: 7200 },
    { month: "Jan", einnahmen: 12500, ausgaben: 6800 },
    { month: "Feb", einnahmen: 8900, ausgaben: 7100 },
    { month: "Mär", einnahmen: 9300, ausgaben: 6500 },
  ],
  aktionen: [
    {
      id: "1",
      title: "SEPA-Einzug vorbereiten",
      description: "Monatlicher Beitragseinzug fällig am 15. März",
      variant: "action",
      href: "/finanzen",
    },
    {
      id: "2",
      title: "Mahnlauf 3 Mitglieder",
      description: "Stufe M2 erreicht - sofortige Aktion empfohlen",
      variant: "warn",
      href: "/finanzen",
    },
    {
      id: "3",
      title: "Jahresabschluss 2025",
      description: "Alle Dokumente eingereicht und geprüft",
      variant: "ok",
    },
    {
      id: "4",
      title: "Versicherungsnachweis fehlt",
      description: "Haftpflicht für Fitness-Bereich läuft am 01.04. aus",
      variant: "warn",
    },
  ],
};

interface VorstandViewProps {
  data?: VorstandDashboard | null;
  onMemberCountChange?: (count: number) => void;
}

export function VorstandView({ data, onMemberCountChange }: VorstandViewProps) {
  const d = data ?? MOCK_DATA;
  const [liveCount, setLiveCount] = useState(d.kpis.mitglieder);
  const navigate = useNavigate();

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
