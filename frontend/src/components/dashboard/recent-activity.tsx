import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"

interface Activity {
  id: number
  description: string
  timestamp: string
  type: "mitglied" | "zahlung" | "system"
}

const activities: Activity[] = [
  {
    id: 1,
    description: "Neues Mitglied: Anna Schmidt registriert",
    timestamp: "Vor 2 Stunden",
    type: "mitglied",
  },
  {
    id: 2,
    description: "Beitragszahlung von Max Müller eingegangen",
    timestamp: "Vor 3 Stunden",
    type: "zahlung",
  },
  {
    id: 3,
    description: "Mitgliedsdaten von Lisa Weber aktualisiert",
    timestamp: "Vor 5 Stunden",
    type: "mitglied",
  },
  {
    id: 4,
    description: "Monatliche Beitragsabrechnung gestartet",
    timestamp: "Gestern",
    type: "system",
  },
  {
    id: 5,
    description: "Neues Mitglied: Thomas Fischer registriert",
    timestamp: "Gestern",
    type: "mitglied",
  },
]

const typeBadgeVariant: Record<Activity["type"], "default" | "secondary" | "outline"> = {
  mitglied: "default",
  zahlung: "secondary",
  system: "outline",
}

const typeLabels: Record<Activity["type"], string> = {
  mitglied: "Mitglied",
  zahlung: "Zahlung",
  system: "System",
}

export function RecentActivity() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Letzte Aktivitäten</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {activities.map((activity) => (
            <div
              key={activity.id}
              className="flex items-center justify-between gap-4"
            >
              <div className="flex-1 space-y-1">
                <p className="text-sm font-medium leading-none">
                  {activity.description}
                </p>
                <p className="text-sm text-muted-foreground">
                  {activity.timestamp}
                </p>
              </div>
              <Badge variant={typeBadgeVariant[activity.type]}>
                {typeLabels[activity.type]}
              </Badge>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
