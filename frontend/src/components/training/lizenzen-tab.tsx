import { useState, useEffect, useCallback } from "react"
import { Plus, Trash2 } from "lucide-react"
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
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import api from "@/lib/api"

interface TrainerLizenz {
  id: number
  mitglied_id: number
  lizenztyp: string
  bezeichnung: string
  ausstellungsdatum: string
  ablaufdatum: string
  lizenznummer: string | null
  ausstellende_stelle: string | null
  created_at: string | null
}

interface MitgliedOption {
  id: number
  vorname: string
  nachname: string
  mitgliedsnummer: string
}

const LIZENZTYP_LABELS: Record<string, string> = {
  trainerlizenz_c: "Trainerlizenz C",
  trainerlizenz_b: "Trainerlizenz B",
  trainerlizenz_a: "Trainerlizenz A",
  erste_hilfe: "Erste Hilfe",
  jugendleiter: "Jugendleiter",
  rettungsschwimmer: "Rettungsschwimmer",
  sonstiges: "Sonstiges",
}

type StatusFilter = "alle" | "gueltig" | "ablaufend" | "abgelaufen"

function getLizenzStatus(ablaufdatum: string): { label: string; variant: "default" | "secondary" | "destructive" } {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const expiry = new Date(ablaufdatum)
  expiry.setHours(0, 0, 0, 0)
  const diffDays = Math.ceil((expiry.getTime() - today.getTime()) / (1000 * 60 * 60 * 24))

  if (diffDays < 0) {
    return { label: "Abgelaufen", variant: "destructive" }
  }
  if (diffDays <= 90) {
    return { label: "Laeuft ab", variant: "secondary" }
  }
  return { label: "Gueltig", variant: "default" }
}

