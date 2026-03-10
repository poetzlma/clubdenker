import { useState, useEffect, useCallback } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { ChevronLeft, ChevronRight } from "lucide-react"
import { cn } from "@/lib/utils"
import type { AuditLogEntry } from "@/types/audit"

const API_BASE = "/api"
const PAGE_SIZE = 20

const mockAuditEntries: AuditLogEntry[] = [
  {
    id: 1,
    user_id: 1,
    action: "create",
    entity_type: "mitglied",
    entity_id: 47,
    details: "Weber, Thomas angelegt",
    ip_address: "192.168.1.10",
    created_at: "2026-03-10T14:23:00Z",
  },
  {
    id: 2,
    user_id: 1,
    action: "update",
    entity_type: "buchung",
    entity_id: 42,
    details: "Buchung #42 geändert",
    ip_address: "192.168.1.10",
    created_at: "2026-03-10T13:15:00Z",
  },
  {
    id: 3,
    user_id: 1,
    action: "delete",
    entity_type: "rechnung",
    entity_id: 12,
    details: "R-2025-012 storniert",
    ip_address: "192.168.1.10",
    created_at: "2026-03-10T11:30:00Z",
  },
  {
    id: 4,
    user_id: 1,
    action: "create",
    entity_type: "beitragslauf",
    entity_id: 5,
    details: "23 Rechnungen generiert",
    ip_address: "192.168.1.10",
    created_at: "2026-03-09T16:45:00Z",
  },
  {
    id: 5,
    user_id: 1,
    action: "update",
    entity_type: "mitglied",
    entity_id: 12,
    details: "Fischer, Maria - Adresse aktualisiert",
    ip_address: "192.168.1.10",
    created_at: "2026-03-09T14:20:00Z",
  },
  {
    id: 6,
    user_id: 1,
    action: "create",
    entity_type: "buchung",
    entity_id: 108,
    details: "Buchung #108 - Hallenmiete März",
    ip_address: "192.168.1.10",
    created_at: "2026-03-09T10:05:00Z",
  },
  {
    id: 7,
    user_id: 1,
    action: "update",
    entity_type: "rechnung",
    entity_id: 8,
    details: "R-2026-008 als bezahlt markiert",
    ip_address: "192.168.1.10",
    created_at: "2026-03-08T15:30:00Z",
  },
  {
    id: 8,
    user_id: 1,
    action: "create",
    entity_type: "mitglied",
    entity_id: 48,
    details: "Klein, Sabine angelegt",
    ip_address: "192.168.1.10",
    created_at: "2026-03-08T11:00:00Z",
  },
  {
    id: 9,
    user_id: 1,
    action: "delete",
    entity_type: "buchung",
    entity_id: 95,
    details: "Buchung #95 gelöscht (Fehlbuchung)",
    ip_address: "192.168.1.10",
    created_at: "2026-03-07T16:15:00Z",
  },
  {
    id: 10,
    user_id: 1,
    action: "create",
    entity_type: "rechnung",
    entity_id: 15,
    details: "R-2026-015 erstellt für Becker, Stefan",
    ip_address: "192.168.1.10",
    created_at: "2026-03-07T09:45:00Z",
  },
]

function formatDateTime(dateStr: string): string {
  const date = new Date(dateStr)
  const day = String(date.getDate()).padStart(2, "0")
  const month = String(date.getMonth() + 1).padStart(2, "0")
  const year = date.getFullYear()
  const hours = String(date.getHours()).padStart(2, "0")
  const minutes = String(date.getMinutes()).padStart(2, "0")
  return `${day}.${month}.${year} ${hours}:${minutes}`
}

const ACTION_CONFIG: Record<string, { label: string; className: string }> = {
  create: {
    label: "Erstellt",
    className: "bg-emerald-50 text-emerald-700 border-emerald-200",
  },
  update: {
    label: "Aktualisiert",
    className: "bg-blue-50 text-blue-700 border-blue-200",
  },
  delete: {
    label: "Gelöscht",
    className: "bg-red-50 text-red-700 border-red-200",
  },
}

const ENTITY_LABELS: Record<string, string> = {
  mitglied: "Mitglied",
  buchung: "Buchung",
  rechnung: "Rechnung",
  beitragslauf: "Beitragslauf",
  token: "Token",
}

const ALL_ACTIONS = "alle"
const ALL_ENTITY_TYPES = "alle"

