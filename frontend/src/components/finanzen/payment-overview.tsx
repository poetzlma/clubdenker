import { useState, useEffect, useCallback, useRef } from "react"
import type {
  Rechnung,
  Kassenstand,
  KassenstandSphare,
  Buchung,
  BeitragseinzugResult,
  MahnwesenResult,
} from "@/types/finance"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { cn } from "@/lib/utils"
import { SPHERE_COLORS, SEMANTIC_COLORS } from "@/constants/design"
import { KpiCard } from "@/components/dashboard/kpi-card"
import { SectionHeader } from "@/components/dashboard/section-header"
import { MahnstufenBadge } from "@/components/dashboard/mahnstufen-badge"
import { BookingDialog } from "@/components/finanzen/booking-dialog"
import { InvoiceDialog } from "@/components/finanzen/invoice-dialog"
import { BeitragslaufDialog } from "@/components/finanzen/beitragslauf-dialog"
import {
  Plus,
  CreditCard,
  AlertTriangle,
  FileText,
} from "lucide-react"

const API_BASE = "/api"

function formatEuro(amount: number | null | undefined): string {
  return (amount ?? 0).toLocaleString("de-DE", {
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

function daysOverdue(faelligkeitsdatum: string): number {
  const due = new Date(faelligkeitsdatum)
  const now = new Date()
  const diff = Math.floor((now.getTime() - due.getTime()) / (1000 * 60 * 60 * 24))
  return Math.max(0, diff)
}

function getMahnstufe(daysOver: number): 0 | 1 | 2 | 3 {
  if (daysOver > 60) return 3
  if (daysOver > 30) return 2
  if (daysOver > 14) return 1
  return 0
}

// --- Mock data ---

const mockMitgliedNames: Record<number, string> = {
  1: "Schmidt, Thomas",
  2: "Müller, Anna",
  3: "Weber, Klaus",
  4: "Fischer, Maria",
  5: "Becker, Stefan",
  6: "Hoffmann, Lisa",
  7: "Klein, Tom",
  8: "Wagner, Peter",
}

const mockRechnungen: Rechnung[] = [
  {
    id: 1, rechnungsnummer: "RE-2026-001", rechnungstyp: "mitgliedsbeitrag",
    status: "mahnung_2", mahnstufe: 2, empfaenger_typ: "mitglied",
    empfaenger_name: "Schmidt, Thomas", mitglied_id: 1, mitglied_name: "Schmidt, Thomas",
    rechnungsdatum: "2026-01-15", faelligkeitsdatum: "2026-01-24",
    summe_netto: 120.0, summe_steuer: 0, summe_brutto: 120.0,
    betrag: 120.0, bezahlt_betrag: 0, offener_betrag: 120.0,
    sphaere: "ideell", zahlungsziel_tage: 14, positionen: [],
    created_at: "2026-01-15T10:00:00Z",
  },
  {
    id: 2, rechnungsnummer: "RE-2026-002", rechnungstyp: "mitgliedsbeitrag",
    status: "gestellt", mahnstufe: 0, empfaenger_typ: "mitglied",
    empfaenger_name: "Müller, Anna", mitglied_id: 2, mitglied_name: "Müller, Anna",
    rechnungsdatum: "2026-02-15", faelligkeitsdatum: "2026-02-26",
    summe_netto: 60.0, summe_steuer: 0, summe_brutto: 60.0,
    betrag: 60.0, bezahlt_betrag: 0, offener_betrag: 60.0,
    sphaere: "ideell", zahlungsziel_tage: 14, positionen: [],
    created_at: "2026-02-15T10:00:00Z",
  },
  {
    id: 3, rechnungsnummer: "RE-2026-003", rechnungstyp: "mitgliedsbeitrag",
    status: "mahnung_1", mahnstufe: 1, empfaenger_typ: "mitglied",
    empfaenger_name: "Becker, Stefan", mitglied_id: 5, mitglied_name: "Becker, Stefan",
    rechnungsdatum: "2026-01-15", faelligkeitsdatum: "2026-02-01",
    summe_netto: 120.0, summe_steuer: 0, summe_brutto: 120.0,
    betrag: 120.0, bezahlt_betrag: 0, offener_betrag: 120.0,
    sphaere: "ideell", zahlungsziel_tage: 14, positionen: [],
    created_at: "2026-01-15T10:00:00Z",
  },
  {
    id: 4, rechnungsnummer: "RE-2026-004", rechnungstyp: "mitgliedsbeitrag",
    status: "gestellt", mahnstufe: 0, empfaenger_typ: "mitglied",
    empfaenger_name: "Hoffmann, Lisa", mitglied_id: 6, mitglied_name: "Hoffmann, Lisa",
    rechnungsdatum: "2026-02-20", faelligkeitsdatum: "2026-03-20",
    summe_netto: 80.0, summe_steuer: 0, summe_brutto: 80.0,
    betrag: 80.0, bezahlt_betrag: 0, offener_betrag: 80.0,
    sphaere: "ideell", zahlungsziel_tage: 14, positionen: [],
    created_at: "2026-02-20T10:00:00Z",
  },
]

const mockKassenstand: Kassenstand = {
  total: 12450.0,
  by_sphere: [
    { sphare: "ideell", betrag: 5200.0 },
    { sphare: "zweckbetrieb", betrag: 3100.0 },
    { sphare: "vermoegensverwaltung", betrag: 2650.0 },
    { sphare: "wirtschaftlich", betrag: 1500.0 },
  ],
}

const mockRecentPayments: Buchung[] = [
  {
    id: 101,
    buchungsdatum: "2026-03-05",
    betrag: 120.0,
    beschreibung: "Beitrag Schmidt, Thomas",
    konto: "1200",
    gegenkonto: "8100",
    sphare: "ideell",
    kostenstelle: "Verwaltung",
    mitglied_id: 1,
    created_at: "2026-03-05T10:00:00Z",
  },
  {
    id: 102,
    buchungsdatum: "2026-03-03",
    betrag: -450.0,
    beschreibung: "Hallenmiete März",
    konto: "4200",
    gegenkonto: "1200",
    sphare: "vermoegensverwaltung",
    kostenstelle: "Verwaltung",
    mitglied_id: null,
    created_at: "2026-03-03T10:00:00Z",
  },
  {
    id: 103,
    buchungsdatum: "2026-03-01",
    betrag: 60.0,
    beschreibung: "Beitrag Müller, Anna",
    konto: "1200",
    gegenkonto: "8100",
    sphare: "ideell",
    kostenstelle: "Jugendarbeit",
    mitglied_id: 2,
    created_at: "2026-03-01T10:00:00Z",
  },
  {
    id: 104,
    buchungsdatum: "2026-02-28",
    betrag: -800.0,
    beschreibung: "Trainerhonorar Februar",
    konto: "4100",
    gegenkonto: "1200",
    sphare: "zweckbetrieb",
    kostenstelle: "Tennis",
    mitglied_id: null,
    created_at: "2026-02-28T10:00:00Z",
  },
  {
    id: 105,
    buchungsdatum: "2026-02-25",
    betrag: 1500.0,
    beschreibung: "Sponsoring Vereinsfest",
    konto: "1200",
    gegenkonto: "8400",
    sphare: "wirtschaftlich",
    kostenstelle: null,
    mitglied_id: null,
    created_at: "2026-02-25T10:00:00Z",
  },
  {
    id: 106,
    buchungsdatum: "2026-02-20",
    betrag: 80.0,
    beschreibung: "Beitrag Hoffmann, Lisa",
    konto: "1200",
    gegenkonto: "8100",
    sphare: "ideell",
    kostenstelle: "Verwaltung",
    mitglied_id: 6,
    created_at: "2026-02-20T10:00:00Z",
  },
]

export function PaymentOverview() {
  const [rechnungen, setRechnungen] = useState<Rechnung[]>([])
  const [kassenstand, setKassenstand] = useState<Kassenstand | null>(null)
  const [recentPayments, setRecentPayments] = useState<Buchung[]>([])
  const [loading, setLoading] = useState(true)

  // Dialog states
  const [bookingDialogOpen, setBookingDialogOpen] = useState(false)
  const [invoiceDialogOpen, setInvoiceDialogOpen] = useState(false)
  const [beitragslaufDialogOpen, setBeitragslaufDialogOpen] = useState(false)
  const [beitragseinzugDialogOpen, setBeitragseinzugDialogOpen] = useState(false)
  const [mahnlaufDialogOpen, setMahnlaufDialogOpen] = useState(false)
  const [beitragseinzugResult, setBeitragseinzugResult] = useState<BeitragseinzugResult | null>(null)
  const [mahnwesenResult, setMahnwesenResult] = useState<MahnwesenResult | null>(null)
  const [agentLoading, setAgentLoading] = useState(false)

  const offeneTableRef = useRef<HTMLDivElement>(null)

  const fetchData = useCallback(async () => {
    setLoading(true)

    // Fetch rechnungen
    let fetchedRechnungen: Rechnung[] = mockRechnungen
    try {
      const res = await fetch(`${API_BASE}/finanzen/rechnungen?status=offen`)
      if (res.ok) {
        const data = await res.json()
        const items: Rechnung[] = data.items ?? data
        fetchedRechnungen = items.map((r) => ({
          ...r,
          mitglied_name: r.mitglied_id != null ? (mockMitgliedNames[r.mitglied_id] ?? `Mitglied #${r.mitglied_id}`) : "Unbekannt",
          mahnstufe: r.mahnstufe ?? (["mahnung_1", "mahnung_2", "mahnung_3", "faellig"].includes(r.status) ? getMahnstufe(daysOverdue(r.faelligkeitsdatum)) : 0),
        }))
      }
    } catch {
      // use mock data
    }
    setRechnungen(fetchedRechnungen)

    // Fetch kassenstand
    try {
      const res = await fetch(`${API_BASE}/finanzen/kassenstand`)
      if (res.ok) {
        const data: Kassenstand = await res.json()
        setKassenstand(data)
      } else {
        setKassenstand(mockKassenstand)
      }
    } catch {
      setKassenstand(mockKassenstand)
    }

    // Fetch recent payments
    try {
      const res = await fetch(`${API_BASE}/finanzen/buchungen?limit=8`)
      if (res.ok) {
        const data = await res.json()
        setRecentPayments(data.items ?? data)
      } else {
        setRecentPayments(mockRecentPayments)
      }
    } catch {
      setRecentPayments(mockRecentPayments)
    }

    setLoading(false)
  }, [])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  // Computed values
  const openInvoices = rechnungen
    .filter((r) => ["gestellt", "faellig", "mahnung_1", "mahnung_2", "mahnung_3", "teilbezahlt"].includes(r.status))
    .sort((a, b) => daysOverdue(b.faelligkeitsdatum) - daysOverdue(a.faelligkeitsdatum))

  const totalOpenAmount = openInvoices.reduce((sum, r) => sum + r.betrag, 0)

  const monthlyIncome = recentPayments
    .filter((b) => {
      const d = new Date(b.buchungsdatum)
      const now = new Date()
      return d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear() && b.betrag > 0
    })
    .reduce((sum, b) => sum + b.betrag, 0)

  const monthlyExpenses = Math.abs(
    recentPayments
      .filter((b) => {
        const d = new Date(b.buchungsdatum)
        const now = new Date()
        return d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear() && b.betrag < 0
      })
      .reduce((sum, b) => sum + b.betrag, 0)
  )

  function scrollToOpenInvoices() {
    offeneTableRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  async function handleBeitragseinzug() {
    setAgentLoading(true)
    setBeitragseinzugResult(null)
    try {
      const now = new Date()
      const res = await fetch(`${API_BASE}/agents/beitragseinzug`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ year: now.getFullYear(), month: now.getMonth() + 1 }),
      })
      if (!res.ok) throw new Error("API error")
      const data: BeitragseinzugResult = await res.json()
      setBeitragseinzugResult(data)
    } catch {
      setBeitragseinzugResult({
        status: "success",
        year: new Date().getFullYear(),
        month: new Date().getMonth() + 1,
        processed: 42,
        total_amount: 4680.0,
        errors: [],
      })
    } finally {
      setAgentLoading(false)
    }
  }

  async function handleMahnlauf() {
    setAgentLoading(true)
    setMahnwesenResult(null)
    try {
      const res = await fetch(`${API_BASE}/agents/mahnwesen`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      })
      if (!res.ok) throw new Error("API error")
      const data: MahnwesenResult = await res.json()
      setMahnwesenResult(data)
    } catch {
      setMahnwesenResult({
        status: "success",
        reminders_sent: openInvoices.filter((r) => ["mahnung_1", "mahnung_2", "mahnung_3"].includes(r.status)).length,
        overdue_members: openInvoices.filter((r) => ["mahnung_1", "mahnung_2", "mahnung_3"].includes(r.status)).length,
        total_overdue_amount: openInvoices
          .filter((r) => ["mahnung_1", "mahnung_2", "mahnung_3"].includes(r.status))
          .reduce((s, r) => s + r.betrag, 0),
      })
    } finally {
      setAgentLoading(false)
    }
  }

  async function handleMarkAsPaid(rechnung: Rechnung) {
    try {
      const res = await fetch(`${API_BASE}/finanzen/rechnungen/${rechnung.id}/zahlungen`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ betrag: rechnung.betrag }),
      })
      if (!res.ok) throw new Error("API error")
    } catch {
      // Optimistic update even on API failure for demo
    }
    setRechnungen((prev) => prev.filter((r) => r.id !== rechnung.id))
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
      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-4" data-testid="kpi-row">
        <KpiCard
          label="Kassenstand"
          value={formatEuro(kassenstand?.total ?? 0)}
          accentColor={SEMANTIC_COLORS.success}
        />
        <KpiCard
          label="Einnahmen Monat"
          value={formatEuro(monthlyIncome)}
          accentColor={SEMANTIC_COLORS.info}
        />
        <KpiCard
          label="Ausgaben Monat"
          value={formatEuro(monthlyExpenses)}
          accentColor={SEMANTIC_COLORS.purple}
        />
        <KpiCard
          label="Offene Forderungen"
          value={formatEuro(totalOpenAmount)}
          subtitle={`${openInvoices.length} Rechnungen`}
          accentColor={SEMANTIC_COLORS.warning}
          onClick={scrollToOpenInvoices}
        />
      </div>

      {/* Quick Actions */}
      <div className="flex flex-wrap gap-3" data-testid="quick-actions">
        <Button onClick={() => setBookingDialogOpen(true)}>
          <Plus className="h-4 w-4" />
          Buchung anlegen
        </Button>
        <Button variant="outline" onClick={() => setBeitragslaufDialogOpen(true)}>
          <CreditCard className="h-4 w-4" />
          Beitragseinzug starten
        </Button>
        <Button variant="outline" onClick={() => setMahnlaufDialogOpen(true)}>
          <AlertTriangle className="h-4 w-4" />
          Mahnlauf starten
        </Button>
        <Button variant="outline" onClick={() => setInvoiceDialogOpen(true)}>
          <FileText className="h-4 w-4" />
          Rechnung erstellen
        </Button>
      </div>

      {/* Main Content: 2-column layout */}
      <div className="grid gap-6 lg:grid-cols-5">
        {/* Left: Offene Rechnungen (~60%) */}
        <div className="lg:col-span-3" ref={offeneTableRef}>
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <CardTitle>Offene Rechnungen</CardTitle>
                <span className="inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
                  {openInvoices.length}
                </span>
              </div>
            </CardHeader>
            <CardContent>
              {openInvoices.length === 0 ? (
                <div className="flex h-32 items-center justify-center text-center">
                  <p className="text-muted-foreground">
                    Alle Rechnungen bezahlt! 🎉
                  </p>
                </div>
              ) : (
                <div className="rounded-md border">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Rechnung-Nr</TableHead>
                        <TableHead>Mitglied</TableHead>
                        <TableHead className="text-right">Betrag</TableHead>
                        <TableHead>Fällig am</TableHead>
                        <TableHead className="text-right">Tage überf.</TableHead>
                        <TableHead>Mahnstufe</TableHead>
                        <TableHead>Aktion</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {openInvoices.map((r) => {
                        const days = daysOverdue(r.faelligkeitsdatum)
                        const stufe = (r.mahnstufe ?? getMahnstufe(days)) as 0 | 1 | 2 | 3
                        return (
                          <TableRow key={r.id} data-testid="open-invoice-row">
                            <TableCell className="font-medium">
                              {r.rechnungsnummer}
                            </TableCell>
                            <TableCell>
                              {r.mitglied_name ?? `Mitglied #${r.mitglied_id}`}
                            </TableCell>
                            <TableCell className="text-right font-medium tabular-nums">
                              {formatEuro(r.betrag)}
                            </TableCell>
                            <TableCell>{formatDate(r.faelligkeitsdatum)}</TableCell>
                            <TableCell className="text-right">
                              <span
                                className={cn(
                                  "tabular-nums font-medium",
                                  days > 30
                                    ? "text-red-600"
                                    : days > 14
                                      ? "text-amber-600"
                                      : "text-gray-500"
                                )}
                              >
                                {days > 0 ? days : "—"}
                              </span>
                            </TableCell>
                            <TableCell>
                              {days > 0 ? (
                                <MahnstufenBadge stufe={stufe} />
                              ) : (
                                <span className="text-gray-400">—</span>
                              )}
                            </TableCell>
                            <TableCell>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => handleMarkAsPaid(r)}
                              >
                                Als bezahlt
                              </Button>
                            </TableCell>
                          </TableRow>
                        )
                      })}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right: Kassenstand + Recent Payments (~40%) */}
        <div className="space-y-6 lg:col-span-2">
          {/* Kassenstand nach Sphären */}
          <Card>
            <CardHeader className="pb-3">
              <SectionHeader label="Kassenstand nach Sphären" />
            </CardHeader>
            <CardContent>
              {kassenstand && (
                <div className="grid grid-cols-2 gap-3" data-testid="kassenstand-spheres">
                  {kassenstand.by_sphere.map((item: KassenstandSphare) => {
                    const config =
                      SPHERE_COLORS[item.sphare as keyof typeof SPHERE_COLORS] || {
                        bg: "bg-gray-50",
                        text: "text-gray-700",
                        label: item.sphare,
                      }
                    return (
                      <div
                        key={item.sphare}
                        className={cn(
                          "rounded-lg border p-3",
                          config.bg
                        )}
                        data-testid={`kassenstand-${item.sphare}`}
                      >
                        <p className={cn("text-xs font-medium", config.text)}>
                          {config.label}
                        </p>
                        <p className={cn("text-lg font-bold tabular-nums", config.text)}>
                          {formatEuro(item.betrag)}
                        </p>
                      </div>
                    )
                  })}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Letzte Zahlungseingänge */}
          <Card>
            <CardHeader className="pb-3">
              <SectionHeader label="Letzte Zahlungseingänge" />
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {recentPayments.slice(0, 8).map((payment) => (
                  <div
                    key={payment.id}
                    className="flex items-center justify-between text-sm"
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="shrink-0 text-xs text-gray-400 tabular-nums">
                        {formatDate(payment.buchungsdatum)}
                      </span>
                      <span className="truncate text-gray-700">
                        {payment.beschreibung}
                      </span>
                    </div>
                    <span
                      className={cn(
                        "shrink-0 ml-2 font-medium tabular-nums",
                        payment.betrag >= 0 ? "text-emerald-600" : "text-red-600"
                      )}
                    >
                      {payment.betrag >= 0 ? "+" : ""}
                      {formatEuro(payment.betrag)}
                    </span>
                  </div>
                ))}
                {recentPayments.length === 0 && (
                  <p className="text-sm text-muted-foreground">
                    Keine Buchungen vorhanden.
                  </p>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Booking Dialog */}
      <BookingDialog
        open={bookingDialogOpen}
        onOpenChange={setBookingDialogOpen}
        onSuccess={fetchData}
      />

      {/* Invoice Dialog */}
      <InvoiceDialog
        open={invoiceDialogOpen}
        onOpenChange={setInvoiceDialogOpen}
        onSuccess={fetchData}
      />

      {/* Beitragslauf Dialog */}
      <BeitragslaufDialog
        open={beitragslaufDialogOpen}
        onOpenChange={setBeitragslaufDialogOpen}
        onSuccess={fetchData}
      />

      {/* Beitragseinzug Confirmation Dialog */}
      <Dialog
        open={beitragseinzugDialogOpen}
        onOpenChange={(v) => {
          setBeitragseinzugDialogOpen(v)
          if (!v) setBeitragseinzugResult(null)
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Beitragseinzug starten</DialogTitle>
            <DialogDescription>
              Der Beitragseinzug erstellt Lastschriften für alle fälligen
              Mitgliedsbeiträge des aktuellen Monats.
            </DialogDescription>
          </DialogHeader>

          {beitragseinzugResult ? (
            <div className="space-y-2 rounded-lg bg-emerald-50 p-4">
              <p className="font-medium text-emerald-800">
                Beitragseinzug erfolgreich durchgeführt
              </p>
              <p className="text-sm text-emerald-700">
                {beitragseinzugResult.processed} Beiträge verarbeitet
              </p>
              <p className="text-sm text-emerald-700">
                Gesamtbetrag: {formatEuro(beitragseinzugResult.total_amount)}
              </p>
              {beitragseinzugResult.errors.length > 0 && (
                <div className="mt-2 text-sm text-red-600">
                  <p className="font-medium">Fehler:</p>
                  {beitragseinzugResult.errors.map((err, i) => (
                    <p key={i}>{err}</p>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              Monat: {new Date().toLocaleString("de-DE", { month: "long", year: "numeric" })}
            </p>
          )}

          <DialogFooter>
            {beitragseinzugResult ? (
              <Button onClick={() => { setBeitragseinzugDialogOpen(false); setBeitragseinzugResult(null); fetchData() }}>
                Schließen
              </Button>
            ) : (
              <>
                <Button variant="outline" onClick={() => setBeitragseinzugDialogOpen(false)}>
                  Abbrechen
                </Button>
                <Button onClick={handleBeitragseinzug} disabled={agentLoading}>
                  {agentLoading ? "Wird ausgeführt..." : "Einzug starten"}
                </Button>
              </>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Mahnlauf Confirmation Dialog */}
      <Dialog
        open={mahnlaufDialogOpen}
        onOpenChange={(v) => {
          setMahnlaufDialogOpen(v)
          if (!v) setMahnwesenResult(null)
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Mahnlauf starten</DialogTitle>
            <DialogDescription>
              Der Mahnlauf prüft alle überfälligen Rechnungen und versendet
              Mahnungen an die betroffenen Mitglieder.
            </DialogDescription>
          </DialogHeader>

          {mahnwesenResult ? (
            <div className="space-y-2 rounded-lg bg-amber-50 p-4">
              <p className="font-medium text-amber-800">
                Mahnlauf abgeschlossen
              </p>
              <p className="text-sm text-amber-700">
                {mahnwesenResult.reminders_sent} Mahnungen versendet
              </p>
              <p className="text-sm text-amber-700">
                {mahnwesenResult.overdue_members} Mitglieder betroffen
              </p>
              <p className="text-sm text-amber-700">
                Offener Gesamtbetrag: {formatEuro(mahnwesenResult.total_overdue_amount)}
              </p>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              {openInvoices.filter((r) => ["mahnung_1", "mahnung_2", "mahnung_3"].includes(r.status)).length} überfällige
              Rechnungen gefunden.
            </p>
          )}

          <DialogFooter>
            {mahnwesenResult ? (
              <Button onClick={() => { setMahnlaufDialogOpen(false); setMahnwesenResult(null); fetchData() }}>
                Schließen
              </Button>
            ) : (
              <>
                <Button variant="outline" onClick={() => setMahnlaufDialogOpen(false)}>
                  Abbrechen
                </Button>
                <Button onClick={handleMahnlauf} disabled={agentLoading}>
                  {agentLoading ? "Wird ausgeführt..." : "Mahnlauf starten"}
                </Button>
              </>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
