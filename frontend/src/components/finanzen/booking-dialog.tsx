import { useState } from "react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import type { BuchungCreatePayload } from "@/types/finance"

const API_BASE = "/api"

interface BookingDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess?: () => void
}

export function BookingDialog({ open, onOpenChange, onSuccess }: BookingDialogProps) {
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [form, setForm] = useState<BuchungCreatePayload>({
    beschreibung: "",
    betrag: 0,
    konto: "",
    gegenkonto: "",
    sphare: "ideell",
    kostenstelle: "",
  })

  function resetForm() {
    setForm({
      beschreibung: "",
      betrag: 0,
      konto: "",
      gegenkonto: "",
      sphare: "ideell",
      kostenstelle: "",
    })
    setError(null)
  }

  async function handleSubmit() {
    if (!form.beschreibung || !form.konto || !form.gegenkonto || form.betrag === 0) {
      setError("Bitte alle Pflichtfelder ausfüllen.")
      return
    }

    setSubmitting(true)
    setError(null)
    try {
      const payload: BuchungCreatePayload = {
        ...form,
        kostenstelle: form.kostenstelle || undefined,
      }
      const res = await fetch(`${API_BASE}/finanzen/buchungen`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })
      if (!res.ok) throw new Error("Buchung konnte nicht erstellt werden.")
      resetForm()
      onOpenChange(false)
      onSuccess?.()
    } catch {
      setError("Fehler beim Erstellen der Buchung. Bitte erneut versuchen.")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(v) => { onOpenChange(v); if (!v) resetForm() }}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Neue Buchung anlegen</DialogTitle>
          <DialogDescription>
            Erstellen Sie eine neue Buchung im Journal.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="beschreibung">Beschreibung *</Label>
            <Input
              id="beschreibung"
              placeholder="z.B. Mitgliedsbeitrag Schmidt"
              value={form.beschreibung}
              onChange={(e) => setForm({ ...form, beschreibung: e.target.value })}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="betrag">Betrag (EUR) *</Label>
            <Input
              id="betrag"
              type="number"
              step="0.01"
              placeholder="120.00"
              value={form.betrag || ""}
              onChange={(e) => setForm({ ...form, betrag: parseFloat(e.target.value) || 0 })}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="konto">Konto *</Label>
              <Input
                id="konto"
                placeholder="z.B. 1200"
                value={form.konto}
                onChange={(e) => setForm({ ...form, konto: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="gegenkonto">Gegenkonto *</Label>
              <Input
                id="gegenkonto"
                placeholder="z.B. 8100"
                value={form.gegenkonto}
                onChange={(e) => setForm({ ...form, gegenkonto: e.target.value })}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Sphäre *</Label>
              <Select
                value={form.sphare}
                onValueChange={(v) =>
                  setForm({ ...form, sphare: v as BuchungCreatePayload["sphare"] })
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ideell">Ideell</SelectItem>
                  <SelectItem value="zweckbetrieb">Zweckbetrieb</SelectItem>
                  <SelectItem value="vermoegensverwaltung">Vermögensverwaltung</SelectItem>
                  <SelectItem value="wirtschaftlich">Wirtschaftlich</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="kostenstelle">Kostenstelle</Label>
              <Input
                id="kostenstelle"
                placeholder="z.B. Fussball"
                value={form.kostenstelle ?? ""}
                onChange={(e) => setForm({ ...form, kostenstelle: e.target.value })}
              />
            </div>
          </div>

          {error && (
            <p className="text-sm text-red-600">{error}</p>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => { onOpenChange(false); resetForm() }}>
            Abbrechen
          </Button>
          <Button onClick={handleSubmit} disabled={submitting}>
            {submitting ? "Wird erstellt..." : "Buchung anlegen"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