export function AuditLogViewer() {
  const [entries, setEntries] = useState<AuditLogEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [totalEntries, setTotalEntries] = useState(0)
  const [actionFilter, setActionFilter] = useState(ALL_ACTIONS)
  const [entityFilter, setEntityFilter] = useState(ALL_ENTITY_TYPES)
  const [expandedId, setExpandedId] = useState<number | null>(null)

  const fetchEntries = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({
        skip: String((page - 1) * PAGE_SIZE),
        limit: String(PAGE_SIZE),
      })
      if (actionFilter !== ALL_ACTIONS) {
        params.set("action", actionFilter)
      }
      if (entityFilter !== ALL_ENTITY_TYPES) {
        params.set("entity_type", entityFilter)
      }
      const res = await fetch(`${API_BASE}/audit/?${params.toString()}`)
      if (!res.ok) throw new Error("API error")
      const data = await res.json()
      const items: AuditLogEntry[] = data.items ?? data
      setEntries(items)
      setTotalEntries(data.total ?? items.length)
    } catch {
      // Use mock data with client-side filtering
      let filtered = mockAuditEntries
      if (actionFilter !== ALL_ACTIONS) {
        filtered = filtered.filter((e) => e.action === actionFilter)
      }
      if (entityFilter !== ALL_ENTITY_TYPES) {
        filtered = filtered.filter((e) => e.entity_type === entityFilter)
      }
      setTotalEntries(filtered.length)
      const start = (page - 1) * PAGE_SIZE
      setEntries(filtered.slice(start, start + PAGE_SIZE))
    } finally {
      setLoading(false)
    }
  }, [page, actionFilter, entityFilter])

  useEffect(() => {
    fetchEntries()
  }, [fetchEntries])

  // Reset page when filters change
  useEffect(() => {
    setPage(1)
  }, [actionFilter, entityFilter])

  const totalPages = Math.max(1, Math.ceil(totalEntries / PAGE_SIZE))

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <CardTitle>Protokoll</CardTitle>
          <div className="flex gap-2">
            <Select value={actionFilter} onValueChange={setActionFilter}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="Aktion" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL_ACTIONS}>Alle Aktionen</SelectItem>
                <SelectItem value="create">Erstellt</SelectItem>
                <SelectItem value="update">Aktualisiert</SelectItem>
                <SelectItem value="delete">Gelöscht</SelectItem>
              </SelectContent>
            </Select>
            <Select value={entityFilter} onValueChange={setEntityFilter}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="Bereich" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL_ENTITY_TYPES}>Alle Bereiche</SelectItem>
                <SelectItem value="mitglied">Mitglied</SelectItem>
                <SelectItem value="buchung">Buchung</SelectItem>
                <SelectItem value="rechnung">Rechnung</SelectItem>
                <SelectItem value="beitragslauf">Beitragslauf</SelectItem>
                <SelectItem value="token">Token</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="flex h-32 items-center justify-center">
            <p className="text-muted-foreground">Laden...</p>
          </div>
        ) : entries.length === 0 ? (
          <div className="flex h-32 items-center justify-center">
            <p className="text-muted-foreground">
              Keine Einträge gefunden.
            </p>
          </div>
        ) : (
          <>
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Zeitpunkt</TableHead>
                    <TableHead>Benutzer</TableHead>
                    <TableHead>Aktion</TableHead>
                    <TableHead>Bereich</TableHead>
                    <TableHead>Details</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {entries.map((entry) => {
                    const actionCfg = ACTION_CONFIG[entry.action] ?? {
                      label: entry.action,
                      className: "bg-gray-50 text-gray-700 border-gray-200",
                    }
                    const entityLabel =
                      ENTITY_LABELS[entry.entity_type] ?? entry.entity_type
                    const isExpanded = expandedId === entry.id
                    const detailsText = entry.details ?? ""
                    const isTruncated = detailsText.length > 40

                    return (
                      <TableRow key={entry.id}>
                        <TableCell className="whitespace-nowrap tabular-nums text-sm">
                          {formatDateTime(entry.created_at)}
                        </TableCell>
                        <TableCell className="text-sm">
                          {entry.user_id ? `Admin` : "System"}
                        </TableCell>
                        <TableCell>
                          <Badge
                            variant="outline"
                            className={cn(actionCfg.className)}
                          >
                            {actionCfg.label}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-sm">
                          {entityLabel}
                        </TableCell>
                        <TableCell className="max-w-[300px] text-sm">
                          {isTruncated && !isExpanded ? (
                            <button
                              className="text-left hover:underline"
                              onClick={() => setExpandedId(entry.id)}
                            >
                              {detailsText.slice(0, 40)}...
                            </button>
                          ) : (
                            <span
                              className={cn(
                                isTruncated && "cursor-pointer hover:underline"
                              )}
                              onClick={() =>
                                isTruncated && setExpandedId(null)
                              }
                            >
                              {detailsText || "—"}
                            </span>
                          )}
                        </TableCell>
                      </TableRow>
                    )
                  })}
                </TableBody>
              </Table>
            </div>

            {/* Pagination */}
            <div className="flex items-center justify-between pt-4">
              <p className="text-sm text-muted-foreground">
                {totalEntries} Einträge gesamt
              </p>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page <= 1}
                >
                  <ChevronLeft className="h-4 w-4" />
                </Button>
                <span className="text-sm tabular-nums">
                  Seite {page} von {totalPages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages}
                >
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  )
}
