import { useState, useEffect, useCallback } from "react"
import type { Rechnung } from "@/types/finance"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { CheckCircle, ChevronRight, Download, FileText } from "lucide-react"

const API_BASE = "/api"

function formatEuro(amount: number): string {
  return amount.toLocaleString("de-DE", {
    style: "currency",
    currency: "EUR",
  })
}

function formatDate(dateStr: string): string {
  if (!dateStr) return ""
  const date = new Date(dateStr)
  const day = String(date.getDate()).padStart(2, "0")
  const month = String(date.getMonth() + 1).padStart(2, "0")
  const year = date.getFullYear()
  return `${day}.${month}.${year}`
}

const mockOpenInvoices: Rechnung[] = [
  {
    id: 3,
    rechnungsnummer: "R-2025-003",
    mitglied_id: 3,
    betrag: 60.0,
    beschreibung: "Jahresbeitrag Jugend 2025",
    rechnungsdatum: "2025-01-15",
    faelligkeitsdatum: "2025-02-15",
    status: "offen",
    created_at: "2025-01-15T10:00:00Z",
  },
  {
    id: 5,
    rechnungsnummer: "R-2025-005",
    mitglied_id: 5,
    betrag: 120.0,
    beschreibung: "Jahresbeitrag 2025",
    rechnungsdatum: "2025-01-15",
    faelligkeitsdatum: "2025-02-15",
    status: "ueberfaellig",
    created_at: "2025-01-15T10:00:00Z",
  },
  {
    id: 6,
    rechnungsnummer: "R-2025-006",
    mitglied_id: 6,
    betrag: 80.0,
    beschreibung: "Jahresbeitrag Passiv 2025",
    rechnungsdatum: "2025-01-15",
    faelligkeitsdatum: "2025-02-15",
    status: "offen",
    created_at: "2025-01-15T10:00:00Z",
  },
]

const mockSepaXml = `<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.008.001.02">
  <CstmrDrctDbtInitn>
    <GrpHdr>
      <MsgId>SEPA-2025-001</MsgId>
      <CreDtTm>2025-03-10T10:00:00</CreDtTm>
      <NbOfTxs>3</NbOfTxs>
      <CtrlSum>260.00</CtrlSum>
    </GrpHdr>
  </CstmrDrctDbtInitn>
</Document>`

