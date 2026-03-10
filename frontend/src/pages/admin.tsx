import { TokenManagement } from "@/components/admin/token-management"
import { AgentDashboard } from "@/components/admin/agent-dashboard"
import { AuditLogViewer } from "@/components/admin/audit-log-viewer"
import { PageHeader } from "@/components/dashboard/page-header"

export function AdminPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Administration"
        description="Verwalten Sie die Systemeinstellungen und API-Tokens."
      />

      <TokenManagement />
      <AgentDashboard />
      <AuditLogViewer />
    </div>
  )
}
