import { useState, useEffect, useCallback } from "react"
import type {
  EuerReport,
  EuerSphareItem,
  EuerMonatItem,
  EuerKostenstelleItem,
} from "@/types/finance"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { cn } from "@/lib/utils"
import { SPHERE_COLORS } from "@/constants/design"
import { Download, TrendingUp, TrendingDown, Minus } from "lucide-react"

const API_BASE = "/api"

function formatEuro(amount: number): string {
  return amount.toLocaleString("de-DE", {
    style: "currency",
    currency: "EUR",
  })
}

function formatMonthLabel(monat: string): string {
  const [year, month] = monat.split("-")
  const monthNames = [
    "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember",
  ]
  return `${monthNames[parseInt(month, 10) - 1]} ${year}`
}

const SPHERE_OPTIONS = [
  { value: "all", label: "Alle Sphären" },
  { value: "ideell", label: "Ideell" },
  { value: "zweckbetrieb", label: "Zweckbetrieb" },
  { value: "vermoegensverwaltung", label: "Vermögensverwaltung" },
  { value: "wirtschaftlich", label: "Wirtschaftlich" },
]

// Mock data for when API is unavailable
const mockReport: EuerReport = {
  jahr: new Date().getFullYear(),
  zeitraum: {
    von: `${new Date().getFullYear()}-01-01`,
    bis: `${new Date().getFullYear()}-12-31`,
  },
  gesamt: { einnahmen: 52400, ausgaben: 37200, ergebnis: 15200 },
  nach_sphare: [
    { sphare: "ideell", einnahmen: 22000, ausgaben: 15000, ergebnis: 7000 },
    { sphare: "zweckbetrieb", einnahmen: 14000, ausgaben: 10800, ergebnis: 3200 },
    { sphare: "vermoegensverwaltung", einnahmen: 8400, ausgaben: 5200, ergebnis: 3200 },
    { sphare: "wirtschaftlich", einnahmen: 8000, ausgaben: 6200, ergebnis: 1800 },
  ],
  nach_monat: [
    { monat: `${new Date().getFullYear()}-01`, einnahmen: 6200, ausgaben: 3800, ergebnis: 2400 },
    { monat: `${new Date().getFullYear()}-02`, einnahmen: 4800, ausgaben: 3200, ergebnis: 1600 },
    { monat: `${new Date().getFullYear()}-03`, einnahmen: 5100, ausgaben: 2900, ergebnis: 2200 },
  ],
  nach_kostenstelle: [
    { kostenstelle: "Fussball", einnahmen: 12000, ausgaben: 9500, ergebnis: 2500 },
    { kostenstelle: "Tennis", einnahmen: 8000, ausgaben: 6200, ergebnis: 1800 },
    { kostenstelle: "Verwaltung", einnahmen: 2000, ausgaben: 4500, ergebnis: -2500 },
  ],
}

function generateCsv(report: EuerReport): string {
  const lines: string[] = []

  lines.push(`EÜR ${report.jahr}`)
  lines.push(`Zeitraum: ${report.zeitraum.von} bis ${report.zeitraum.bis}`)
  lines.push("")

  // Gesamt
  lines.push("Zusammenfassung")
  lines.push("Typ;Betrag")
  lines.push(`Einnahmen;${report.gesamt.einnahmen.toFixed(2).replace(".", ",")}`)
  lines.push(`Ausgaben;${report.gesamt.ausgaben.toFixed(2).replace(".", ",")}`)
  lines.push(`Ergebnis;${report.gesamt.ergebnis.toFixed(2).replace(".", ",")}`)
  lines.push("")

  // Nach Sphäre
  lines.push("Nach Sphäre")
  lines.push("Sphäre;Einnahmen;Ausgaben;Ergebnis")
  for (const item of report.nach_sphare) {
    const label = SPHERE_COLORS[item.sphare as keyof typeof SPHERE_COLORS]?.label ?? item.sphare
    lines.push(
      `${label};${item.einnahmen.toFixed(2).replace(".", ",")};${item.ausgaben.toFixed(2).replace(".", ",")};${item.ergebnis.toFixed(2).replace(".", ",")}`
    )
  }
  lines.push("")

  // Nach Monat
  lines.push("Nach Monat")
  lines.push("Monat;Einnahmen;Ausgaben;Ergebnis")
  for (const item of report.nach_monat) {
    lines.push(
      `${item.monat};${item.einnahmen.toFixed(2).replace(".", ",")};${item.ausgaben.toFixed(2).replace(".", ",")};${item.ergebnis.toFixed(2).replace(".", ",")}`
    )
  }
  lines.push("")

  // Nach Kostenstelle
  if (report.nach_kostenstelle.length > 0) {
    lines.push("Nach Kostenstelle")
    lines.push("Kostenstelle;Einnahmen;Ausgaben;Ergebnis")
    for (const item of report.nach_kostenstelle) {
      lines.push(
        `${item.kostenstelle};${item.einnahmen.toFixed(2).replace(".", ",")};${item.ausgaben.toFixed(2).replace(".", ",")};${item.ergebnis.toFixed(2).replace(".", ",")}`
      )
    }
  }

  return lines.join("\n")
}

