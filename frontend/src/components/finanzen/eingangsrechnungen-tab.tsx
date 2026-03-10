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
import type { Eingangsrechnung, EingangsrechnungStatus } from "@/types/finance"
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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { EINGANGSRECHNUNG_STATUS_COLORS } from "@/constants/design"
import { cn } from "@/lib/utils"
import {
  ArrowUpDown,
  ChevronLeft,
  ChevronRight,
  MoreHorizontal,
} from "lucide-react"

const API_BASE = "/api"

function formatEuro(amount: number): string {
  return amount.toLocaleString("de-DE", {
    style: "currency",
    currency: "EUR",
  })
}

function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return "--"
  const date = new Date(dateStr)
  const day = String(date.getDate()).padStart(2, "0")
  const month = String(date.getMonth() + 1).padStart(2, "0")
  const year = date.getFullYear()
  return `${day}.${month}.${year}`
}

/** Valid next statuses for each current status */
const STATUS_TRANSITIONS: Record<EingangsrechnungStatus, EingangsrechnungStatus[]> = {
  eingegangen: ["geprueft", "abgelehnt"],
  geprueft: ["freigegeben", "abgelehnt"],
  freigegeben: ["bezahlt"],
  bezahlt: [],
  abgelehnt: [],
}

function EingangsrechnungStatusBadge({ status }: { status: string }) {
  const config =
    EINGANGSRECHNUNG_STATUS_COLORS[status as keyof typeof EINGANGSRECHNUNG_STATUS_COLORS]
  if (!config) return <span className="text-xs">{status}</span>
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
        config.bg,
        config.text
      )}
    >
      {config.label}
    </span>
  )
}

