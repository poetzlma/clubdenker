import { TokenManagement } from "@/components/admin/token-management"

export function AdminPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Administration</h1>
        <p className="text-muted-foreground">
          Verwalten Sie die Systemeinstellungen und API-Tokens.
        </p>
      </div>

      <TokenManagement />
    </div>
  )
}
