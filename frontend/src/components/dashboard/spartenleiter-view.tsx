import { useState, useMemo } from "react";
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { cn } from "@/lib/utils";
import { KpiCard } from "./kpi-card";
import { SectionHeader } from "./section-header";
import { ChartTooltip } from "./chart-tooltip";
import { ClickableCard } from "./clickable-card";
import { SPARTEN_COLORS, SPARTEN_NAMES, SEMANTIC_COLORS } from "@/constants/design";
import type { SpartenleiterDashboard, HeatmapCell } from "@/types/dashboard";

function generateHeatmap(): HeatmapCell[] {
  const cells: HeatmapCell[] = [];
  for (let week = 0; week < 12; week++) {
    for (let day = 0; day < 7; day++) {
      cells.push({
        week,
        day,
        value: Math.floor(Math.random() * 4),
      });
    }
  }
  return cells;
}

const MOCK_DATA_BY_SPARTE: Record<string, SpartenleiterDashboard> = {
  Fussball: {
    kpis: {
      mitglieder: 95,
      mitgliederTrend: 4.2,
      durchschnittAnwesenheit: 78,
      anwesenheitTrend: 2.1,
      budgetVerbrauch: 8400,
      budgetTotal: 12000,
      risikoMitglieder: 3,
    },
    heatmap: generateHeatmap(),
    trainings: [
      { id: "1", tag: "Mo", zeit: "18:00", gruppe: "Herren I", trainer: "M. Schmidt", kapazitaet: 22, angemeldet: 18 },
      { id: "2", tag: "Mi", zeit: "17:30", gruppe: "Jugend A", trainer: "K. Weber", kapazitaet: 18, angemeldet: 16 },
      { id: "3", tag: "Fr", zeit: "19:00", gruppe: "Herren II", trainer: "M. Schmidt", kapazitaet: 22, angemeldet: 14 },
      { id: "4", tag: "Sa", zeit: "10:00", gruppe: "Bambini", trainer: "L. Fischer", kapazitaet: 15, angemeldet: 12 },
    ],
    risikoMitglieder: [
      { id: "1", name: "P. Hoffmann", tageSeitLetztemTraining: 42, beitragskategorie: "erwachsene" },
      { id: "2", name: "R. Becker", tageSeitLetztemTraining: 35, beitragskategorie: "erwachsene" },
      { id: "3", name: "S. Klein", tageSeitLetztemTraining: 28, beitragskategorie: "jugend" },
    ],
    budgetSegments: [
      { name: "Verbraucht", value: 8400, color: "#3b82f6" },
      { name: "Gebunden", value: 1800, color: "#3b82f660" },
      { name: "Frei", value: 1800, color: "#e5e7eb" },
    ],
  },
  Tennis: {
    kpis: {
      mitglieder: 53,
      mitgliederTrend: 1.9,
      durchschnittAnwesenheit: 72,
      anwesenheitTrend: -1.3,
      budgetVerbrauch: 5200,
      budgetTotal: 8000,
      risikoMitglieder: 2,
    },
    heatmap: generateHeatmap(),
    trainings: [
      { id: "1", tag: "Di", zeit: "16:00", gruppe: "Damen", trainer: "A. Lange", kapazitaet: 12, angemeldet: 10 },
      { id: "2", tag: "Do", zeit: "18:00", gruppe: "Herren", trainer: "B. Richter", kapazitaet: 12, angemeldet: 8 },
      { id: "3", tag: "Sa", zeit: "09:00", gruppe: "Jugend", trainer: "A. Lange", kapazitaet: 10, angemeldet: 9 },
    ],
    risikoMitglieder: [
      { id: "1", name: "M. Braun", tageSeitLetztemTraining: 38, beitragskategorie: "erwachsene" },
      { id: "2", name: "K. Wolf", tageSeitLetztemTraining: 31, beitragskategorie: "erwachsene" },
    ],
    budgetSegments: [
      { name: "Verbraucht", value: 5200, color: "#f59e0b" },
      { name: "Gebunden", value: 1200, color: "#f59e0b60" },
      { name: "Frei", value: 1600, color: "#e5e7eb" },
    ],
  },
  Fitness: {
    kpis: {
      mitglieder: 49,
      mitgliederTrend: 6.5,
      durchschnittAnwesenheit: 85,
      anwesenheitTrend: 3.8,
      budgetVerbrauch: 5100,
      budgetTotal: 6000,
      risikoMitglieder: 1,
    },
    heatmap: generateHeatmap(),
    trainings: [
      { id: "1", tag: "Mo", zeit: "07:00", gruppe: "Frühsport", trainer: "J. Neumann", kapazitaet: 20, angemeldet: 18 },
      { id: "2", tag: "Mi", zeit: "19:00", gruppe: "Kraft", trainer: "J. Neumann", kapazitaet: 15, angemeldet: 14 },
      { id: "3", tag: "Fr", zeit: "18:00", gruppe: "Cardio", trainer: "S. Keller", kapazitaet: 20, angemeldet: 17 },
    ],
    risikoMitglieder: [
      { id: "1", name: "H. Zimmermann", tageSeitLetztemTraining: 25, beitragskategorie: "erwachsene" },
    ],
    budgetSegments: [
      { name: "Verbraucht", value: 5100, color: "#10b981" },
      { name: "Gebunden", value: 600, color: "#10b98160" },
      { name: "Frei", value: 300, color: "#e5e7eb" },
    ],
  },
  Leichtathletik: {
    kpis: {
      mitglieder: 34,
      mitgliederTrend: -2.1,
      durchschnittAnwesenheit: 68,
      anwesenheitTrend: -4.2,
      budgetVerbrauch: 1600,
      budgetTotal: 4000,
      risikoMitglieder: 4,
    },
    heatmap: generateHeatmap(),
    trainings: [
      { id: "1", tag: "Di", zeit: "17:00", gruppe: "Sprint", trainer: "C. Fuchs", kapazitaet: 16, angemeldet: 10 },
      { id: "2", tag: "Do", zeit: "17:00", gruppe: "Ausdauer", trainer: "C. Fuchs", kapazitaet: 16, angemeldet: 8 },
    ],
    risikoMitglieder: [
      { id: "1", name: "T. Schäfer", tageSeitLetztemTraining: 55, beitragskategorie: "jugend" },
      { id: "2", name: "N. Koch", tageSeitLetztemTraining: 48, beitragskategorie: "erwachsene" },
      { id: "3", name: "L. Bauer", tageSeitLetztemTraining: 40, beitragskategorie: "erwachsene" },
      { id: "4", name: "E. Werner", tageSeitLetztemTraining: 33, beitragskategorie: "jugend" },
    ],
    budgetSegments: [
      { name: "Verbraucht", value: 1600, color: "#a855f7" },
      { name: "Gebunden", value: 800, color: "#a855f760" },
      { name: "Frei", value: 1600, color: "#e5e7eb" },
    ],
  },
};

