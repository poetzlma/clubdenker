import { useState, useEffect } from "react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import api from "@/lib/api"
import type { Protokoll, ProtokollTyp } from "@/types/dokumente"
import { PROTOKOLL_TYP_LABELS } from "@/types/dokumente"

interface ProtokollDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  protokoll: Protokoll | null
  onSaved: () => void
}

interface FormData {
  titel: string
  datum: string
  inhalt: string
  typ: ProtokollTyp
  erstellt_von: string
  teilnehmer: string
  beschluesse: string
}

function defaultForm(): FormData {
  return {
    titel: "",
    datum: new Date().toISOString().slice(0, 10),
    inhalt: "",
    typ: "sonstige",
    erstellt_von: "",
    teilnehmer: "",
    beschluesse: "",
  }
}

export function ProtokollDialog({
  open,
  onOpenChange,
  protokoll,
  onSaved,
}: ProtokollDialogProps) {
  const [form, setForm] = useState<FormData>(defaultForm())
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (open) {
      if (protokoll) {
        setForm({
          titel: protokoll.titel,
          datum: protokoll.datum,
          inhalt: protokoll.inhalt,
          typ: protokoll.typ as ProtokollTyp,
          erstellt_von: protokoll.erstellt_von ?? "",
          teilnehmer: protokoll.teilnehmer ?? "",
          beschluesse: protokoll.beschluesse ?? "",
        })
      } else {
        setForm(defaultForm())
      }
    }
  }, [open, protokoll])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    try {
      const payload = {
        ...form,
        erstellt_von: form.erstellt_von || null,
        teilnehmer: form.teilnehmer || null,
        beschluesse: form.beschluesse || null,
      }
      if (protokoll) {
        await api.put(`/api/dokumente/protokolle/${protokoll.id}`, payload)
      } else {
        await api.post("/api/dokumente/protokolle", payload)
      }
      onOpenChange(false)
      onSaved()
    } catch {
      // Error handling could be improved
    } finally {
      setSaving(false)
    }
  }

  const isEditing = !!protokoll

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {isEditing ? "Protokoll bearbeiten" : "Neues Protokoll"}
          </DialogTitle>
          <DialogDescription>
            {isEditing
              ? "Bearbeiten Sie das Sitzungsprotokoll."
              : "Erstellen Sie ein neues Sitzungsprotokoll."}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="titel">Titel</Label>
              <Input
                id="titel"
                value={form.titel}
                onChange={(e) => setForm({ ...form, titel: e.target.value })}
                placeholder="z.B. Vorstandssitzung Q1 2026"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="datum">Datum</Label>
              <Input
                id="datum"
                type="date"
                value={form.datum}
                onChange={(e) => setForm({ ...form, datum: e.target.value })}
                required
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="typ">Typ</Label>
              <Select
                value={form.typ}
                onValueChange={(v) => setForm({ ...form, typ: v as ProtokollTyp })}
              >
                <SelectTrigger id="typ">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {(
                    Object.entries(PROTOKOLL_TYP_LABELS) as [ProtokollTyp, string][]
                  ).map(([value, label]) => (
                    <SelectItem key={value} value={value}>
                      {label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="erstellt_von">Erstellt von</Label>
              <Input
                id="erstellt_von"
                value={form.erstellt_von}
                onChange={(e) =>
                  setForm({ ...form, erstellt_von: e.target.value })
                }
                placeholder="Name des Protokollanten"
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="teilnehmer">Teilnehmer</Label>
            <Input
              id="teilnehmer"
              value={form.teilnehmer}
              onChange={(e) =>
                setForm({ ...form, teilnehmer: e.target.value })
              }
              placeholder="z.B. Max Mustermann, Erika Musterfrau"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="inhalt">Inhalt / Tagesordnung</Label>
            <Textarea
              id="inhalt"
              value={form.inhalt}
              onChange={(e) => setForm({ ...form, inhalt: e.target.value })}
              placeholder="Tagesordnungspunkte und Diskussionen..."
              rows={8}
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="beschluesse">Beschluesse</Label>
            <Textarea
              id="beschluesse"
              value={form.beschluesse}
              onChange={(e) =>
                setForm({ ...form, beschluesse: e.target.value })
              }
              placeholder="Gefasste Beschluesse..."
              rows={4}
            />
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Abbrechen
            </Button>
            <Button type="submit" disabled={saving}>
              {saving ? "Speichern..." : isEditing ? "Aktualisieren" : "Anlegen"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