export function LizenzenTab() {
  const [lizenzen, setLizenzen] = useState<TrainerLizenz[]>([])
  const [mitglieder, setMitglieder] = useState<MitgliedOption[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<StatusFilter>("alle")
  const [dialogOpen, setDialogOpen] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [deleting, setDeleting] = useState<TrainerLizenz | null>(null)

  // Form state
  const [formMitgliedId, setFormMitgliedId] = useState("")
  const [formLizenztyp, setFormLizenztyp] = useState("")
  const [formBezeichnung, setFormBezeichnung] = useState("")
  const [formAusstellungsdatum, setFormAusstellungsdatum] = useState("")
  const [formAblaufdatum, setFormAblaufdatum] = useState("")
  const [formLizenznummer, setFormLizenznummer] = useState("")
  const [formAusstellendeStelle, setFormAusstellendeStelle] = useState("")
  const [saving, setSaving] = useState(false)

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (filter === "abgelaufen") {
        params.set("expired", "true")
      } else if (filter === "gueltig" || filter === "ablaufend") {
        params.set("expired", "false")
      }
      const queryStr = params.toString() ? `?${params.toString()}` : ""
      const [lizData, mData] = await Promise.all([
        api.get<TrainerLizenz[]>(`/api/training/lizenzen${queryStr}`),
        api.get<{ items: MitgliedOption[] }>("/api/mitglieder"),
      ])
      setLizenzen(lizData)
      setMitglieder(mData.items ?? [])
    } catch {
      setLizenzen([])
      setMitglieder([])
    } finally {
      setLoading(false)
    }
  }, [filter])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const filteredLizenzen = lizenzen.filter((liz) => {
    if (filter === "ablaufend") {
      const status = getLizenzStatus(liz.ablaufdatum)
      return status.label === "Laeuft ab"
    }
    return true
  })

  function getMitgliedName(mitgliedId: number): string {
    const m = mitglieder.find((m) => m.id === mitgliedId)
    return m ? `${m.vorname} ${m.nachname}` : `Mitglied #${mitgliedId}`
  }

  function openCreate() {
    setFormMitgliedId("")
    setFormLizenztyp("")
    setFormBezeichnung("")
    setFormAusstellungsdatum("")
    setFormAblaufdatum("")
    setFormLizenznummer("")
    setFormAusstellendeStelle("")
    setDialogOpen(true)
  }

  function openDelete(liz: TrainerLizenz) {
    setDeleting(liz)
    setDeleteDialogOpen(true)
  }

  async function handleCreate() {
    const payload = {
      mitglied_id: parseInt(formMitgliedId),
      lizenztyp: formLizenztyp,
      bezeichnung: formBezeichnung,
      ausstellungsdatum: formAusstellungsdatum,
      ablaufdatum: formAblaufdatum,
      lizenznummer: formLizenznummer || undefined,
      ausstellende_stelle: formAusstellendeStelle || undefined,
    }

    setSaving(true)
    try {
      await api.post("/api/training/lizenzen", payload)
    } catch {
      // API error
    }
    setSaving(false)
    setDialogOpen(false)
    fetchData()
  }

  async function handleDelete() {
    if (!deleting) return
    try {
      await api.delete(`/api/training/lizenzen/${deleting.id}`)
    } catch {
      // API error
    }
    setDeleteDialogOpen(false)
    setDeleting(null)
    fetchData()
  }

  const isFormValid =
    formMitgliedId &&
    formLizenztyp &&
    formBezeichnung.trim() &&
    formAusstellungsdatum &&
    formAblaufdatum

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
        <div className="space-y-1">
          <CardTitle>Trainer-Lizenzen</CardTitle>
          <CardDescription>
            Qualifikationen und Zertifikate der Trainer verwalten.
          </CardDescription>
        </div>
        <div className="flex items-center gap-2">
          <Select value={filter} onValueChange={(v) => setFilter(v as StatusFilter)}>
            <SelectTrigger className="w-[160px]">
              <SelectValue placeholder="Filter" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="alle">Alle</SelectItem>
              <SelectItem value="gueltig">Gueltig</SelectItem>
              <SelectItem value="ablaufend">Laeuft ab</SelectItem>
              <SelectItem value="abgelaufen">Abgelaufen</SelectItem>
            </SelectContent>
          </Select>
          <Button onClick={openCreate} size="sm">
            <Plus className="mr-2 h-4 w-4" />
            Neue Lizenz
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <p className="text-sm text-muted-foreground">Laden...</p>
        ) : filteredLizenzen.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Keine Lizenzen vorhanden.
          </p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Trainer</TableHead>
                <TableHead>Lizenztyp</TableHead>
                <TableHead>Bezeichnung</TableHead>
                <TableHead>Gueltig bis</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Aktionen</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredLizenzen.map((liz) => {
                const status = getLizenzStatus(liz.ablaufdatum)
                return (
                  <TableRow key={liz.id}>
                    <TableCell className="font-medium">
                      {getMitgliedName(liz.mitglied_id)}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">
                        {LIZENZTYP_LABELS[liz.lizenztyp] ?? liz.lizenztyp}
                      </Badge>
                    </TableCell>
                    <TableCell>{liz.bezeichnung}</TableCell>
                    <TableCell>
                      {new Date(liz.ablaufdatum).toLocaleDateString("de-DE")}
                    </TableCell>
                    <TableCell>
                      <Badge variant={status.variant}>{status.label}</Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => openDelete(liz)}
                        aria-label={`${liz.bezeichnung} loeschen`}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        )}
      </CardContent>

      {/* Create Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>Neue Lizenz erfassen</DialogTitle>
            <DialogDescription>
              Erfassen Sie eine neue Trainer-Lizenz oder Qualifikation.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label htmlFor="liz-mitglied">Trainer (Mitglied)</Label>
              <Select value={formMitgliedId} onValueChange={setFormMitgliedId}>
                <SelectTrigger id="liz-mitglied">
                  <SelectValue placeholder="Mitglied waehlen" />
                </SelectTrigger>
                <SelectContent>
                  {mitglieder.map((m) => (
                    <SelectItem key={m.id} value={m.id.toString()}>
                      {m.vorname} {m.nachname} ({m.mitgliedsnummer})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="liz-typ">Lizenztyp</Label>
              <Select value={formLizenztyp} onValueChange={setFormLizenztyp}>
                <SelectTrigger id="liz-typ">
                  <SelectValue placeholder="Lizenztyp waehlen" />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(LIZENZTYP_LABELS).map(([value, label]) => (
                    <SelectItem key={value} value={value}>
                      {label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="liz-bezeichnung">Bezeichnung</Label>
              <Input
                id="liz-bezeichnung"
                value={formBezeichnung}
                onChange={(e) => setFormBezeichnung(e.target.value)}
                placeholder="z.B. DOSB Trainerlizenz C Breitensport"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="liz-ausstellung">Ausstellungsdatum</Label>
                <Input
                  id="liz-ausstellung"
                  type="date"
                  value={formAusstellungsdatum}
                  onChange={(e) => setFormAusstellungsdatum(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="liz-ablauf">Ablaufdatum</Label>
                <Input
                  id="liz-ablauf"
                  type="date"
                  value={formAblaufdatum}
                  onChange={(e) => setFormAblaufdatum(e.target.value)}
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="liz-nummer">Lizenznummer (optional)</Label>
              <Input
                id="liz-nummer"
                value={formLizenznummer}
                onChange={(e) => setFormLizenznummer(e.target.value)}
                placeholder="z.B. TC-2024-001"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="liz-stelle">Ausstellende Stelle (optional)</Label>
              <Input
                id="liz-stelle"
                value={formAusstellendeStelle}
                onChange={(e) => setFormAusstellendeStelle(e.target.value)}
                placeholder="z.B. DOSB, DRK, Landesverband"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Abbrechen
            </Button>
            <Button onClick={handleCreate} disabled={!isFormValid || saving}>
              {saving ? "Speichern..." : "Speichern"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Lizenz loeschen</DialogTitle>
            <DialogDescription>
              Moechten Sie die Lizenz &quot;{deleting?.bezeichnung}&quot; wirklich
              loeschen? Diese Aktion kann nicht rueckgaengig gemacht werden.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
              Abbrechen
            </Button>
            <Button variant="destructive" onClick={handleDelete}>
              Loeschen
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  )
}