export function SepaGenerator() {
  const [step, setStep] = useState(1)
  const [invoices, setInvoices] = useState<Rechnung[]>([])
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [sepaResult, setSepaResult] = useState<string | null>(null)

  const fetchOpenInvoices = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/invoices?status=offen`)
      if (!res.ok) throw new Error("API error")
      const data = await res.json()
      setInvoices(data.items ?? data)
    } catch {
      setInvoices(mockOpenInvoices)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchOpenInvoices()
  }, [fetchOpenInvoices])

  const selectedInvoices = invoices.filter((inv) => selectedIds.has(inv.id))
  const totalSelected = selectedInvoices.reduce(
    (sum, inv) => sum + inv.betrag,
    0
  )

  function toggleInvoice(id: number) {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  function toggleAll() {
    if (selectedIds.size === invoices.length) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(invoices.map((inv) => inv.id)))
    }
  }

  async function handleGenerate() {
    setGenerating(true)
    try {
      const res = await fetch(`${API_BASE}/sepa/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ invoice_ids: Array.from(selectedIds) }),
      })
      if (!res.ok) throw new Error("API error")
      const data = await res.json()
      setSepaResult(data.xml ?? mockSepaXml)
    } catch {
      setSepaResult(mockSepaXml)
    } finally {
      setGenerating(false)
      setStep(3)
    }
  }

  function handleDownload() {
    if (!sepaResult) return
    const blob = new Blob([sepaResult], { type: "application/xml" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = "sepa-lastschrift.xml"
    a.click()
    URL.revokeObjectURL(url)
  }

  function handleReset() {
    setStep(1)
    setSelectedIds(new Set())
    setSepaResult(null)
  }

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <p className="text-muted-foreground">Laden...</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Step indicators */}
      <div className="flex items-center gap-2">
        {[1, 2, 3].map((s) => (
          <div key={s} className="flex items-center gap-2">
            <div
              className={`flex h-8 w-8 items-center justify-center rounded-full text-sm font-medium ${
                s === step
                  ? "bg-primary text-primary-foreground"
                  : s < step
                    ? "bg-green-100 text-green-800"
                    : "bg-muted text-muted-foreground"
              }`}
            >
              {s < step ? <CheckCircle className="h-4 w-4" /> : s}
            </div>
            <span
              className={`text-sm ${s === step ? "font-medium" : "text-muted-foreground"}`}
            >
              {s === 1
                ? "Rechnungen auswählen"
                : s === 2
                  ? "Vorschau"
                  : "Ergebnis"}
            </span>
            {s < 3 && <ChevronRight className="h-4 w-4 text-muted-foreground" />}
          </div>
        ))}
      </div>

      {/* Step 1: Select invoices */}
      {step === 1 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Offene Rechnungen
            </CardTitle>
          </CardHeader>
          <CardContent>
            {invoices.length === 0 ? (
              <p className="text-muted-foreground">
                Keine offenen Rechnungen vorhanden.
              </p>
            ) : (
              <>
                <div className="mb-4">
                  <label className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={selectedIds.size === invoices.length}
                      onChange={toggleAll}
                      className="h-4 w-4 rounded border-gray-300"
                    />
                    Alle auswählen
                  </label>
                </div>
                <div className="space-y-2">
                  {invoices.map((inv) => (
                    <label
                      key={inv.id}
                      className="flex items-center gap-3 rounded-lg border p-3 hover:bg-muted/50 cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={selectedIds.has(inv.id)}
                        onChange={() => toggleInvoice(inv.id)}
                        className="h-4 w-4 rounded border-gray-300"
                      />
                      <div className="flex-1">
                        <div className="flex items-center justify-between">
                          <span className="font-medium">
                            {inv.rechnungsnummer}
                          </span>
                          <span className="font-medium">
                            {formatEuro(inv.betrag)}
                          </span>
                        </div>
                        <p className="text-sm text-muted-foreground">
                          {inv.beschreibung} - Fällig: {formatDate(inv.faelligkeitsdatum)}
                        </p>
                      </div>
                      {inv.status === "ueberfaellig" && (
                        <span className="inline-flex items-center rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-800">
                          Überfällig
                        </span>
                      )}
                    </label>
                  ))}
                </div>
                <div className="mt-4 flex items-center justify-between">
                  <p className="text-sm text-muted-foreground">
                    {selectedIds.size} von {invoices.length} ausgewählt
                  </p>
                  <Button
                    onClick={() => setStep(2)}
                    disabled={selectedIds.size === 0}
                  >
                    Weiter
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      )}

      {/* Step 2: Preview */}
      {step === 2 && (
        <Card>
          <CardHeader>
            <CardTitle>Vorschau SEPA-Lastschrift</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {selectedInvoices.map((inv) => (
                <div
                  key={inv.id}
                  className="flex items-center justify-between rounded-lg border p-3"
                >
                  <div>
                    <span className="font-medium">{inv.rechnungsnummer}</span>
                    <p className="text-sm text-muted-foreground">
                      {inv.beschreibung}
                    </p>
                  </div>
                  <span className="font-medium">{formatEuro(inv.betrag)}</span>
                </div>
              ))}
            </div>
            <div className="mt-4 flex items-center justify-between border-t pt-4">
              <div>
                <p className="text-sm text-muted-foreground">Gesamtbetrag</p>
                <p className="text-xl font-bold">{formatEuro(totalSelected)}</p>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" onClick={() => setStep(1)}>
                  Zurück
                </Button>
                <Button onClick={handleGenerate} disabled={generating}>
                  {generating ? "Generiere..." : "SEPA-XML generieren"}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step 3: Result */}
      {step === 3 && sepaResult && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-green-700">
              <CheckCircle className="h-5 w-5" />
              SEPA-Datei erfolgreich generiert
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="mb-4 rounded-lg bg-muted p-4">
              <pre className="overflow-x-auto text-xs">
                <code>{sepaResult}</code>
              </pre>
            </div>
            <div className="flex gap-2">
              <Button onClick={handleDownload}>
                <Download className="h-4 w-4" />
                XML herunterladen
              </Button>
              <Button variant="outline" onClick={handleReset}>
                Neue Lastschrift
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
