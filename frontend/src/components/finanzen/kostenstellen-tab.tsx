import { useState, useEffect, useCallback } from "react"
import type { Kostenstelle } from "@/types/finance"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import { UTILIZATION } from "@/constants/design"

const API_BASE = "/api"

function formatEuro(amount: number | null | undefined): string {
  return (amount ?? 0).toLocaleString("de-DE", {
    style: "currency",
    currency: "EUR",
  })
}

const mockKostenstellen: Kostenstelle[] = [
  {
    id: 1,
    name: "Fussball",
    beschreibung: "Kosten der Fussballabteilung",
    budget: 15000,
    freigabelimit: 500,
    ausgegeben: 8500,
    verfuegbar: 6500,
  },
  {
    id: 2,
    name: "Tennis",
    beschreibung: "Kosten der Tennisabteilung",
    budget: 8000,
    freigabelimit: 300,
    ausgegeben: 6800,
    verfuegbar: 1200,
  },
  {
    id: 3,
    name: "Schwimmen",
    beschreibung: "Kosten der Schwimmabteilung",
    budget: 12000,
    freigabelimit: 400,
    ausgegeben: 11500,
    verfuegbar: 500,
  },
  {
    id: 4,
    name: "Verwaltung",
    beschreibung: "Allgemeine Verwaltungskosten",
    budget: 20000,
    freigabelimit: 1000,
    ausgegeben: 10000,
    verfuegbar: 10000,
  },
  {
    id: 5,
    name: "Jugendarbeit",
    beschreibung: "Kosten der Jugendarbeit",
    budget: 5000,
    freigabelimit: 200,
    ausgegeben: 2000,
    verfuegbar: 3000,
  },
]

function getUtilizationColor(percent: number): string {
  if (percent >= UTILIZATION.warning.max) return UTILIZATION.danger.color
  if (percent >= UTILIZATION.ok.max) return UTILIZATION.warning.color
  return UTILIZATION.ok.color
}

function getProgressBarColor(percent: number): string {
  if (percent >= UTILIZATION.warning.max) return "bg-red-500"
  if (percent >= UTILIZATION.ok.max) return "bg-amber-500"
  return "bg-emerald-500"
}

export function KostenstellenTab() {
  const [kostenstellen, setKostenstellen] = useState<Kostenstelle[]>([])
  const [loading, setLoading] = useState(true)

  const fetchKostenstellen = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/finanzen/kostenstellen`)
      if (!res.ok) throw new Error("API error")
      const data = await res.json()
      setKostenstellen(data.items ?? data)
    } catch {
      setKostenstellen(mockKostenstellen)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchKostenstellen()
  }, [fetchKostenstellen])

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <p className="text-muted-foreground">Laden...</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {kostenstellen.map((ks) => {
          const budget = ks.budget ?? 0
          const ausgegeben = ks.ausgegeben ?? 0
          const percent = budget > 0 ? (ausgegeben / budget) * 100 : 0
          return (
            <Card key={ks.id} data-testid="kostenstelle-card">
              <CardHeader className="pb-2">
                <CardTitle className="text-lg">{ks.name}</CardTitle>
                <p className="text-sm text-muted-foreground">
                  {ks.beschreibung}
                </p>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Budget</span>
                  <span className="font-medium tabular-nums">{formatEuro(ks.budget)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Ausgegeben</span>
                  <span className="font-medium tabular-nums">{formatEuro(ks.ausgegeben)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Verfügbar</span>
                  <span className="font-medium tabular-nums">{formatEuro(ks.verfuegbar)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Freigabelimit</span>
                  <span className="font-medium tabular-nums">
                    {formatEuro(ks.freigabelimit)}
                  </span>
                </div>
                <div className="space-y-1">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Auslastung</span>
                    <span
                      className={cn(
                        "font-medium tabular-nums",
                        getUtilizationColor(percent)
                      )}
                    >
                      {percent.toFixed(0)}%
                    </span>
                  </div>
                  <div className="h-2 w-full overflow-hidden rounded-full bg-primary/20">
                    <div
                      className={cn(
                        "h-full rounded-full transition-all",
                        getProgressBarColor(percent)
                      )}
                      style={{ width: `${Math.min(percent, 100)}%` }}
                      data-testid="progress-bar"
                    />
                  </div>
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>
    </div>
  )
}
