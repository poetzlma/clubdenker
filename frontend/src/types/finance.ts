export interface Buchung {
  id: number;
  buchungsdatum: string;
  betrag: number;
  beschreibung: string;
  konto: string;
  gegenkonto: string;
  sphare: 'ideell' | 'zweckbetrieb' | 'vermoegensverwaltung' | 'wirtschaftlich';
  mitglied_id: number | null;
  created_at: string;
}

export interface Rechnung {
  id: number;
  rechnungsnummer: string;
  mitglied_id: number;
  betrag: number;
  beschreibung: string;
  rechnungsdatum: string;
  faelligkeitsdatum: string;
  status: 'offen' | 'bezahlt' | 'ueberfaellig' | 'storniert';
  created_at: string;
}

export interface KassenstandSphare {
  sphare: string;
  betrag: number;
}

export interface Kassenstand {
  total: number;
  by_sphere: KassenstandSphare[];
}
