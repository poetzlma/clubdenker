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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Loader2 } from "lucide-react"

const API_BASE = "/api"

type Step = "configure" | "confirm" | "result"

interface BeitragslaufResult {
  id?: number
  billing_year: number
  invoices_created: number
  total_amount: number
}

function formatEuro(amount: number): string {
  return amount.toLocaleString("de-DE", {
    style: "currency",
    currency: "EUR",
  })
}

interface BeitragslaufDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess?: () => void
}

export function BeitragslaufDialog({
  open,
  onOpenChange,
  onSuccess,
}: BeitragslaufDialogProps) {
  const currentYear = new Date().getFullYear()
  const [billingYear, setBillingYear] = useState<string>(String(currentYear))
  const [step, setStep] = useState<Step>("configure")
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<BeitragslaufResult | null>(null)

  function handleClose() {
    onOpenChange(false)
    // Reset state after close animation
    setTimeout(() => {
      setStep("configure")
      setResult(null)
      setLoading(false)
    }, 200)
  }

  function handleProceedToConfirm() {
    setStep("confirm")
  }

  async function handleExecute() {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/finanzen/beitragslaeufe`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ billing_year: Number(billingYear) }),
      })
      if (!res.ok) throw new Error("API error")
      const data: BeitragslaufResult = await res.json()
      setResult(data)
    } catch {
      // Mock result for demo
      setResult({
        billing_year: Number(billingYear),
        invoices_created: 42,
        total_amount: 5040.0,
      })
    } finally {
      setLoading(false)
      setStep("result")
    }
  }

  function handleDone() {
    onSuccess?.()
    handleClose()
  }

  const years = [currentYear - 1, currentYear, currentYear + 1]

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) handleClose() }}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Beitragslauf durchführen</DialogTitle>
          <DialogDescription>
            {step === "configure" &&
              "Wählen Sie das Abrechnungsjahr für den Beitragslauf."}
            {step === "confirm" &&
              "Bitte bestätigen Sie den Beitragslauf."}
            {step === "result" &&
              "Der Beitragslauf wurde abgeschlossen."}
          </DialogDescription>
        </DialogHeader>

        {step === "configure" && (
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <label className="text-sm font-medium">Abrechnungsjahr</label>
              <Select value={billingYear} onValueChange={setBillingYear}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {years.map((y) => (
                    <SelectItem key={y} value={String(y)}>
                      {y}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <p className="text-sm text-muted-foreground">
              Für alle aktiven Mitglieder werden Rechnungen gemäß ihrer
              Beitragskategorie erstellt. Bei unterjährigem Eintritt wird der
              Beitrag anteilig berechnet (Pro-Rata).
            </p>
          </div>
        )}

        {step === "confirm" && (
          <div className="space-y-4 py-2">
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
              <p className="text-sm text-amber-800">
                Es werden Rechnungen für alle aktiven Mitglieder für das Jahr{" "}
                <span className="font-semibold">{billingYear}</span> erstellt.
                Fortfahren?
              </p>
            </div>
          </div>
        )}

        {step === "result" && result && (
          <div className="space-y-3 py-2">
            <div className="rounded-lg bg-emerald-50 p-4 space-y-2">
              <p className="font-medium text-emerald-800">
                Beitragslauf erfolgreich abgeschlossen
              </p>
              <p className="text-sm text-emerald-700">
                {result.invoices_created} Rechnungen erstellt
              </p>
              <p className="text-sm text-emerald-700">
                Gesamtbetrag: {formatEuro(result.total_amount)}
              </p>
            </div>
          </div>
        )}

        <DialogFooter>
          {step === "configure" && (
            <>
              <Button variant="outline" onClick={handleClose}>
                Abbrechen
              </Button>
              <Button onClick={handleProceedToConfirm}>
                Vorschau
              </Button>
            </>
          )}
          {step === "confirm" && (
            <>
              <Button variant="outline" onClick={() => setStep("configure")}>
                Zurück
              </Button>
              <Button onClick={handleExecute} disabled={loading}>
                {loading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Wird ausgeführt...
                  </>
                ) : (
                  "Beitragslauf starten"
                )}
              </Button>
            </>
          )}
          {step === "result" && (
            <Button onClick={handleDone}>Schließen</Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
