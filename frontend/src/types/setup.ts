export interface Abteilung {
  id: number;
  name: string;
  beschreibung: string | null;
  mitglieder_count?: number;
  created_at: string;
}

export interface BeitragsKategorie {
  id: number;
  name: string;
  jahresbeitrag: number;
  beschreibung: string | null;
  created_at: string;
}

export interface AbteilungPayload {
  name: string;
  beschreibung?: string;
}

export interface BeitragsKategoriePayload {
  name: string;
  jahresbeitrag: number;
  beschreibung?: string;
}
