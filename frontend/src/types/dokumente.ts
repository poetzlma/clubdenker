export interface Protokoll {
  id: number
  titel: string
  datum: string
  inhalt: string
  typ: string
  erstellt_von: string | null
  teilnehmer: string | null
  beschluesse: string | null
  created_at: string | null
}

export interface ProtokollListResponse {
  items: Protokoll[]
  total: number
  page: number
  page_size: number
}

export type ProtokollTyp =
  | "vorstandssitzung"
  | "mitgliederversammlung"
  | "abteilungssitzung"
  | "sonstige"

export const PROTOKOLL_TYP_LABELS: Record<ProtokollTyp, string> = {
  vorstandssitzung: "Vorstandssitzung",
  mitgliederversammlung: "Mitgliederversammlung",
  abteilungssitzung: "Abteilungssitzung",
  sonstige: "Sonstige",
}
