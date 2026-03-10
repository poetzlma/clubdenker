import { Users, UserPlus, Wallet, AlertCircle } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

interface KpiCard {
  title: string
  value: string
  description: string
  icon: React.ComponentType<{ className?: string }>
}

const kpiData: KpiCard[] = [
  {
    title: "Aktive Mitglieder",
    value: "248",
    description: "Gesamt aktive Mitglieder",
    icon: Users,
  },
  {
    title: "Neue diesen Monat",
    value: "12",
    description: "+4 gegenüber Vormonat",
    icon: UserPlus,
  },
  {
    title: "Kassenstand",
    value: "14.520,00 €",
    description: "Aktueller Kontostand",
    icon: Wallet,
  },
  {
    title: "Offene Beiträge",
    value: "23",
    description: "Ausstehende Zahlungen",
    icon: AlertCircle,
  },
]

export function KpiCards() {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4" data-testid="kpi-cards">
      {kpiData.map((kpi) => (
        <Card key={kpi.title}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">{kpi.title}</CardTitle>
            <kpi.icon className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{kpi.value}</div>
            <p className="text-xs text-muted-foreground">{kpi.description}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
