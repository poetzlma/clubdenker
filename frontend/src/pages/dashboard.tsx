import { KpiCards } from "@/components/dashboard/kpi-cards"
import { MemberTrendChart } from "@/components/dashboard/member-trend-chart"
import { RecentActivity } from "@/components/dashboard/recent-activity"

export function DashboardPage() {
  return (
    <div className="space-y-6">
      <KpiCards />
      <div className="grid gap-6 lg:grid-cols-2">
        <MemberTrendChart />
        <RecentActivity />
      </div>
    </div>
  )
}
