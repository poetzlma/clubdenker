import { FileText } from "lucide-react"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"

interface Vorlage {
  name: string
  beschreibung: string
  kategorie: string
  status: "verfügbar" | "in Bearbeitung"
}

const VORLAGEN: Vorlage[] = [
  {
    name: "Satzung",
    beschreibung: "Vereinssatzung gemaess BGB und Landesrecht",
    kategorie: "Grunddokumente",
    status: "in Bearbeitung",
  },
  {
    name: "Beitragsordnung",
    beschreibung: "Regelung der Mitgliedsbeitraege und Gebuehren",
    kategorie: "Grunddokumente",
    status: "in Bearbeitung",
  },
  {
    name: "Geschaeftsordnung",
    beschreibung: "Regelung der internen Ablaeufe und Zustaendigkeiten",
    kategorie: "Grunddokumente",
    status: "in Bearbeitung",
  },
  {
    name: "Aufnahmeantrag",
    beschreibung: "Formular fuer den Vereinsbeitritt neuer Mitglieder",
    kategorie: "Formulare",
    status: "in Bearbeitung",
  },
  {
    name: "Kuendigungsformular",
    beschreibung: "Formular fuer die Beendigung der Mitgliedschaft",
    kategorie: "Formulare",
    status: "in Bearbeitung",
  },
  {
    name: "SEPA-Lastschriftmandat",
    beschreibung: "Einzugsermaechtigung fuer Lastschriftverfahren",
    kategorie: "Formulare",
    status: "in Bearbeitung",
  },
  {
    name: "Datenschutzerklaerung",
    beschreibung: "Informationen zur Verarbeitung personenbezogener Daten",
    kategorie: "DSGVO",
    status: "in Bearbeitung",
  },
  {
    name: "Einwilligungserklaerung",
    beschreibung: "Zustimmung zur Datenverarbeitung und Bildveroeffentlichung",
    kategorie: "DSGVO",
    status: "in Bearbeitung",
  },
]

const KATEGORIE_VARIANT: Record<string, "default" | "secondary" | "outline"> = {
  Grunddokumente: "default",
  Formulare: "secondary",
  DSGVO: "outline",
}

export function VorlagenList() {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <FileText className="h-5 w-5 text-muted-foreground" />
          <div className="space-y-1">
            <CardTitle>Dokumentvorlagen</CardTitle>
            <CardDescription>
              Standardvorlagen fuer den Vereinsbetrieb. Vorlagen werden in einer
              zukuenftigen Version editierbar sein.
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Beschreibung</TableHead>
              <TableHead>Kategorie</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {VORLAGEN.map((v) => (
              <TableRow key={v.name}>
                <TableCell className="font-medium">{v.name}</TableCell>
                <TableCell>{v.beschreibung}</TableCell>
                <TableCell>
                  <Badge variant={KATEGORIE_VARIANT[v.kategorie] ?? "outline"}>
                    {v.kategorie}
                  </Badge>
                </TableCell>
                <TableCell>
                  <Badge variant="secondary">{v.status}</Badge>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}
