export interface Buchung {
  id: number;
  buchungsdatum: string;
  betrag: number;
  beschreibung: string;
  konto: string;
  gegenkonto: string;
  sphare: 'ideell' | 'zweckbetrieb' | 'vermoegensverwaltung' | 'wirtschaftlich';
  kostenstelle?: string | null;
  mitglied_id: number | null;
  created_at: string;
}

export type RechnungTyp = 'mitgliedsbeitrag' | 'kursgebuehr' | 'hallenmiete' | 'sponsoring' | 'sonstige' | 'storno' | 'mahnung';

export type RechnungStatus = 'entwurf' | 'gestellt' | 'faellig' | 'mahnung_1' | 'mahnung_2' | 'mahnung_3' | 'bezahlt' | 'teilbezahlt' | 'storniert' | 'abgeschrieben';

export type EmpfaengerTyp = 'mitglied' | 'sponsor' | 'extern';

export interface Rechnungsposition {
  id?: number;
  position_nr: number;
  beschreibung: string;
  menge: number;
  einheit: string;
  einzelpreis_netto: number;
  steuersatz: number;  // 0, 7, or 19
  steuerbefreiungsgrund?: string;
  gesamtpreis_netto: number;
  gesamtpreis_steuer: number;
  gesamtpreis_brutto: number;
  kostenstelle_id?: number;
}

export interface Rechnung {
  id: number;
  rechnungsnummer: string;
  rechnungstyp: RechnungTyp;
  status: RechnungStatus;
  mahnstufe: number;
  empfaenger_typ: EmpfaengerTyp;
  empfaenger_name?: string;
  mitglied_id?: number;
  mitglied_name?: string;
  rechnungsdatum: string;
  faelligkeitsdatum: string;
  leistungsdatum?: string;
  leistungszeitraum_von?: string;
  leistungszeitraum_bis?: string;
  summe_netto: number;
  summe_steuer: number;
  summe_brutto: number;
  betrag: number;  // alias for summe_brutto, backward compat
  bezahlt_betrag: number;
  offener_betrag: number;
  sphaere?: string;
  steuerhinweis_text?: string;
  zahlungsziel_tage: number;
  verwendungszweck?: string;
  gestellt_am?: string;
  bezahlt_am?: string;
  positionen: Rechnungsposition[];
  created_at: string;
}

export interface RechnungCreatePayload {
  rechnungstyp: RechnungTyp;
  empfaenger_typ: EmpfaengerTyp;
  mitglied_id?: number;
  empfaenger_name?: string;
  empfaenger_strasse?: string;
  empfaenger_plz?: string;
  empfaenger_ort?: string;
  sphaere?: string;
  leistungsdatum?: string;
  leistungszeitraum_von?: string;
  leistungszeitraum_bis?: string;
  zahlungsziel_tage?: number;
  steuerhinweis_text?: string;
  positionen: Array<{
    beschreibung: string;
    menge: number;
    einheit: string;
    einzelpreis_netto: number;
    steuersatz: number;
    steuerbefreiungsgrund?: string;
    kostenstelle_id?: number;
  }>;
}

// Backward compat: RechnungWithMitglied is now identical to Rechnung
export type RechnungWithMitglied = Rechnung;

// Eingangsrechnung (incoming invoice)
export type EingangsrechnungStatus = 'eingegangen' | 'geprueft' | 'freigegeben' | 'bezahlt' | 'abgelehnt';

export interface Eingangsrechnung {
  id: number;
  rechnungsnummer: string;
  aussteller_name: string;
  aussteller_strasse?: string | null;
  aussteller_plz?: string | null;
  aussteller_ort?: string | null;
  aussteller_steuernr?: string | null;
  aussteller_ust_id?: string | null;
  rechnungsdatum: string;
  faelligkeitsdatum?: string | null;
  leistungsdatum?: string | null;
  summe_netto: number;
  summe_steuer: number;
  summe_brutto: number;
  waehrung: string;
  status: EingangsrechnungStatus;
  kostenstelle_id?: number | null;
  sphaere?: string | null;
  quell_format?: string | null;
  notiz?: string | null;
  created_at?: string | null;
}

