import { useState, useMemo, useEffect, useCallback } from "react";
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
import api from "@/lib/api";
import type { SpartenleiterDashboard, HeatmapCell } from "@/types/dashboard";

// Backend API response types
interface ApiSpartenleiterKPIs {
  member_count: number;
  avg_attendance_pct: number;
  budget_utilization_pct: number;
  risk_count: number;
}

interface ApiHeatmapRow {
  day: number;
  cells: number[];
}

interface ApiTrainingItem {
  group: string;
  trainer: string;
  registered: number;
  max_participants: number;
  weekday: string;
  time: string;
}

interface ApiRiskMember {
  member_id: number;
  name: string;
  reason: string;
}

interface ApiBudgetDonut {
  used: number;
  committed: number;
  free: number;
}

interface ApiSpartenleiterResponse {
  kpis: ApiSpartenleiterKPIs;
  attendance_heatmap: ApiHeatmapRow[];
  training_schedule: ApiTrainingItem[];
  risk_members: ApiRiskMember[];
  budget_donut: ApiBudgetDonut;
}

const WEEKDAY_SHORT: Record<string, string> = {
  Montag: "Mo", Dienstag: "Di", Mittwoch: "Mi",
  Donnerstag: "Do", Freitag: "Fr", Samstag: "Sa", Sonntag: "So",
};

function mapApiToSpartenleiterDashboard(
  resp: ApiSpartenleiterResponse,
  sparteName: string
): SpartenleiterDashboard {
  const sparteColor = SPARTEN_COLORS[sparteName] || "#6b7280";

  // Budget: reverse-calculate total from utilization percentage
  // If utilization is 0, we can't know total, but used=0 anyway
  const totalBudget = resp.kpis.budget_utilization_pct > 0
    ? Math.round((resp.budget_donut.used + resp.budget_donut.committed + resp.budget_donut.free))
    : resp.budget_donut.used + resp.budget_donut.committed + resp.budget_donut.free;

  const kpis = {
    mitglieder: resp.kpis.member_count,
    mitgliederTrend: 0,
    durchschnittAnwesenheit: resp.kpis.avg_attendance_pct,
    anwesenheitTrend: 0,
    budgetVerbrauch: resp.budget_donut.used,
    budgetTotal: totalBudget,
    risikoMitglieder: resp.kpis.risk_count,
  };

  // Convert heatmap: backend gives {day, cells[12]} -> frontend expects {week, day, value}
  const heatmap: HeatmapCell[] = [];
  for (const row of resp.attendance_heatmap) {
    for (let week = 0; week < row.cells.length; week++) {
      heatmap.push({ week, day: row.day, value: row.cells[week] });
    }
  }

  const trainings = resp.training_schedule.map((t, idx) => ({
    id: String(idx + 1),
    tag: WEEKDAY_SHORT[t.weekday] || t.weekday.slice(0, 2),
    zeit: t.time,
    gruppe: t.group,
    trainer: t.trainer,
    kapazitaet: t.max_participants,
    angemeldet: t.registered,
  }));

  const risikoMitglieder = resp.risk_members.map((m) => ({
    id: String(m.member_id),
    name: m.name,
    tageSeitLetztemTraining: 0,
    beitragskategorie: m.reason,
  }));

  const budgetSegments = [
    { name: "Verbraucht", value: resp.budget_donut.used, color: sparteColor },
    { name: "Gebunden", value: resp.budget_donut.committed, color: `${sparteColor}60` },
    { name: "Frei", value: resp.budget_donut.free, color: "#e5e7eb" },
  ];

  return { kpis, heatmap, trainings, risikoMitglieder, budgetSegments };
}

const DAY_LABELS = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"];

interface SpartenleiterViewProps {
  data?: Record<string, SpartenleiterDashboard> | null;
}

export function SpartenleiterView({ data }: SpartenleiterViewProps) {
  const [activeSparte, setActiveSparte] = useState(SPARTEN_NAMES[0]);
  const [apiCache, setApiCache] = useState<Record<string, SpartenleiterDashboard>>({});
  const [loading, setLoading] = useState(!data);
  const [error, setError] = useState<string | null>(null);

  const fetchSparteData = useCallback(async (sparte: string) => {
    if (data) return;
    setLoading(true);
    setError(null);
    try {
      const resp = await api.get<ApiSpartenleiterResponse>(
        `/api/dashboard/spartenleiter/${encodeURIComponent(sparte)}`
      );
      const mapped = mapApiToSpartenleiterDashboard(resp, sparte);
      setApiCache((prev) => ({ ...prev, [sparte]: mapped }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Fehler beim Laden der Daten");
    } finally {
      setLoading(false);
    }
  }, [data]);

  useEffect(() => {
    if (!data && !apiCache[activeSparte]) {
      fetchSparteData(activeSparte);
    }
  }, [activeSparte, data, apiCache, fetchSparteData]);

  const allData = data ?? apiCache;
  const d = allData[activeSparte];

  const handleSparteChange = (sparte: string) => {
    setActiveSparte(sparte);
  };
  const sparteColor = SPARTEN_COLORS[activeSparte] || "#6b7280";

  // Stable heatmap memoized per sparte
  const heatmapData = useMemo(() => d?.heatmap ?? [], [d?.heatmap]);

  function getHeatmapColor(value: number) {
    if (value === 0) return "#f3f4f6";
    const opacities = [0, 0.15, 0.35, 0.6];
    return `${sparteColor}${Math.round((opacities[value] || 0) * 255)
      .toString(16)
      .padStart(2, "0")}`;
  }

  // Render loading/error before the main content, but keep switcher visible
  const renderContent = () => {
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
            onClick={() => fetchSparteData(activeSparte)}
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

    return null;
  };

  return (
    <div className="space-y-6 p-6">
      {/* Sparten Switcher */}
      <div className="flex items-center gap-2">
        {SPARTEN_NAMES.map((name) => (
          <button
            key={name}
            onClick={() => handleSparteChange(name)}
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

      {renderContent() || (<>

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
      </>)}
    </div>
  );
}
