import { useState, useMemo, useEffect, useCallback } from "react"
import {
  type ColumnDef,
  type SortingState,
  type PaginationState,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  getPaginationRowModel,
  useReactTable,
} from "@tanstack/react-table"
import type { SepaMandat } from "@/types/finance"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { MandateDialog } from "@/components/finanzen/mandate-dialog"
import { ArrowUpDown, ChevronLeft, ChevronRight, Plus, Pencil, Ban } from "lucide-react"

const API_BASE = "/api"

function maskIban(iban: string): string {
  if (iban.length <= 4) return iban
  return "****" + iban.slice(-4)
}

function formatDate(dateStr: string): string {
  if (!dateStr) return ""
  const d = new Date(dateStr)
  const day = String(d.getDate()).padStart(2, "0")
  const month = String(d.getMonth() + 1).padStart(2, "0")
  const year = d.getFullYear()
  return `${day}.${month}.${year}`
}

export function SepaMandateTab() {
  const [mandate, setMandate] = useState<SepaMandat[]>([])
  const [loading, setLoading] = useState(true)
  const [sorting, setSorting] = useState<SortingState>([])
  const [pagination, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: 10,
  })
  const [statusFilter, setStatusFilter] = useState<string>("alle")
  const [searchTerm, setSearchTerm] = useState("")
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editMandat, setEditMandat] = useState<SepaMandat | null>(null)

  const fetchMandate = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (statusFilter === "aktiv") params.set("aktiv", "true")
      else if (statusFilter === "inaktiv") params.set("aktiv", "false")

      const res = await fetch(`${API_BASE}/finanzen/mandate?${params.toString()}`)
      if (!res.ok) throw new Error("API error")
      const data = await res.json()
      setMandate(data.items ?? data)
    } catch {
      setMandate([])
    } finally {
      setLoading(false)
    }
  }, [statusFilter])

  useEffect(() => {
    fetchMandate()
  }, [fetchMandate])

  async function handleDeactivate(mandat: SepaMandat) {
    try {
      const res = await fetch(`${API_BASE}/finanzen/mandate/${mandat.id}`, {
        method: "DELETE",
      })
      if (!res.ok) throw new Error("API error")
    } catch {
      // optimistic update
    }
    setMandate((prev) =>
      prev.map((m) => (m.id === mandat.id ? { ...m, aktiv: false } : m))
    )
  }

  function handleEdit(mandat: SepaMandat) {
    setEditMandat(mandat)
    setDialogOpen(true)
  }

  function handleDialogClose(open: boolean) {
    setDialogOpen(open)
    if (!open) setEditMandat(null)
  }

  const columns = useMemo<ColumnDef<SepaMandat>[]>(
    () => [
      {
        accessorKey: "mitglied_name",
        header: ({ column }) => (
          <button
            className="flex items-center gap-1 hover:text-foreground"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          >
            Mitglied
            <ArrowUpDown className="h-4 w-4" />
          </button>
        ),
        cell: ({ row }) =>
          row.original.mitglied_name ?? `Mitglied #${row.original.mitglied_id}`,
      },
      {
        accessorKey: "iban",
        header: "IBAN",
        cell: ({ getValue }) => (
          <span className="font-mono text-sm">{maskIban(getValue<string>())}</span>
        ),
      },
      {
        accessorKey: "bic",
        header: "BIC",
        cell: ({ getValue }) => (
          <span className="font-mono text-sm">{getValue<string>() ?? "-"}</span>
        ),
      },
      {
        accessorKey: "kontoinhaber",
        header: ({ column }) => (
          <button
            className="flex items-center gap-1 hover:text-foreground"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          >
            Kontoinhaber
            <ArrowUpDown className="h-4 w-4" />
          </button>
        ),
      },
      {
        accessorKey: "mandatsreferenz",
        header: "Mandatsreferenz",
        cell: ({ getValue }) => (
          <span className="font-mono text-sm">{getValue<string>()}</span>
        ),
      },
      {
        accessorKey: "unterschriftsdatum",
        header: ({ column }) => (
          <button
            className="flex items-center gap-1 hover:text-foreground"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          >
            Unterschrift
            <ArrowUpDown className="h-4 w-4" />
          </button>
        ),
        cell: ({ getValue }) => formatDate(getValue<string>()),
      },
      {
        accessorKey: "gueltig_ab",
        header: "Gueltig ab",
        cell: ({ getValue }) => formatDate(getValue<string>()),
      },
      {
        accessorKey: "gueltig_bis",
        header: "Gueltig bis",
        cell: ({ getValue }) => {
          const val = getValue<string | null>()
          return val ? formatDate(val) : "-"
        },
      },
      {
        accessorKey: "aktiv",
        header: "Status",
        cell: ({ getValue }) => {
          const aktiv = getValue<boolean>()
          return aktiv ? (
            <Badge className="bg-emerald-100 text-emerald-700 hover:bg-emerald-100">Aktiv</Badge>
          ) : (
            <Badge variant="secondary" className="bg-gray-100 text-gray-500 hover:bg-gray-100">Inaktiv</Badge>
          )
        },
      },
      {
        id: "aktionen",
        header: "Aktionen",
        enableSorting: false,
        cell: ({ row }) => {
          const m = row.original
          return (
            <div className="flex gap-1">
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleEdit(m)}
                disabled={!m.aktiv}
              >
                <Pencil className="h-3 w-3" />
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleDeactivate(m)}
                disabled={!m.aktiv}
              >
                <Ban className="h-3 w-3" />
              </Button>
            </div>
          )
        },
      },
    ],
    []
  )

  const filteredData = useMemo(() => {
    let data = mandate
    if (searchTerm) {
      const term = searchTerm.toLowerCase()
      data = data.filter(
        (m) =>
          (m.mitglied_name ?? "").toLowerCase().includes(term) ||
          m.mandatsreferenz.toLowerCase().includes(term) ||
          m.kontoinhaber.toLowerCase().includes(term)
      )
    }
    return data
  }, [mandate, searchTerm])

  const table = useReactTable({
    data: filteredData,
    columns,
    state: { sorting, pagination },
    onSortingChange: setSorting,
    onPaginationChange: setPagination,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
  })

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <p className="text-muted-foreground">Laden...</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Filters + New Mandate button */}
      <div className="flex flex-wrap items-center gap-4">
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-44" data-testid="mandate-status-filter">
            <SelectValue placeholder="Status filtern" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="alle">Alle</SelectItem>
            <SelectItem value="aktiv">Aktiv</SelectItem>
            <SelectItem value="inaktiv">Inaktiv</SelectItem>
          </SelectContent>
        </Select>
        <Input
          className="w-64"
          placeholder="Mitglied / Referenz suchen..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
        <div className="ml-auto">
          <Button onClick={() => { setEditMandat(null); setDialogOpen(true) }}>
            <Plus className="h-4 w-4" />
            Neues Mandat
          </Button>
        </div>
      </div>

      {/* Table */}
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <TableHead key={header.id}>
                    {header.isPlaceholder
                      ? null
                      : flexRender(header.column.columnDef.header, header.getContext())}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows?.length ? (
              table.getRowModel().rows.map((row) => (
                <TableRow key={row.id} data-testid="mandate-row">
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={columns.length} className="h-24 text-center">
                  Keine SEPA-Mandate gefunden.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between px-2">
        <p className="text-sm text-muted-foreground">
          Seite {table.getState().pagination.pageIndex + 1} von{" "}
          {table.getPageCount() || 1} ({filteredData.length} Eintraege)
        </p>
        <div className="flex items-center gap-2">
          <button
            className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-input bg-transparent text-sm font-medium shadow-sm hover:bg-accent hover:text-accent-foreground disabled:pointer-events-none disabled:opacity-50"
            onClick={() => table.previousPage()}
            disabled={!table.getCanPreviousPage()}
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <button
            className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-input bg-transparent text-sm font-medium shadow-sm hover:bg-accent hover:text-accent-foreground disabled:pointer-events-none disabled:opacity-50"
            onClick={() => table.nextPage()}
            disabled={!table.getCanNextPage()}
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Mandate Dialog */}
      <MandateDialog
        open={dialogOpen}
        onOpenChange={handleDialogClose}
        onSuccess={fetchMandate}
        editMandat={editMandat}
      />
    </div>
  )
}