export interface RechnungTemplatePosition {
  beschreibung: string;
  menge: number;
  einheit: string;
  einzelpreis_netto?: number;
  steuersatz: number;
  steuerbefreiungsgrund?: string;
  platzhalter?: Record<string, string>;
}

export interface RechnungTemplate {
  id: string;
  name: string;
  beschreibung: string;
  rechnungstyp: RechnungTyp;
  sphaere?: string;
  empfaenger_typ?: EmpfaengerTyp;
  steuerhinweis_text?: string;
  zahlungsziel_tage: number;
  positionen: RechnungTemplatePosition[];
}

export interface Vereinsstammdaten {
  id: number;
  name: string;
  strasse: string;
  plz: string;
  ort: string;
  steuernummer?: string;
  ust_id?: string;
  iban: string;
  bic?: string;
  registergericht?: string;
  registernummer?: string;
}

export interface KassenstandSphare {
  sphare: string;
  betrag: number;
}

export interface Kassenstand {
  total: number;
  by_sphere: KassenstandSphare[];
}

export interface Kostenstelle {
  id: number;
  name: string;
  beschreibung: string;
  budget: number | null;
  freigabelimit: number | null;
  ausgegeben: number | null;
  verfuegbar: number | null;
}

export interface BeitragseinzugResult {
  status: string;
  year: number;
  month: number;
  processed: number;
  total_amount: number;
  errors: string[];
}

export interface MahnwesenResult {
  status: string;
  reminders_sent: number;
  overdue_members: number;
  total_overdue_amount: number;
}

export interface ComplianceFinding {
  category: string;
  severity: 'info' | 'warning' | 'critical';
  message: string;
  affected_count: number;
}

export interface ComplianceMonitorResult {
  findings: ComplianceFinding[];
  total: number;
  critical_count: number;
  warning_count: number;
  info_count: number;
}

export interface AufwandMonitorResult {
  status: string;
  cost_centers: {
    name: string;
    budget: number;
    spent: number;
    utilization_percent: number;
    warning: boolean;
  }[];
  total_budget: number;
  total_spent: number;
}

// Ehrenamt (volunteer compensation)
export type AufwandTyp = 'uebungsleiter' | 'ehrenamt';

export interface Aufwandsentschaedigung {
  id: number;
  mitglied_id: number;
  mitglied_name: string;
  betrag: number;
  datum: string;
  typ: AufwandTyp;
  beschreibung: string;
  created_at?: string | null;
}

export interface FreibetragSummary {
  mitglied_id: number;
  mitglied_name: string;
  typ: AufwandTyp;
  total: number;
  limit: number;
  remaining: number;
  percent: number;
  warning: boolean;
}

export interface BuchungCreatePayload {
  beschreibung: string;
  betrag: number;
  konto: string;
  gegenkonto: string;
  sphare: Buchung["sphare"];
  kostenstelle?: string;
}

export interface EuerSumme {
  einnahmen: number;
  ausgaben: number;
  ergebnis: number;
}

export interface EuerSphareItem {
  sphare: string;
  einnahmen: number;
  ausgaben: number;
  ergebnis: number;
}

export interface EuerMonatItem {
  monat: string;
  einnahmen: number;
  ausgaben: number;
  ergebnis: number;
}

export interface EuerKostenstelleItem {
  kostenstelle: string;
  einnahmen: number;
  ausgaben: number;
  ergebnis: number;
}

export interface EuerReport {
  jahr: number;
  zeitraum: { von: string; bis: string };
  gesamt: EuerSumme;
  nach_sphare: EuerSphareItem[];
  nach_monat: EuerMonatItem[];
  nach_kostenstelle: EuerKostenstelleItem[];
}

export interface SepaMandat {
  id: number;
  mitglied_id: number;
  mitglied_name?: string | null;
  iban: string;
  bic?: string | null;
  kontoinhaber: string;
  mandatsreferenz: string;
  unterschriftsdatum: string;
  gueltig_ab: string;
  gueltig_bis?: string | null;
  aktiv: boolean;
}

export interface SepaMandatCreatePayload {
  mitglied_id: number;
  iban: string;
  bic?: string;
  kontoinhaber: string;
  mandatsreferenz: string;
  unterschriftsdatum: string;
  gueltig_ab: string;
  gueltig_bis?: string;
}
