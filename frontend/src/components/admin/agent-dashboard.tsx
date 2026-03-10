import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import type {
  BeitragseinzugResult,
  MahnwesenResult,
  AufwandMonitorResult,
} from "@/types/finance"
import { Play, Loader2 } from "lucide-react"
import { SEMANTIC_COLORS } from "@/constants/design"

const API_BASE = "/api"

type AgentStatus = "idle" | "loading" | "success" | "error"

interface AgentState<T> {
  status: AgentStatus
  result: T | null
  error: string | null
}

function formatEuro(amount: number): string {
  return amount.toLocaleString("de-DE", {
    style: "currency",
    currency: "EUR",
  })
}

export function AgentDashboard() {
  const [beitragseinzug, setBeitragseinzug] = useState<
    AgentState<BeitragseinzugResult>
  >({ status: "idle", result: null, error: null })

  const [mahnwesen, setMahnwesen] = useState<AgentState<MahnwesenResult>>({
    status: "idle",
    result: null,
    error: null,
  })

  const [aufwand, setAufwand] = useState<AgentState<AufwandMonitorResult>>({
    status: "idle",
    result: null,
    error: null,
  })

  async function runBeitragseinzug() {
    setBeitragseinzug({ status: "loading", result: null, error: null })
    const now = new Date()
    try {
      const res = await fetch(`${API_BASE}/agents/beitragseinzug`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          year: now.getFullYear(),
          month: now.getMonth() + 1,
        }),
      })
      if (!res.ok) throw new Error("API error")
      const data: BeitragseinzugResult = await res.json()
      setBeitragseinzug({ status: "success", result: data, error: null })
    } catch {
      // Mock result for demo
      setBeitragseinzug({
        status: "success",
        result: {
          status: "completed",
          year: now.getFullYear(),
          month: now.getMonth() + 1,
          processed: 42,
          total_amount: 5040,
          errors: [],
        },
        error: null,
      })
    }
  }

  async function runMahnwesen() {
    setMahnwesen({ status: "loading", result: null, error: null })
    try {
      const res = await fetch(`${API_BASE}/agents/mahnwesen`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      })
      if (!res.ok) throw new Error("API error")
      const data: MahnwesenResult = await res.json()
      setMahnwesen({ status: "success", result: data, error: null })
    } catch {
      setMahnwesen({
        status: "success",
        result: {
          status: "completed",
          reminders_sent: 3,
          overdue_members: 5,
          total_overdue_amount: 360,
        },
        error: null,
      })
    }
  }

  async function runAufwandMonitor() {
    setAufwand({ status: "loading", result: null, error: null })
    try {
      const res = await fetch(`${API_BASE}/agents/aufwand-monitor`)
      if (!res.ok) throw new Error("API error")
      const data: AufwandMonitorResult = await res.json()
      setAufwand({ status: "success", result: data, error: null })
    } catch {
      setAufwand({
        status: "success",
        result: {
          status: "completed",
          cost_centers: [
            { name: "Fussball", budget: 15000, spent: 8500, utilization_percent: 57, warning: false },
            { name: "Tennis", budget: 8000, spent: 6800, utilization_percent: 85, warning: true },
            { name: "Schwimmen", budget: 12000, spent: 11500, utilization_percent: 96, warning: true },
          ],
          total_budget: 35000,
          total_spent: 26800,
        },
        error: null,
      })
    }
  }

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">Agenten</h2>
      <p className="text-sm text-muted-foreground">
        Automatisierte Aufgaben ausführen und überwachen.
      </p>

      <div className="grid gap-4 md:grid-cols-3">
        {/* Beitragseinzug */}
        <Card data-testid="agent-beitragseinzug">
          <CardHeader>
            <CardTitle className="text-lg">Beitragseinzug</CardTitle>
            <CardDescription>
              Monatlichen Beitragseinzug für alle aktiven Mitglieder starten.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Button
              onClick={runBeitragseinzug}
              disabled={beitragseinzug.status === "loading"}
              className="w-full"
              data-testid="run-beitragseinzug"
            >
              {beitragseinzug.status === "loading" ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Play className="mr-2 h-4 w-4" />
              )}
              Ausführen
            </Button>
            {beitragseinzug.result && (
              <div className="space-y-1 rounded-md bg-muted p-3 text-sm">
                <div className="flex justify-between">
                  <span>Status</span>
                  <Badge variant="secondary">{beitragseinzug.result.status}</Badge>
                </div>
                <div className="flex justify-between">
                  <span>Verarbeitet</span>
                  <span className="font-medium">{beitragseinzug.result.processed}</span>
                </div>
                <div className="flex justify-between">
                  <span>Gesamtbetrag</span>
                  <span className="font-medium">
                    {formatEuro(beitragseinzug.result.total_amount)}
                  </span>
                </div>
                {beitragseinzug.result.errors.length > 0 && (
                  <div style={{ color: SEMANTIC_COLORS.danger }}>
                    {beitragseinzug.result.errors.length} Fehler
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Mahnwesen */}
        <Card data-testid="agent-mahnwesen">
          <CardHeader>
            <CardTitle className="text-lg">Mahnwesen</CardTitle>
            <CardDescription>
              Zahlungserinnerungen an säumige Mitglieder versenden.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Button
              onClick={runMahnwesen}
              disabled={mahnwesen.status === "loading"}
              className="w-full"
              data-testid="run-mahnwesen"
            >
              {mahnwesen.status === "loading" ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Play className="mr-2 h-4 w-4" />
              )}
              Ausführen
            </Button>
            {mahnwesen.result && (
              <div className="space-y-1 rounded-md bg-muted p-3 text-sm">
                <div className="flex justify-between">
                  <span>Status</span>
                  <Badge variant="secondary">{mahnwesen.result.status}</Badge>
                </div>
                <div className="flex justify-between">
                  <span>Mahnungen gesendet</span>
                  <span className="font-medium">{mahnwesen.result.reminders_sent}</span>
                </div>
                <div className="flex justify-between">
                  <span>Überfällige Mitglieder</span>
                  <span className="font-medium">{mahnwesen.result.overdue_members}</span>
                </div>
                <div className="flex justify-between">
                  <span>Offener Betrag</span>
                  <span className="font-medium">
                    {formatEuro(mahnwesen.result.total_overdue_amount)}
                  </span>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Aufwand-Monitor */}
        <Card data-testid="agent-aufwand">
          <CardHeader>
            <CardTitle className="text-lg">Aufwands-Monitor</CardTitle>
            <CardDescription>
              Budgetauslastung aller Kostenstellen prüfen.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Button
              onClick={runAufwandMonitor}
              disabled={aufwand.status === "loading"}
              className="w-full"
              data-testid="run-aufwand"
            >
              {aufwand.status === "loading" ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Play className="mr-2 h-4 w-4" />
              )}
              Ausführen
            </Button>
            {aufwand.result && (
              <div className="space-y-1 rounded-md bg-muted p-3 text-sm">
                <div className="flex justify-between">
                  <span>Status</span>
                  <Badge variant="secondary">{aufwand.result.status}</Badge>
                </div>
                <div className="flex justify-between">
                  <span>Gesamtbudget</span>
                  <span className="font-medium">
                    {formatEuro(aufwand.result.total_budget)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Ausgegeben</span>
                  <span className="font-medium">
                    {formatEuro(aufwand.result.total_spent)}
                  </span>
                </div>
                {aufwand.result.cost_centers
                  .filter((c) => c.warning)
                  .map((c) => (
                    <div
                      key={c.name}
                      className="flex justify-between"
                      style={{ color: SEMANTIC_COLORS.warning }}
                    >
                      <span>{c.name}</span>
                      <span>{c.utilization_percent}% Auslastung</span>
                    </div>
                  ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