const DAY_LABELS = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"];

interface SpartenleiterViewProps {
  data?: Record<string, SpartenleiterDashboard> | null;
}

export function SpartenleiterView({ data }: SpartenleiterViewProps) {
  const [activeSparte, setActiveSparte] = useState(SPARTEN_NAMES[0]);
  const allData = data ?? MOCK_DATA_BY_SPARTE;
  const d = allData[activeSparte] ?? Object.values(allData)[0];
  const sparteColor = SPARTEN_COLORS[activeSparte] || "#6b7280";

  // Stable heatmap memoized per sparte
  const heatmapData = useMemo(() => d.heatmap, [d.heatmap]);

  function getHeatmapColor(value: number) {
    if (value === 0) return "#f3f4f6";
    const opacities = [0, 0.15, 0.35, 0.6];
    return `${sparteColor}${Math.round((opacities[value] || 0) * 255)
      .toString(16)
      .padStart(2, "0")}`;
  }

  return (
    <div className="space-y-6 p-6">
      {/* Sparten Switcher */}
      <div className="flex items-center gap-2">
        {SPARTEN_NAMES.map((name) => (
          <button
            key={name}
            onClick={() => setActiveSparte(name)}
            className={cn(
              "rounded-lg border px-4 py-2 text-sm font-medium transition-colors",
              activeSparte === name
                ? "text-gray-900"
                : "border-gray-200 bg-white text-gray-500 hover:text-gray-700"
            )}
            style={
              activeSparte === name
                ? {
                    borderColor: SPARTEN_COLORS[name],
                    backgroundColor: `${SPARTEN_COLORS[name]}15`,
                  }
                : undefined
            }
          >
            {name}
          </button>
        ))}
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-4 gap-4">
        <KpiCard
          label="Mitglieder"
          value={d.kpis.mitglieder.toString()}
          trend={d.kpis.mitgliederTrend}
          trendLabel="vs. Vormonat"
          accentColor={sparteColor}
          href="/mitglieder"
        />
        <KpiCard
          label="Ø Anwesenheit"
          value={`${d.kpis.durchschnittAnwesenheit}%`}
          trend={d.kpis.anwesenheitTrend}
          trendLabel="vs. Vormonat"
          accentColor={sparteColor}
        />
        <KpiCard
          label="Budget"
          value={`${d.kpis.budgetVerbrauch.toLocaleString("de-DE")} / ${d.kpis.budgetTotal.toLocaleString("de-DE")} €`}
          accentColor={sparteColor}
          href="/finanzen"
        />
        <KpiCard
          label="Risiko-Mitglieder"
          value={d.kpis.risikoMitglieder.toString()}
          accentColor={SEMANTIC_COLORS.danger}
        />
      </div>

      {/* Middle row */}
      <div className="grid grid-cols-2 gap-4">
        {/* Attendance Heatmap */}
        <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
          <SectionHeader label="Anwesenheit (12 Wochen)" />
          <div className="mt-3">
            <div className="flex gap-1">
              <div className="flex flex-col gap-1 pr-1 pt-0">
                {DAY_LABELS.map((day) => (
                  <div
                    key={day}
                    className="flex h-5 items-center text-xs text-gray-400"
                  >
                    {day}
                  </div>
                ))}
              </div>
              <div className="grid grid-cols-12 gap-1">
                {Array.from({ length: 12 }, (_, week) =>
                  Array.from({ length: 7 }, (_, day) => {
                    const cell = heatmapData.find(
                      (c) => c.week === week && c.day === day
                    );
                    return (
                      <div
                        key={`${week}-${day}`}
                        className="h-5 w-5 rounded"
                        style={{
                          backgroundColor: getHeatmapColor(cell?.value ?? 0),
                        }}
                        title={`Woche ${week + 1}, ${DAY_LABELS[day]}: Level ${cell?.value ?? 0}`}
                      />
                    );
                  })
                )}
              </div>
            </div>
            <div className="mt-2 flex items-center gap-1 text-xs text-gray-400">
              <span>Weniger</span>
              {[0, 1, 2, 3].map((level) => (
                <div
                  key={level}
                  className="h-3 w-3 rounded-sm"
                  style={{ backgroundColor: getHeatmapColor(level) }}
                />
              ))}
              <span>Mehr</span>
            </div>
          </div>
        </div>

        {/* Training cards */}
        <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
          <SectionHeader label="Trainings diese Woche" />
          <div className="mt-3 space-y-2">
            {d.trainings.map((t) => {
              const fillPercent = Math.round(
                (t.angemeldet / t.kapazitaet) * 100
              );
              return (
                <div
                  key={t.id}
                  className="flex items-center justify-between rounded-md border border-gray-100 bg-gray-50 px-3 py-2"
                >
                  <div>
                    <p className="text-sm font-medium text-gray-900">
                      {t.tag} {t.zeit} &middot; {t.gruppe}
                    </p>
                    <p className="text-xs text-gray-500">
                      Trainer: {t.trainer}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="tabular-nums text-xs text-gray-500">
                      {t.angemeldet}/{t.kapazitaet}
                    </span>
                    <div className="h-1.5 w-16 overflow-hidden rounded-full bg-gray-100">
                      <div
                        className="h-full rounded-full"
                        style={{
                          width: `${fillPercent}%`,
                          backgroundColor:
                            fillPercent > 90
                              ? SEMANTIC_COLORS.danger
                              : fillPercent > 70
                                ? SEMANTIC_COLORS.warning
                                : sparteColor,
                        }}
                      />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Bottom row */}
      <div className="grid grid-cols-2 gap-4">
        {/* Risiko-Mitglieder */}
        <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
          <SectionHeader label="Risiko-Mitglieder" />
          <div className="mt-3 space-y-2">
            {d.risikoMitglieder.map((m) => (
              <ClickableCard key={m.id} href="/mitglieder">
                <div
                  className="flex items-center justify-between rounded-md border border-red-100 bg-red-50 px-3 py-2"
                >
                  <div>
                    <p className="text-sm font-medium text-gray-900">
                      {m.name}
                    </p>
                    <p className="text-xs text-gray-500">
                      {m.beitragskategorie}
                    </p>
                  </div>
                  <span className="tabular-nums text-xs font-medium" style={{ color: SEMANTIC_COLORS.danger }}>
                    {m.tageSeitLetztemTraining} Tage
                  </span>
                </div>
              </ClickableCard>
            ))}
          </div>
        </div>

        {/* Budget Donut */}
        <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
          <SectionHeader label="Budget-Verteilung" />
          <div className="mt-3 flex items-center justify-center">
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={d.budgetSegments}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={90}
                  dataKey="value"
                  stroke="none"
                >
                  {d.budgetSegments.map((entry, i) => (
                    <Cell key={i} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  content={
                    <ChartTooltip
                      formatter={(v) => `${v.toLocaleString("de-DE")} €`}
                    />
                  }
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-2 flex justify-center gap-4">
            {d.budgetSegments.map((s) => (
              <div key={s.name} className="flex items-center gap-1.5 text-xs">
                <span
                  className="h-2 w-2 rounded-full"
                  style={{ backgroundColor: s.color }}
                />
                <span className="text-gray-500">{s.name}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
