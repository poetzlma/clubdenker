export interface Member {
  id: number;
  mitgliedsnummer: string;
  vorname: string;
  nachname: string;
  email: string;
  telefon: string;
  geburtsdatum: string;
  strasse: string;
  plz: string;
  ort: string;
  eintrittsdatum: string;
  austrittsdatum: string | null;
  status: 'aktiv' | 'passiv' | 'gekuendigt' | 'ehrenmitglied';
  beitragskategorie: 'erwachsene' | 'jugend' | 'familie' | 'passiv' | 'ehrenmitglied';
  notizen: string | null;
  abteilungen: string[];
}

export interface MemberListResponse {
  items: Member[];
  total: number;
  page: number;
  page_size: number;
}
