import { useState, useEffect, useCallback } from "react"
import { Plus, Pencil, Trash2, Search, Eye } from "lucide-react"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import api from "@/lib/api"
import type { Protokoll, ProtokollListResponse, ProtokollTyp } from "@/types/dokumente"
import { PROTOKOLL_TYP_LABELS } from "@/types/dokumente"
import { ProtokollDialog } from "./protokoll-dialog"
import { ProtokollDetailDialog } from "./protokoll-detail-dialog"

const TYP_BADGE_VARIANT: Record<string, "default" | "secondary" | "outline" | "destructive"> = {
  vorstandssitzung: "default",
  mitgliederversammlung: "destructive",
  abteilungssitzung: "secondary",
  sonstige: "outline",
}

export function ProtokollList() {
  const [protokolle, setProtokolle] = useState<Protokoll[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState("")
  const [typFilter, setTypFilter] = useState<string>("all")
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<Protokoll | null>(null)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [deleting, setDeleting] = useState<Protokoll | null>(null)
  const [detailDialogOpen, setDetailDialogOpen] = useState(false)
  const [viewing, setViewing] = useState<Protokoll | null>(null)

  const pageSize = 15

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      params.set("page", String(page))
      params.set("page_size", String(pageSize))
      if (search) params.set("search", search)
      if (typFilter && typFilter !== "all") params.set("typ", typFilter)

      const data = await api.get<ProtokollListResponse>(
        `/api/dokumente/protokolle?${params.toString()}`
      )
      setProtokolle(data.items)
      setTotal(data.total)
    } catch {
      setProtokolle([])
      setTotal(0)
    } finally {
      setLoading(false)
    }
  }, [page, search, typFilter])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  // Reset to page 1 when filters change
  useEffect(() => {
    setPage(1)
  }, [search, typFilter])

  function openCreate() {
    setEditing(null)
    setDialogOpen(true)
  }

  function openEdit(protokoll: Protokoll) {
    setEditing(protokoll)
    setDialogOpen(true)
  }

  function openDelete(protokoll: Protokoll) {
    setDeleting(protokoll)
    setDeleteDialogOpen(true)
  }

  function openDetail(protokoll: Protokoll) {
    setViewing(protokoll)
    setDetailDialogOpen(true)
  }

  async function handleDelete() {
    if (!deleting) return
    try {
      await api.delete(`/api/dokumente/protokolle/${deleting.id}`)
    } catch {
      // silent
    }
    setDeleteDialogOpen(false)
    setDeleting(null)
    fetchData()
  }

  function formatDate(dateStr: string): string {
    try {
      return new Date(dateStr).toLocaleDateString("de-DE", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
      })
    } catch {
      return dateStr
    }
  }

  const totalPages = Math.ceil(total / pageSize)

  return (
    <>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
          <div className="space-y-1">
            <CardTitle>Protokolle</CardTitle>
            <CardDescription>
              Sitzungsprotokolle und Niederschriften des Vereins.
            </CardDescription>
          </div>
          <Button onClick={openCreate} size="sm">
            <Plus className="mr-2 h-4 w-4" />
            Neues Protokoll
          </Button>
        </CardHeader>
        <CardContent>
          {/* Filters */}
          <div className="mb-4 flex gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Suche nach Titel oder Inhalt..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>
            <Select value={typFilter} onValueChange={setTypFilter}>
              <SelectTrigger className="w-[220px]">
                <SelectValue placeholder="Alle Typen" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Alle Typen</SelectItem>
                {(
                  Object.entries(PROTOKOLL_TYP_LABELS) as [ProtokollTyp, string][]
                ).map(([value, label]) => (
                  <SelectItem key={value} value={value}>
                    {label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Table */}
          {loading ? (
            <p className="text-sm text-muted-foreground">Laden...</p>
          ) : protokolle.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Keine Protokolle vorhanden.{" "}
              {search || typFilter !== "all"
                ? "Passen Sie die Filter an."
                : "Erstellen Sie das erste Protokoll."}
            </p>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Datum</TableHead>
                    <TableHead>Titel</TableHead>
                    <TableHead>Typ</TableHead>
                    <TableHead>Erstellt von</TableHead>
                    <TableHead className="text-right">Aktionen</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {protokolle.map((p) => (
                    <TableRow key={p.id}>
                      <TableCell>{formatDate(p.datum)}</TableCell>
                      <TableCell className="font-medium">{p.titel}</TableCell>
                      <TableCell>
                        <Badge variant={TYP_BADGE_VARIANT[p.typ] ?? "outline"}>
                          {PROTOKOLL_TYP_LABELS[p.typ as ProtokollTyp] ?? p.typ}
                        </Badge>
                      </TableCell>
                      <TableCell>{p.erstellt_von ?? "---"}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => openDetail(p)}
                            aria-label={`${p.titel} ansehen`}
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => openEdit(p)}
                            aria-label={`${p.titel} bearbeiten`}
                          >
                            <Pencil className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => openDelete(p)}
                            aria-label={`${p.titel} löschen`}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="mt-4 flex items-center justify-between">
                  <p className="text-sm text-muted-foreground">
                    {total} Protokoll{total !== 1 ? "e" : ""} gesamt
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={page <= 1}
                      onClick={() => setPage(page - 1)}
                    >
                      Zurück
                    </Button>
                    <span className="flex items-center text-sm text-muted-foreground">
                      Seite {page} von {totalPages}
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={page >= totalPages}
                      onClick={() => setPage(page + 1)}
                    >
                      Weiter
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* Create/Edit Dialog */}
      <ProtokollDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        protokoll={editing}
        onSaved={fetchData}
      />

      {/* Detail View Dialog */}
      <ProtokollDetailDialog
        open={detailDialogOpen}
        onOpenChange={setDetailDialogOpen}
        protokoll={viewing}
      />

      {/* Delete Confirmation */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Protokoll löschen</DialogTitle>
            <DialogDescription>
              Möchten Sie das Protokoll &quot;{deleting?.titel}&quot; wirklich
              löschen? Diese Aktion kann nicht rückgängig gemacht werden.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeleteDialogOpen(false)}
            >
              Abbrechen
            </Button>
            <Button variant="destructive" onClick={handleDelete}>
              Löschen
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
