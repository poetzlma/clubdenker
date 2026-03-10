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
import type { SchatzmeisterDashboard } from "@/types/dashboard";

const MOCK_DATA: SchatzmeisterDashboard = {
  kpis: {
    ideell: 8420,
    zweckbetrieb: 3210,
    offeneForderungen: 4850,
    offeneForderungenTrend: -8.3,
    ueberweisungen: 12,
  },
  sepa: {
    betrag: 6240,
    anzahl: 186,
    readiness: 82,
    naechsterEinzug: "15.03.2026",
  },
  offenePosten: [
    { id: "1", mitglied: "Schmidt, Anna", sparte: "Fussball", betrag: 180, tageUeberfaellig: 45, mahnstufe: 2 },
    { id: "2", mitglied: "Müller, Max", sparte: "Tennis", betrag: 120, tageUeberfaellig: 30, mahnstufe: 1 },
    { id: "3", mitglied: "Weber, Lisa", sparte: "Fitness", betrag: 90, tageUeberfaellig: 62, mahnstufe: 3 },
    { id: "4", mitglied: "Fischer, Thomas", sparte: "Fussball", betrag: 180, tageUeberfaellig: 15, mahnstufe: 1 },
    { id: "5", mitglied: "Wagner, Sarah", sparte: "Leichtathletik", betrag: 60, tageUeberfaellig: 8, mahnstufe: 0 },
  ],
  budgetBurn: [
    { name: "Fussball", budget: 12000, used: 8400 },
    { name: "Tennis", budget: 8000, used: 5200 },
    { name: "Fitness", budget: 6000, used: 5100 },
    { name: "Leichtathletik", budget: 4000, used: 1600 },
  ],
  liquiditaet: [
    { month: "Okt", einnahmen: 8200, ausgaben: 6100 },
    { month: "Nov", einnahmen: 7800, ausgaben: 5900 },
    { month: "Dez", einnahmen: 9100, ausgaben: 7200 },
    { month: "Jan", einnahmen: 12500, ausgaben: 6800 },
    { month: "Feb", einnahmen: 8900, ausgaben: 7100 },
    { month: "Mär", einnahmen: 9300, ausgaben: 6500 },
    { month: "Apr", einnahmen: 8800, ausgaben: 6900 },
    { month: "Mai", einnahmen: 9500, ausgaben: 7300 },
    { month: "Jun", einnahmen: 10200, ausgaben: 7800 },
  ],
};

interface SchatzmeisterViewProps {
  data?: SchatzmeisterDashboard | null;
}

export function SchatzmeisterView({ data }: SchatzmeisterViewProps) {
  const d = data ?? MOCK_DATA;
  const navigate = useNavigate();

  return (
    <div className="space-y-6 p-6">
      {/* SEPA Hero */}
      <div className="rounded-xl border border-blue-200 bg-blue-50 p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-blue-600">
              SEPA-Lastschrifteinzug
            </p>
            <p className="mt-1 tabular-nums text-3xl font-bold text-gray-900">
              {d.sepa.betrag.toLocaleString("de-DE")} €
            </p>
            <p className="mt-0.5 text-xs text-gray-500">
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
                className="rounded-md border border-gray-300 bg-white px-4 py-2 text-xs font-medium text-gray-700 hover:bg-gray-50"
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
        <div className="col-span-3 rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
          <SectionHeader
            label="Offene Posten"
            action="Alle anzeigen"
            onAction={() => navigate("/finanzen")}
          />
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="pb-2 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                    Mitglied
                  </th>
                  <th className="pb-2 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                    Sparte
                  </th>
                  <th className="pb-2 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                    Betrag
                  </th>
                  <th className="pb-2 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                    Tage
                  </th>
                  <th className="pb-2 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                    Stufe
                  </th>
                </tr>
              </thead>
              <tbody>
                {d.offenePosten.map((p) => (
                  <ClickableRow
                    key={p.id}
                    href="/mitglieder"
                    className="border-b border-gray-50 last:border-0"
                  >
                    <td className="py-2.5 text-gray-700">
                      {p.mitglied}
                    </td>
                    <td className="py-2.5">
                      <SpartenChip name={p.sparte} />
                    </td>
                    <td className="py-2.5 text-right tabular-nums text-gray-900">
                      {p.betrag.toLocaleString("de-DE")} €
                    </td>
                    <td className="py-2.5 text-right tabular-nums text-gray-500">
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
        <div className="col-span-2 rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
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
      <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
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
