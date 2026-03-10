import { useState, useEffect, useCallback } from "react"
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
import type { Abteilung } from "@/types/setup"
import type { Trainingsgruppe } from "./trainingsgruppen-table"

interface GruppeDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  gruppe: Trainingsgruppe | null
  abteilungen: Abteilung[]
  onSaved: () => void
}

const WOCHENTAGE = [
  { value: "montag", label: "Montag" },
  { value: "dienstag", label: "Dienstag" },
  { value: "mittwoch", label: "Mittwoch" },
  { value: "donnerstag", label: "Donnerstag" },
  { value: "freitag", label: "Freitag" },
  { value: "samstag", label: "Samstag" },
  { value: "sonntag", label: "Sonntag" },
]

export function GruppeDialog({
  open,
  onOpenChange,
  gruppe,
  abteilungen,
  onSaved,
}: GruppeDialogProps) {
  const [formName, setFormName] = useState("")
  const [formBeschreibung, setFormBeschreibung] = useState("")
  const [formAbteilungId, setFormAbteilungId] = useState("")
  const [formTrainerName, setFormTrainerName] = useState("")
  const [formWochentag, setFormWochentag] = useState("")
  const [formUhrzeit, setFormUhrzeit] = useState("")
  const [formMaxTeilnehmer, setFormMaxTeilnehmer] = useState("")
  const [formAktiv, setFormAktiv] = useState(true)
  const [saving, setSaving] = useState(false)

  const resetForm = useCallback(() => {
    if (gruppe) {
      setFormName(gruppe.name)
      setFormBeschreibung(gruppe.beschreibung ?? "")
      setFormAbteilungId(gruppe.abteilung_id.toString())
      setFormTrainerName(gruppe.trainer_name)
      setFormWochentag(gruppe.wochentag)
      setFormUhrzeit(gruppe.uhrzeit)
      setFormMaxTeilnehmer(gruppe.max_teilnehmer.toString())
      setFormAktiv(gruppe.aktiv)
    } else {
      setFormName("")
      setFormBeschreibung("")
      setFormAbteilungId("")
      setFormTrainerName("")
      setFormWochentag("")
      setFormUhrzeit("")
      setFormMaxTeilnehmer("")
      setFormAktiv(true)
    }
  }, [gruppe])

  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    if (open) resetForm()
  }, [open, resetForm])
  /* eslint-enable react-hooks/set-state-in-effect */

  async function handleSave() {
    const payload = {
      name: formName,
      beschreibung: formBeschreibung || undefined,
      abteilung_id: parseInt(formAbteilungId),
      trainer_name: formTrainerName,
      wochentag: formWochentag,
      uhrzeit: formUhrzeit,
      max_teilnehmer: parseInt(formMaxTeilnehmer) || 0,
      aktiv: formAktiv,
    }

    setSaving(true)
    try {
      if (gruppe) {
        await api.put(`/api/training/gruppen/${gruppe.id}`, payload)
      } else {
        await api.post("/api/training/gruppen", payload)
      }
    } catch {
      // API error - still close dialog
    }
    setSaving(false)
    onOpenChange(false)
    onSaved()
  }

  const isValid =
    formName.trim() &&
    formAbteilungId &&
    formTrainerName.trim() &&
    formWochentag &&
    formUhrzeit &&
    formMaxTeilnehmer

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>
            {gruppe ? "Trainingsgruppe bearbeiten" : "Neue Trainingsgruppe"}
          </DialogTitle>
          <DialogDescription>
            {gruppe
              ? "Bearbeiten Sie die Trainingsgruppe."
              : "Erstellen Sie eine neue Trainingsgruppe."}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-2">
          <div className="space-y-2">
            <Label htmlFor="gruppe-name">Name</Label>
            <Input
              id="gruppe-name"
              value={formName}
              onChange={(e) => setFormName(e.target.value)}
              placeholder="z.B. Jugend Fußball A"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="gruppe-beschreibung">Beschreibung</Label>
            <Textarea
              id="gruppe-beschreibung"
              value={formBeschreibung}
              onChange={(e) => setFormBeschreibung(e.target.value)}
              placeholder="Optionale Beschreibung"
              rows={3}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="gruppe-abteilung">Abteilung</Label>
            <Select value={formAbteilungId} onValueChange={setFormAbteilungId}>
              <SelectTrigger id="gruppe-abteilung">
                <SelectValue placeholder="Abteilung wählen" />
              </SelectTrigger>
              <SelectContent>
                {abteilungen.map((a) => (
                  <SelectItem key={a.id} value={a.id.toString()}>
                    {a.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="gruppe-trainer">Trainer</Label>
            <Input
              id="gruppe-trainer"
              value={formTrainerName}
              onChange={(e) => setFormTrainerName(e.target.value)}
              placeholder="Name des Trainers"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="gruppe-wochentag">Wochentag</Label>
              <Select value={formWochentag} onValueChange={setFormWochentag}>
                <SelectTrigger id="gruppe-wochentag">
                  <SelectValue placeholder="Wochentag wählen" />
                </SelectTrigger>
                <SelectContent>
                  {WOCHENTAGE.map((w) => (
                    <SelectItem key={w.value} value={w.value}>
                      {w.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="gruppe-uhrzeit">Uhrzeit</Label>
              <Input
                id="gruppe-uhrzeit"
                type="time"
                value={formUhrzeit}
                onChange={(e) => setFormUhrzeit(e.target.value)}
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="gruppe-max">Max. Teilnehmer</Label>
              <Input
                id="gruppe-max"
                type="number"
                min="1"
                value={formMaxTeilnehmer}
                onChange={(e) => setFormMaxTeilnehmer(e.target.value)}
                placeholder="z.B. 20"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="gruppe-aktiv">Status</Label>
              <Select
                value={formAktiv ? "aktiv" : "inaktiv"}
                onValueChange={(v) => setFormAktiv(v === "aktiv")}
              >
                <SelectTrigger id="gruppe-aktiv">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="aktiv">Aktiv</SelectItem>
                  <SelectItem value="inaktiv">Inaktiv</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Abbrechen
          </Button>
          <Button onClick={handleSave} disabled={!isValid || saving}>
            {saving ? "Speichern..." : "Speichern"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