export function EingangsrechnungenTab() {
  const [invoices, setInvoices] = useState<Eingangsrechnung[]>([])
  const [loading, setLoading] = useState(true)
  const [sorting, setSorting] = useState<SortingState>([])
  const [pagination, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: 10,
  })
  const [statusFilter, setStatusFilter] = useState<string>("alle")
  const [searchTerm, setSearchTerm] = useState("")

  const fetchInvoices = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (statusFilter && statusFilter !== "alle") {
        params.set("status", statusFilter)
      }
      const url = `${API_BASE}/finanzen/eingangsrechnungen${params.toString() ? `?${params}` : ""}`
      const res = await fetch(url)
      if (!res.ok) throw new Error("API error")
      const data = await res.json()
      const items: Eingangsrechnung[] = data.items ?? data
      setInvoices(items)
    } catch {
      setInvoices([])
    } finally {
      setLoading(false)
    }
  }, [statusFilter])

  useEffect(() => {
    fetchInvoices()
  }, [fetchInvoices])

  async function handleStatusChange(
    invoice: Eingangsrechnung,
    newStatus: EingangsrechnungStatus
  ) {
    try {
      const res = await fetch(
        `${API_BASE}/finanzen/eingangsrechnungen/${invoice.id}/status`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ status: newStatus }),
        }
      )
      if (res.ok) {
        // Update locally on success
        setInvoices((prev) =>
          prev.map((r) =>
            r.id === invoice.id ? { ...r, status: newStatus } : r
          )
        )
      }
    } catch {
      // Optimistic fallback
      setInvoices((prev) =>
        prev.map((r) =>
          r.id === invoice.id ? { ...r, status: newStatus } : r
        )
      )
    }
  }

  const columns = useMemo<ColumnDef<Eingangsrechnung>[]>(
    () => [
      {
        accessorKey: "rechnungsnummer",
        header: ({ column }) => (
          <button
            className="flex items-center gap-1 hover:text-foreground"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          >
            Nummer
            <ArrowUpDown className="h-4 w-4" />
          </button>
        ),
        cell: ({ getValue }) => (
          <span className="font-medium text-sm">{getValue<string>()}</span>
        ),
      },
      {
        accessorKey: "aussteller_name",
        header: ({ column }) => (
          <button
            className="flex items-center gap-1 hover:text-foreground"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          >
            Lieferant
            <ArrowUpDown className="h-4 w-4" />
          </button>
        ),
        cell: ({ getValue }) => (
          <span className="text-sm">{getValue<string>()}</span>
        ),
      },
      {
        id: "betrag",
        header: ({ column }) => (
          <button
            className="flex items-center gap-1 hover:text-foreground"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          >
            Betrag
            <ArrowUpDown className="h-4 w-4" />
          </button>
        ),
        accessorFn: (row) => row.summe_brutto,
        cell: ({ row }) => (
          <div className="text-right">
            <div className="text-xs text-muted-foreground tabular-nums">
              {formatEuro(row.original.summe_netto)} netto
            </div>
            <div className="font-medium tabular-nums">
              {formatEuro(row.original.summe_brutto)}
            </div>
          </div>
        ),
      },
      {
        accessorKey: "rechnungsdatum",
        header: ({ column }) => (
          <button
            className="flex items-center gap-1 hover:text-foreground"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          >
            Datum
            <ArrowUpDown className="h-4 w-4" />
          </button>
        ),
        cell: ({ getValue }) => (
          <span className="text-sm">{formatDate(getValue<string>())}</span>
        ),
      },
      {
        accessorKey: "faelligkeitsdatum",
        header: ({ column }) => (
          <button
            className="flex items-center gap-1 hover:text-foreground"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          >
            Faellig am
            <ArrowUpDown className="h-4 w-4" />
          </button>
        ),
        cell: ({ getValue }) => (
          <span className="text-sm">{formatDate(getValue<string>())}</span>
        ),
      },
      {
        accessorKey: "status",
        header: "Status",
        cell: ({ getValue }) => (
          <EingangsrechnungStatusBadge status={getValue<string>()} />
        ),
      },
      {
        id: "aktionen",
        header: "Aktionen",
        enableSorting: false,
        cell: ({ row }) => {
          const invoice = row.original
          const transitions =
            STATUS_TRANSITIONS[invoice.status] ?? []
          if (transitions.length === 0) return null

          return (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                  <MoreHorizontal className="h-4 w-4" />
                  <span className="sr-only">Aktionen</span>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuLabel>Status aendern</DropdownMenuLabel>
                <DropdownMenuSeparator />
                {transitions.map((nextStatus) => {
                  const label =
                    EINGANGSRECHNUNG_STATUS_COLORS[nextStatus]?.label ?? nextStatus
                  const isReject = nextStatus === "abgelehnt"
                  return (
                    <DropdownMenuItem
                      key={nextStatus}
                      className={isReject ? "text-red-600 focus:text-red-600" : ""}
                      onClick={() => handleStatusChange(invoice, nextStatus)}
                    >
                      {label}
                    </DropdownMenuItem>
                  )
                })}
              </DropdownMenuContent>
            </DropdownMenu>
          )
        },
      },
    ],
    []
  )

  const filteredData = useMemo(() => {
    let data = invoices
    if (searchTerm) {
      const term = searchTerm.toLowerCase()
      data = data.filter(
        (r) =>
          r.aussteller_name.toLowerCase().includes(term) ||
          r.rechnungsnummer.toLowerCase().includes(term)
      )
    }
    return data
  }, [invoices, searchTerm])

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
      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-44" data-testid="eingangsrechnung-status-filter">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="alle">Alle Status</SelectItem>
            {Object.entries(EINGANGSRECHNUNG_STATUS_COLORS).map(([key, config]) => (
              <SelectItem key={key} value={key}>
                {config.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Input
          className="w-48"
          placeholder="Suche nach Lieferant / Nr..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
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
                <TableRow key={row.id} data-testid="eingangsrechnung-row">
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
                  Keine Eingangsrechnungen gefunden.
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
    </div>
  )
}
