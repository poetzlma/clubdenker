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
import type { Rechnung } from "@/types/finance"

const API_BASE = "/api"

interface VersandDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  invoice: Rechnung | null
  onSuccess?: () => void
}

const VERSAND_KANAELE = [
  { value: "email_pdf", label: "E-Mail (PDF)" },
  { value: "email_zugferd", label: "E-Mail (ZUGFeRD)" },
  { value: "post", label: "Post" },
  { value: "portal", label: "Portal" },
] as const

export function VersandDialog({ open, onOpenChange, invoice, onSuccess }: VersandDialogProps) {
  const [kanal, setKanal] = useState("email_pdf")
  const [empfaenger, setEmpfaenger] = useState("")
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function resetForm() {
    setKanal("email")
    setEmpfaenger("")
    setError(null)
  }

  async function handleSubmit() {
    if (!invoice) return
    if (!empfaenger.trim()) {
      setError("Bitte einen Empfaenger angeben.")
      return
    }

    setSubmitting(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE}/finanzen/rechnungen/${invoice.id}/versenden`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ kanal, empfaenger: empfaenger.trim() }),
      })
      if (!res.ok) {
        const detail = await res.json().catch(() => null)
        throw new Error(detail?.detail ?? "Versand fehlgeschlagen.")
      }
      resetForm()
      onOpenChange(false)
      onSuccess?.()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Fehler beim Versenden.")
    } finally {
      setSubmitting(false)
    }
  }

  function getEmpfaengerPlaceholder(): string {
    if (kanal === "email") return "empfaenger@beispiel.de"
    if (kanal === "post") return "Adresse des Empfaengers"
    return "Portal-Kennung"
  }

  function getEmpfaengerLabel(): string {
    if (kanal === "email") return "E-Mail-Adresse"
    if (kanal === "post") return "Postanschrift"
    return "Portal-Kennung"
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => {
        onOpenChange(v)
        if (!v) resetForm()
      }}
    >
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Rechnung versenden</DialogTitle>
          <DialogDescription>
            {invoice
              ? `${invoice.rechnungsnummer} an ${invoice.empfaenger_name ?? invoice.mitglied_name ?? "---"} versenden.`
              : "Versandkanal und Empfaenger waehlen."}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="space-y-2">
            <Label htmlFor="versand-kanal">Versandkanal</Label>
            <Select value={kanal} onValueChange={setKanal}>
              <SelectTrigger id="versand-kanal">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {VERSAND_KANAELE.map((k) => (
                  <SelectItem key={k.value} value={k.value}>
                    {k.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="versand-empfaenger">{getEmpfaengerLabel()}</Label>
            <Input
              id="versand-empfaenger"
              value={empfaenger}
              onChange={(e) => setEmpfaenger(e.target.value)}
              placeholder={getEmpfaengerPlaceholder()}
            />
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => {
              onOpenChange(false)
              resetForm()
            }}
          >
            Abbrechen
          </Button>
          <Button onClick={handleSubmit} disabled={submitting}>
            {submitting ? "Wird versendet..." : "Versenden"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
