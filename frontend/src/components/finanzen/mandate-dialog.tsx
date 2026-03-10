import { useState, useEffect, useCallback } from "react"
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
import type { SepaMandat, SepaMandatCreatePayload } from "@/types/finance"

const API_BASE = "/api"

interface MitgliedOption {
  id: number
  vorname: string
  nachname: string
  mitgliedsnummer: string
}

interface MandateDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess?: () => void
  editMandat?: SepaMandat | null
}

function generateMandatsreferenz(): string {
  const now = new Date()
  const year = now.getFullYear()
  const rand = Math.random().toString(36).substring(2, 8).toUpperCase()
  return `MANDAT-${year}-${rand}`
}

function todayStr(): string {
  return new Date().toISOString().split("T")[0]
}

const emptyForm: SepaMandatCreatePayload = {
  mitglied_id: 0,
  iban: "",
  bic: "",
  kontoinhaber: "",
  mandatsreferenz: "",
  unterschriftsdatum: "",
  gueltig_ab: "",
  gueltig_bis: "",
}

export function MandateDialog({ open, onOpenChange, onSuccess, editMandat }: MandateDialogProps) {
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [mitglieder, setMitglieder] = useState<MitgliedOption[]>([])
  const [form, setForm] = useState<SepaMandatCreatePayload>({ ...emptyForm })

  const isEdit = !!editMandat

  const fetchMitglieder = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/mitglieder?page_size=500`)
      if (!res.ok) return
      const data = await res.json()
      const items = data.items ?? data
      setMitglieder(
        items.map((m: MitgliedOption) => ({
          id: m.id,
          vorname: m.vorname,
          nachname: m.nachname,
          mitgliedsnummer: m.mitgliedsnummer,
        }))
      )
    } catch {
      // ignore
    }
  }, [])

  useEffect(() => {
    if (open) {
      fetchMitglieder()
      if (editMandat) {
        setForm({
          mitglied_id: editMandat.mitglied_id,
          iban: editMandat.iban,
          bic: editMandat.bic ?? "",
          kontoinhaber: editMandat.kontoinhaber,
          mandatsreferenz: editMandat.mandatsreferenz,
          unterschriftsdatum: editMandat.unterschriftsdatum,
          gueltig_ab: editMandat.gueltig_ab,
          gueltig_bis: editMandat.gueltig_bis ?? "",
        })
      } else {
        setForm({
          ...emptyForm,
          mandatsreferenz: generateMandatsreferenz(),
          unterschriftsdatum: todayStr(),
          gueltig_ab: todayStr(),
        })
      }
      setError(null)
    }
  }, [open, editMandat, fetchMitglieder])

  function resetForm() {
    setForm({ ...emptyForm })
    setError(null)
  }

  async function handleSubmit() {
    if (!form.mitglied_id || !form.iban || !form.kontoinhaber || !form.mandatsreferenz || !form.unterschriftsdatum || !form.gueltig_ab) {
      setError("Bitte alle Pflichtfelder ausfuellen.")
      return
    }

    setSubmitting(true)
    setError(null)

    const payload: Record<string, unknown> = { ...form }
    if (!payload.bic) delete payload.bic
    if (!payload.gueltig_bis) delete payload.gueltig_bis

    try {
      const url = isEdit
        ? `${API_BASE}/finanzen/mandate/${editMandat!.id}`
        : `${API_BASE}/finanzen/mandate`
      const method = isEdit ? "PUT" : "POST"

      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })
      if (!res.ok) {
        const detail = await res.json().catch(() => null)
        throw new Error(detail?.detail ?? "Fehler beim Speichern.")
      }
      resetForm()
      onOpenChange(false)
      onSuccess?.()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Fehler beim Speichern. Bitte erneut versuchen.")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(v) => { onOpenChange(v); if (!v) resetForm() }}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{isEdit ? "SEPA-Mandat bearbeiten" : "Neues SEPA-Mandat"}</DialogTitle>
          <DialogDescription>
            {isEdit
              ? "Bearbeiten Sie die Mandatsdaten."
              : "Erstellen Sie ein neues SEPA-Lastschriftmandat."}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Mitglied selector */}
          <div className="space-y-2">
            <Label htmlFor="mandat_mitglied">Mitglied *</Label>
            <Select
              value={form.mitglied_id ? String(form.mitglied_id) : ""}
              onValueChange={(v) => {
                const mid = parseInt(v)
                const member = mitglieder.find((m) => m.id === mid)
                setForm({
                  ...form,
                  mitglied_id: mid,
                  kontoinhaber: form.kontoinhaber || (member ? `${member.vorname} ${member.nachname}` : ""),
                })
              }}
              disabled={isEdit}
            >
              <SelectTrigger id="mandat_mitglied">
                <SelectValue placeholder="Mitglied auswaehlen..." />
              </SelectTrigger>
              <SelectContent>
                {mitglieder.map((m) => (
                  <SelectItem key={m.id} value={String(m.id)}>
                    {m.nachname}, {m.vorname} ({m.mitgliedsnummer})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* IBAN */}
          <div className="space-y-2">
            <Label htmlFor="mandat_iban">IBAN *</Label>
            <Input
              id="mandat_iban"
              placeholder="DE89 3704 0044 0532 0130 00"
              value={form.iban}
              onChange={(e) => setForm({ ...form, iban: e.target.value.replace(/\s/g, "").toUpperCase() })}
            />
          </div>

          {/* BIC */}
          <div className="space-y-2">
            <Label htmlFor="mandat_bic">BIC</Label>
            <Input
              id="mandat_bic"
              placeholder="COBADEFFXXX"
              value={form.bic ?? ""}
              onChange={(e) => setForm({ ...form, bic: e.target.value.toUpperCase() })}
            />
          </div>

          {/* Kontoinhaber */}
          <div className="space-y-2">
            <Label htmlFor="mandat_kontoinhaber">Kontoinhaber *</Label>
            <Input
              id="mandat_kontoinhaber"
              placeholder="Max Mustermann"
              value={form.kontoinhaber}
              onChange={(e) => setForm({ ...form, kontoinhaber: e.target.value })}
            />
          </div>

          {/* Mandatsreferenz */}
          <div className="space-y-2">
            <Label htmlFor="mandat_referenz">Mandatsreferenz *</Label>
            <Input
              id="mandat_referenz"
              value={form.mandatsreferenz}
              onChange={(e) => setForm({ ...form, mandatsreferenz: e.target.value })}
            />
          </div>

          {/* Unterschriftsdatum */}
          <div className="space-y-2">
            <Label htmlFor="mandat_unterschrift">Unterschriftsdatum *</Label>
            <Input
              id="mandat_unterschrift"
              type="date"
              value={form.unterschriftsdatum}
              onChange={(e) => setForm({ ...form, unterschriftsdatum: e.target.value })}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            {/* Gueltig ab */}
            <div className="space-y-2">
              <Label htmlFor="mandat_gueltig_ab">Gueltig ab *</Label>
              <Input
                id="mandat_gueltig_ab"
                type="date"
                value={form.gueltig_ab}
                onChange={(e) => setForm({ ...form, gueltig_ab: e.target.value })}
              />
            </div>

            {/* Gueltig bis */}
            <div className="space-y-2">
              <Label htmlFor="mandat_gueltig_bis">Gueltig bis</Label>
              <Input
                id="mandat_gueltig_bis"
                type="date"
                value={form.gueltig_bis ?? ""}
                onChange={(e) => setForm({ ...form, gueltig_bis: e.target.value })}
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
            {submitting ? "Wird gespeichert..." : isEdit ? "Speichern" : "Mandat erstellen"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
