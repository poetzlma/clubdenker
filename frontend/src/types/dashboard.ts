export interface TrendDataPoint {
  month: string;
  Fussball: number;
  Tennis: number;
  Fitness: number;
  Leichtathletik: number;
}

export interface CashflowPoint {
  month: string;
  einnahmen: number;
  ausgaben: number;
}

export interface SpartenGesundheit {
  name: string;
  budget: number;
  used: number;
  percent: number;
}

export interface AktionItem {
  id: string;
  title: string;
  description: string;
  variant: "action" | "warn" | "ok";
  href?: string;
}

export interface VorstandKpi {
  mitglieder: number;
  mitgliederTrend: number;
  kassenstand: number;
  kassenstandTrend: number;
  offenePosten: number;
  offenePostenTrend: number;
  compliance: number;
}

export interface VorstandDashboard {
  kpis: VorstandKpi;
  memberTrend: TrendDataPoint[];
  spartenGesundheit: SpartenGesundheit[];
  cashflow: CashflowPoint[];
  aktionen: AktionItem[];
}

export interface OffenerPosten {
  id: string;
  mitglied: string;
  sparte: string;
  betrag: number;
  tageUeberfaellig: number;
  mahnstufe: 0 | 1 | 2 | 3;
}

export interface BudgetBurnItem {
  name: string;
  budget: number;
  used: number;
}

export interface LiquiditaetPoint {
  month: string;
  einnahmen: number;
  ausgaben: number;
}

export interface SchatzmeisterKpi {
  ideell: number;
  zweckbetrieb: number;
  offeneForderungen: number;
  offeneForderungenTrend: number;
  ueberweisungen: number;
}

export interface SepaStatus {
  betrag: number;
  anzahl: number;
  readiness: number;
  naechsterEinzug: string;
}

export interface SchatzmeisterDashboard {
  kpis: SchatzmeisterKpi;
  sepa: SepaStatus;
  offenePosten: OffenerPosten[];
  budgetBurn: BudgetBurnItem[];
  liquiditaet: LiquiditaetPoint[];
}

export interface Training {
  id: string;
  tag: string;
  zeit: string;
  gruppe: string;
  trainer: string;
  kapazitaet: number;
  angemeldet: number;
}

export interface RisikoMitglied {
  id: string;
  name: string;
  tageSeitLetztemTraining: number;
  beitragskategorie: string;
}

export interface HeatmapCell {
  week: number;
  day: number;
  value: number;
}

export interface BudgetSegment {
  name: string;
  value: number;
  color: string;
}

export interface SpartenleiterKpi {
  mitglieder: number;
  mitgliederTrend: number;
  durchschnittAnwesenheit: number;
  anwesenheitTrend: number;
  budgetVerbrauch: number;
  budgetTotal: number;
  risikoMitglieder: number;
}

export interface SpartenleiterDashboard {
  kpis: SpartenleiterKpi;
  heatmap: HeatmapCell[];
  trainings: Training[];
  risikoMitglieder: RisikoMitglied[];
  budgetSegments: BudgetSegment[];
}

export type DashboardView = "vorstand" | "schatzmeister" | "spartenleiter";
