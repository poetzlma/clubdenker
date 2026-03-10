import { useState, useEffect, useCallback } from "react"
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts"
import type { Rechnung } from "@/types/finance"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

const API_BASE = "/api"

function formatEuro(amount: number): string {
  return amount.toLocaleString("de-DE", {
    style: "currency",
    currency: "EUR",
  })
}

const statusConfig: Record<
  Rechnung["status"],
  { label: string; color: string }
> = {
  bezahlt: { label: "Bezahlt", color: "#22c55e" },
  offen: { label: "Offen", color: "#3b82f6" },
  ueberfaellig: { label: "Überfällig", color: "#ef4444" },
  storniert: { label: "Storniert", color: "#9ca3af" },
}

const mockRechnungen: Rechnung[] = [
  {
    id: 1,
    rechnungsnummer: "R-2025-001",
    mitglied_id: 1,
    betrag: 120.0,
    beschreibung: "Jahresbeitrag 2025",
    rechnungsdatum: "2025-01-15",
    faelligkeitsdatum: "2025-02-15",
    status: "bezahlt",
    created_at: "2025-01-15T10:00:00Z",
  },
  {
    id: 2,
    rechnungsnummer: "R-2025-002",
    mitglied_id: 2,
    betrag: 120.0,
    beschreibung: "Jahresbeitrag 2025",
    rechnungsdatum: "2025-01-15",
    faelligkeitsdatum: "2025-02-15",
    status: "bezahlt",
    created_at: "2025-01-15T10:00:00Z",
  },
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
    id: 4,
    rechnungsnummer: "R-2025-004",
    mitglied_id: 4,
    betrag: 0.0,
    beschreibung: "Ehrenmitglied - beitragsfrei",
    rechnungsdatum: "2025-01-15",
    faelligkeitsdatum: "2025-02-15",
    status: "storniert",
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

export function PaymentOverview() {
  const [rechnungen, setRechnungen] = useState<Rechnung[]>([])
  const [loading, setLoading] = useState(true)

  const fetchRechnungen = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/invoices`)
      if (!res.ok) throw new Error("API error")
      const data = await res.json()
      setRechnungen(data.items ?? data)
    } catch {
      setRechnungen(mockRechnungen)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchRechnungen()
  }, [fetchRechnungen])

  const totalBetrag = rechnungen.reduce((sum, r) => sum + r.betrag, 0)
  const offenCount = rechnungen.filter((r) => r.status === "offen").length
  const ueberfaelligCount = rechnungen.filter(
    (r) => r.status === "ueberfaellig"
  ).length
  const bezahltCount = rechnungen.filter((r) => r.status === "bezahlt").length

  const pieData = (
    Object.keys(statusConfig) as Rechnung["status"][]
  )
    .map((status) => ({
      name: statusConfig[status].label,
      value: rechnungen.filter((r) => r.status === status).length,
      color: statusConfig[status].color,
    }))
    .filter((d) => d.value > 0)

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <p className="text-muted-foreground">Laden...</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card data-testid="stat-total">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Gesamtbetrag
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{formatEuro(totalBetrag)}</p>
          </CardContent>
        </Card>
        <Card data-testid="stat-offen">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Offene Rechnungen
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-blue-600">{offenCount}</p>
          </CardContent>
        </Card>
        <Card data-testid="stat-ueberfaellig">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Überfällig
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-red-600">
              {ueberfaelligCount}
            </p>
          </CardContent>
        </Card>
        <Card data-testid="stat-bezahlt">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Bezahlt
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-green-600">{bezahltCount}</p>
          </CardContent>
        </Card>
      </div>

      {/* Pie Chart */}
      <Card>
        <CardHeader>
          <CardTitle>Rechnungsstatus</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={2}
                  dataKey="value"
                >
                  {pieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(value, name) => [`${value}`, `${name}`]}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-4 flex flex-wrap justify-center gap-4">
            {pieData.map((entry) => (
              <div key={entry.name} className="flex items-center gap-2">
                <div
                  className="h-3 w-3 rounded-full"
                  style={{ backgroundColor: entry.color }}
                />
                <span className="text-sm text-muted-foreground">
                  {entry.name} ({entry.value})
                </span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