function downloadCsv(report: EuerReport) {
  const csv = generateCsv(report)
  const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8;" })
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = `euer_${report.jahr}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

function SphereBadge({ sphare }: { sphare: string }) {
  const config =
    SPHERE_COLORS[sphare as keyof typeof SPHERE_COLORS] || {
      bg: "bg-gray-50",
      text: "text-gray-700",
      label: sphare,
    }
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        config.bg,
        config.text
      )}
    >
      {config.label}
    </span>
  )
}

function ErgebnisCell({ value }: { value: number }) {
  return (
    <TableCell className="text-right font-medium tabular-nums">
      <span
        className={cn(
          value > 0
            ? "text-emerald-600"
            : value < 0
              ? "text-red-600"
              : "text-gray-500"
        )}
      >
        {formatEuro(value)}
      </span>
    </TableCell>
  )
}

export function EuerReport() {
  const currentYear = new Date().getFullYear()
  const [year, setYear] = useState(currentYear)
  const [sphare, setSphare] = useState("all")
  const [report, setReport] = useState<EuerReport | null>(null)
  const [loading, setLoading] = useState(true)

  const yearOptions = Array.from({ length: 5 }, (_, i) => currentYear - i)

  const fetchReport = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({ jahr: String(year) })
      if (sphare !== "all") {
        params.set("sphare", sphare)
      }
      const res = await fetch(`${API_BASE}/finanzen/euer?${params}`)
      if (res.ok) {
        const data: EuerReport = await res.json()
        setReport(data)
      } else {
        setReport(mockReport)
      }
    } catch {
      setReport(mockReport)
    }
    setLoading(false)
  }, [year, sphare])

  useEffect(() => {
    fetchReport()
  }, [fetchReport])

  if (loading || !report) {
    return (
      <div className="flex h-64 items-center justify-center">
        <p className="text-muted-foreground">Laden...</p>
      </div>
    )
  }

  const ergebnis = report.gesamt.ergebnis

  return (
    <div className="space-y-6">
      {/* Controls */}
      <div className="flex flex-wrap items-center gap-3">
        <Select value={String(year)} onValueChange={(v) => setYear(Number(v))}>
          <SelectTrigger className="w-[140px]">
            <SelectValue placeholder="Jahr" />
          </SelectTrigger>
          <SelectContent>
            {yearOptions.map((y) => (
              <SelectItem key={y} value={String(y)}>
                {y}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={sphare} onValueChange={setSphare}>
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder="Sphäre" />
          </SelectTrigger>
          <SelectContent>
            {SPHERE_OPTIONS.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Button variant="outline" onClick={() => downloadCsv(report)}>
          <Download className="mr-2 h-4 w-4" />
          Export CSV
        </Button>
      </div>

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card className="relative overflow-hidden">
          <div className="absolute left-0 right-0 top-0 h-[2px] bg-emerald-500" />
          <CardContent className="pt-5 pb-4">
            <p className="text-xs font-semibold uppercase tracking-wider text-gray-500">
              Gesamteinnahmen
            </p>
            <p className="mt-1 text-3xl font-bold tabular-nums text-gray-900">
              {formatEuro(report.gesamt.einnahmen)}
            </p>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden">
          <div className="absolute left-0 right-0 top-0 h-[2px] bg-red-500" />
          <CardContent className="pt-5 pb-4">
            <p className="text-xs font-semibold uppercase tracking-wider text-gray-500">
              Gesamtausgaben
            </p>
            <p className="mt-1 text-3xl font-bold tabular-nums text-gray-900">
              {formatEuro(report.gesamt.ausgaben)}
            </p>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden">
          <div
            className={cn(
              "absolute left-0 right-0 top-0 h-[2px]",
              ergebnis >= 0 ? "bg-emerald-500" : "bg-red-500"
            )}
          />
          <CardContent className="pt-5 pb-4">
            <p className="text-xs font-semibold uppercase tracking-wider text-gray-500">
              Ergebnis
            </p>
            <div className="mt-1 flex items-center gap-2">
              <p
                className={cn(
                  "text-3xl font-bold tabular-nums",
                  ergebnis > 0
                    ? "text-emerald-600"
                    : ergebnis < 0
                      ? "text-red-600"
                      : "text-gray-900"
                )}
              >
                {formatEuro(ergebnis)}
              </p>
              {ergebnis > 0 && <TrendingUp className="h-5 w-5 text-emerald-500" />}
              {ergebnis < 0 && <TrendingDown className="h-5 w-5 text-red-500" />}
              {ergebnis === 0 && <Minus className="h-5 w-5 text-gray-400" />}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Table: Nach Sphäre */}
      {report.nach_sphare.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Nach Sphäre</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Sphäre</TableHead>
                    <TableHead className="text-right">Einnahmen</TableHead>
                    <TableHead className="text-right">Ausgaben</TableHead>
                    <TableHead className="text-right">Ergebnis</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {report.nach_sphare.map((item: EuerSphareItem) => (
                    <TableRow key={item.sphare}>
                      <TableCell>
                        <SphereBadge sphare={item.sphare} />
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {formatEuro(item.einnahmen)}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {formatEuro(item.ausgaben)}
                      </TableCell>
                      <ErgebnisCell value={item.ergebnis} />
                    </TableRow>
                  ))}
                  {/* Summe */}
                  <TableRow className="font-semibold border-t-2">
                    <TableCell>Gesamt</TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatEuro(report.gesamt.einnahmen)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatEuro(report.gesamt.ausgaben)}
                    </TableCell>
                    <ErgebnisCell value={report.gesamt.ergebnis} />
                  </TableRow>
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Table: Nach Monat */}
      {report.nach_monat.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Nach Monat</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Monat</TableHead>
                    <TableHead className="text-right">Einnahmen</TableHead>
                    <TableHead className="text-right">Ausgaben</TableHead>
                    <TableHead className="text-right">Ergebnis</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {report.nach_monat.map((item: EuerMonatItem) => (
                    <TableRow key={item.monat}>
                      <TableCell className="font-medium">
                        {formatMonthLabel(item.monat)}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {formatEuro(item.einnahmen)}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {formatEuro(item.ausgaben)}
                      </TableCell>
                      <ErgebnisCell value={item.ergebnis} />
                    </TableRow>
                  ))}
                  {/* Summe */}
                  <TableRow className="font-semibold border-t-2">
                    <TableCell>Gesamt</TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatEuro(report.gesamt.einnahmen)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatEuro(report.gesamt.ausgaben)}
                    </TableCell>
                    <ErgebnisCell value={report.gesamt.ergebnis} />
                  </TableRow>
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Table: Nach Kostenstelle */}
      {report.nach_kostenstelle.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Nach Kostenstelle</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Kostenstelle</TableHead>
                    <TableHead className="text-right">Einnahmen</TableHead>
                    <TableHead className="text-right">Ausgaben</TableHead>
                    <TableHead className="text-right">Ergebnis</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {report.nach_kostenstelle.map((item: EuerKostenstelleItem) => (
                    <TableRow key={item.kostenstelle}>
                      <TableCell className="font-medium">
                        {item.kostenstelle}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {formatEuro(item.einnahmen)}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {formatEuro(item.ausgaben)}
                      </TableCell>
                      <ErgebnisCell value={item.ergebnis} />
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
