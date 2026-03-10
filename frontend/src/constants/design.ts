// Sparten colors
export const SPARTEN_COLORS: Record<string, string> = {
  Fussball: "#3b82f6",
  Tennis: "#f59e0b",
  Fitness: "#10b981",
  Leichtathletik: "#a855f7",
};

export const SPARTEN_NAMES = Object.keys(SPARTEN_COLORS);

// Status colors (for member status)
export const STATUS_COLORS = {
  aktiv: { bg: "bg-emerald-50", text: "text-emerald-700", label: "Aktiv" },
  passiv: { bg: "bg-amber-50", text: "text-amber-700", label: "Passiv" },
  gekuendigt: { bg: "bg-red-50", text: "text-red-700", label: "Gekündigt" },
  ehrenmitglied: { bg: "bg-blue-50", text: "text-blue-700", label: "Ehrenmitglied" },
} as const;

// Invoice/payment status (legacy, kept for backward compat)
export const PAYMENT_STATUS_COLORS = {
  bezahlt: { color: "#10b981", label: "Bezahlt" },
  offen: { color: "#3b82f6", label: "Offen" },
  ueberfaellig: { color: "#ef4444", label: "Überfällig" },
  storniert: { color: "#6b7280", label: "Storniert" },
} as const;

// Rechnung status colors (new legally-compliant statuses)
export const RECHNUNG_STATUS_COLORS = {
  entwurf: { bg: "bg-gray-50", text: "text-gray-700", label: "Entwurf" },
  gestellt: { bg: "bg-blue-50", text: "text-blue-700", label: "Gestellt" },
  faellig: { bg: "bg-amber-50", text: "text-amber-700", label: "Fällig" },
  mahnung_1: { bg: "bg-orange-50", text: "text-orange-700", label: "Mahnung 1" },
  mahnung_2: { bg: "bg-red-50", text: "text-red-700", label: "Mahnung 2" },
  mahnung_3: { bg: "bg-red-100", text: "text-red-800", label: "Mahnung 3" },
  bezahlt: { bg: "bg-emerald-50", text: "text-emerald-700", label: "Bezahlt" },
  teilbezahlt: { bg: "bg-cyan-50", text: "text-cyan-700", label: "Teilbezahlt" },
  storniert: { bg: "bg-gray-100", text: "text-gray-500", label: "Storniert" },
  abgeschrieben: { bg: "bg-slate-100", text: "text-slate-600", label: "Abgeschrieben" },
} as const;

export const RECHNUNG_TYP_LABELS: Record<string, string> = {
  mitgliedsbeitrag: "Mitgliedsbeitrag",
  kursgebuehr: "Kursgebühr",
  hallenmiete: "Hallenmiete",
  sponsoring: "Sponsoring",
  sonstige: "Sonstige",
  storno: "Storno",
  mahnung: "Mahnung",
};

export const SPHARE_CODES: Record<string, string> = {
  ideell: "IB",
  zweckbetrieb: "ZB",
  vermoegensverwaltung: "VM",
  wirtschaftlich: "WG",
};

export const STEUERBEFREIUNG_VORLAGEN = [
  { label: "§4 Nr. 22b UStG (Mitgliedsbeiträge)", text: "Die Leistung ist nach §4 Nr. 22b UStG von der Umsatzsteuer befreit." },
  { label: "§65 AO / §4 Nr. 22a UStG (Zweckbetrieb)", text: "Steuerfreier Zweckbetrieb gemäß §65 AO." },
  { label: "§19 UStG (Kleinunternehmer)", text: "Gemäß §19 UStG wird keine Umsatzsteuer berechnet." },
];

// Sphere colors (tax spheres)
export const SPHERE_COLORS = {
  ideell: { bg: "bg-blue-50", text: "text-blue-700", label: "Ideell" },
  zweckbetrieb: { bg: "bg-emerald-50", text: "text-emerald-700", label: "Zweckbetrieb" },
  vermoegensverwaltung: { bg: "bg-amber-50", text: "text-amber-700", label: "Vermögensverwaltung" },
  wirtschaftlich: { bg: "bg-purple-50", text: "text-purple-700", label: "Wirtschaftlich" },
} as const;

// Semantic colors
export const SEMANTIC_COLORS = {
  success: "#10b981",
  warning: "#f59e0b",
  danger: "#ef4444",
  info: "#3b82f6",
  purple: "#a855f7",
} as const;

// Mahnstufen (dunning levels)
export const MAHNSTUFEN_COLORS = {
  0: { bg: "bg-emerald-50", text: "text-emerald-700", label: "OK" },
  1: { bg: "bg-amber-50", text: "text-amber-700", label: "M1" },
  2: { bg: "bg-red-50", text: "text-red-700", label: "M2" },
  3: { bg: "bg-red-100", text: "text-red-800", label: "M3" },
} as const;

// Chart constants
export const CHART = {
  gridStroke: "#e5e7eb",
  tickFill: "#6b7280",
  tickFontSize: 12,
  tooltipBg: "#ffffff",
  tooltipBorder: "#e5e7eb",
  heights: { sm: 180, md: 240, lg: 280 },
  barRadius: [4, 4, 0, 0] as [number, number, number, number],
} as const;

// Utilization thresholds
export const UTILIZATION = {
  ok: { max: 70, color: "text-emerald-600" },
  warning: { max: 90, color: "text-amber-600" },
  danger: { max: 100, color: "text-red-600" },
} as const;
