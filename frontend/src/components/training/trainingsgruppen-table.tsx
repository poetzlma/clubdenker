import { useState, useEffect, useCallback } from "react"
import { Plus, Pencil, Trash2 } from "lucide-react"
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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import api from "@/lib/api"
import type { Abteilung } from "@/types/setup"
import { GruppeDialog } from "./gruppe-dialog"

export interface Trainingsgruppe {
  id: number
  name: string
  beschreibung: string | null
  abteilung_id: number
  abteilung_name?: string
  trainer_name: string
  wochentag: string
  uhrzeit: string
  max_teilnehmer: number
  aktiv: boolean
}

const WOCHENTAG_LABELS: Record<string, string> = {
  montag: "Montag",
  dienstag: "Dienstag",
  mittwoch: "Mittwoch",
  donnerstag: "Donnerstag",
  freitag: "Freitag",
  samstag: "Samstag",
  sonntag: "Sonntag",
}

export function TrainingsgruppenTable() {
  const [gruppen, setGruppen] = useState<Trainingsgruppe[]>([])
  const [abteilungen, setAbteilungen] = useState<Abteilung[]>([])
  const [loading, setLoading] = useState(true)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<Trainingsgruppe | null>(null)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [deleting, setDeleting] = useState<Trainingsgruppe | null>(null)

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const [gData, aData] = await Promise.all([
        api.get<Trainingsgruppe[]>("/api/training/gruppen"),
        api.get<Abteilung[]>("/api/setup/abteilungen"),
      ])
      setGruppen(gData)
      setAbteilungen(aData)
    } catch {
      setGruppen([])
      setAbteilungen([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  function openCreate() {
    setEditing(null)
    setDialogOpen(true)
  }

  function openEdit(gruppe: Trainingsgruppe) {
    setEditing(gruppe)
    setDialogOpen(true)
  }

  function openDelete(gruppe: Trainingsgruppe) {
    setDeleting(gruppe)
    setDeleteDialogOpen(true)
  }

  async function handleDelete() {
    if (!deleting) return
    try {
      await api.delete(`/api/training/gruppen/${deleting.id}`)
    } catch {
      setGruppen((prev) => prev.filter((g) => g.id !== deleting.id))
    }
    setDeleteDialogOpen(false)
    setDeleting(null)
    fetchData()
  }

  function getAbteilungName(abteilungId: number): string {
    return abteilungen.find((a) => a.id === abteilungId)?.name ?? "—"
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
        <div className="space-y-1">
          <CardTitle>Trainingsgruppen</CardTitle>
          <CardDescription>Verwalten Sie die Trainingsgruppen des Vereins.</CardDescription>
        </div>
        <Button onClick={openCreate} size="sm">
          <Plus className="mr-2 h-4 w-4" />
          Neue Gruppe
        </Button>
      </CardHeader>
      <CardContent>
        {loading ? (
          <p className="text-sm text-muted-foreground">Laden...</p>
        ) : gruppen.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Keine Trainingsgruppen vorhanden. Erstellen Sie die erste Gruppe.
          </p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Abteilung</TableHead>
                <TableHead>Trainer</TableHead>
                <TableHead>Wochentag</TableHead>
                <TableHead>Uhrzeit</TableHead>
                <TableHead className="text-right">Max. Teilnehmer</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Aktionen</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {gruppen.map((gruppe) => (
                <TableRow key={gruppe.id}>
                  <TableCell className="font-medium">{gruppe.name}</TableCell>
                  <TableCell>{gruppe.abteilung_name ?? getAbteilungName(gruppe.abteilung_id)}</TableCell>
                  <TableCell>{gruppe.trainer_name}</TableCell>
                  <TableCell>{WOCHENTAG_LABELS[gruppe.wochentag] ?? gruppe.wochentag}</TableCell>
                  <TableCell>{gruppe.uhrzeit}</TableCell>
                  <TableCell className="text-right">{gruppe.max_teilnehmer}</TableCell>
                  <TableCell>
                    <Badge variant={gruppe.aktiv ? "default" : "secondary"}>
                      {gruppe.aktiv ? "Aktiv" : "Inaktiv"}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => openEdit(gruppe)}
                        aria-label={`${gruppe.name} bearbeiten`}
                      >
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => openDelete(gruppe)}
                        aria-label={`${gruppe.name} löschen`}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>

      {/* Create/Edit Dialog */}
      <GruppeDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        gruppe={editing}
        abteilungen={abteilungen}
        onSaved={fetchData}
      />

      {/* Delete Confirmation */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Trainingsgruppe löschen</DialogTitle>
            <DialogDescription>
              Möchten Sie die Trainingsgruppe &quot;{deleting?.name}&quot; wirklich löschen? Diese
              Aktion kann nicht rückgängig gemacht werden.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
              Abbrechen
            </Button>
            <Button variant="destructive" onClick={handleDelete}>
              Löschen
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  )
}
