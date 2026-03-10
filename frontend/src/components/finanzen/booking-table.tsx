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
import type { Buchung } from "@/types/finance"
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
import { cn } from "@/lib/utils"
import { ArrowUpDown, ChevronLeft, ChevronRight } from "lucide-react"

const API_BASE = "/api"

function formatEuro(amount: number): string {
  return amount.toLocaleString("de-DE", {
    style: "currency",
    currency: "EUR",
  })
}

function formatDate(dateStr: string): string {
  if (!dateStr) return ""
  const date = new Date(dateStr)
  const day = String(date.getDate()).padStart(2, "0")
  const month = String(date.getMonth() + 1).padStart(2, "0")
  const year = date.getFullYear()
  return `${day}.${month}.${year}`
}

const sphereConfig: Record<
  Buchung["sphare"],
  { label: string; className: string }
> = {
  ideell: { label: "Ideell", className: "bg-blue-100 text-blue-800" },
  zweckbetrieb: {
    label: "Zweckbetrieb",
    className: "bg-green-100 text-green-800",
  },
  vermoegensverwaltung: {
    label: "Vermögensverwaltung",
    className: "bg-yellow-100 text-yellow-800",
  },
  wirtschaftlich: {
    label: "Wirtschaftlich",
    className: "bg-purple-100 text-purple-800",
  },
}

const mockBuchungen: Buchung[] = [
  {
    id: 1,
    buchungsdatum: "2025-01-15",
    betrag: 120.0,
    beschreibung: "Mitgliedsbeitrag Max Mustermann",
    konto: "1200",
    gegenkonto: "8100",
    sphare: "ideell",
    mitglied_id: 1,
    created_at: "2025-01-15T10:00:00Z",
  },
  {
    id: 2,
    buchungsdatum: "2025-01-20",
    betrag: 500.0,
    beschreibung: "Hallenmiete Einnahmen",
    konto: "1200",
    gegenkonto: "8200",
    sphare: "vermoegensverwaltung",
    mitglied_id: null,
    created_at: "2025-01-20T10:00:00Z",
  },
  {
    id: 3,
    buchungsdatum: "2025-02-01",
    betrag: -250.0,
    beschreibung: "Sportgeräte Einkauf",
    konto: "4800",
    gegenkonto: "1200",
    sphare: "zweckbetrieb",
    mitglied_id: null,
    created_at: "2025-02-01T10:00:00Z",
  },
  {
    id: 4,
    buchungsdatum: "2025-02-10",
    betrag: 1500.0,
    beschreibung: "Sponsoring Vereinsfest",
    konto: "1200",
    gegenkonto: "8400",
    sphare: "wirtschaftlich",
    mitglied_id: null,
    created_at: "2025-02-10T10:00:00Z",
  },
  {
    id: 5,
    buchungsdatum: "2025-02-15",
    betrag: 120.0,
    beschreibung: "Mitgliedsbeitrag Anna Schmidt",
    konto: "1200",
    gegenkonto: "8100",
    sphare: "ideell",
    mitglied_id: 2,
    created_at: "2025-02-15T10:00:00Z",
  },
  {
    id: 6,
    buchungsdatum: "2025-03-01",
    betrag: -800.0,
    beschreibung: "Trainerhonorar März",
    konto: "4100",
    gegenkonto: "1200",
    sphare: "zweckbetrieb",
    mitglied_id: null,
    created_at: "2025-03-01T10:00:00Z",
  },
  {
    id: 7,
    buchungsdatum: "2025-03-05",
    betrag: 60.0,
    beschreibung: "Mitgliedsbeitrag Jugend Tom Klein",
    konto: "1200",
    gegenkonto: "8100",
    sphare: "ideell",
    mitglied_id: 3,
    created_at: "2025-03-05T10:00:00Z",
  },
  {
    id: 8,
    buchungsdatum: "2025-03-10",
    betrag: -150.0,
    beschreibung: "Versicherung Vereinsheim",
    konto: "4500",
    gegenkonto: "1200",
    sphare: "vermoegensverwaltung",
    mitglied_id: null,
    created_at: "2025-03-10T10:00:00Z",
  },
]

export function BookingTable() {
  const [buchungen, setBuchungen] = useState<Buchung[]>([])
  const [loading, setLoading] = useState(true)
  const [sorting, setSorting] = useState<SortingState>([])
  const [pagination, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: 10,
  })
  const [sphereFilter, setSphereFilter] = useState<string>("alle")

  const fetchBuchungen = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/bookings`)
      if (!res.ok) throw new Error("API error")
      const data = await res.json()
      setBuchungen(data.items ?? data)
    } catch {
      setBuchungen(mockBuchungen)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchBuchungen()
  }, [fetchBuchungen])

  const columns = useMemo<ColumnDef<Buchung>[]>(
    () => [
      {
        accessorKey: "buchungsdatum",
        header: ({ column }) => (
          <button
            className="flex items-center gap-1 hover:text-foreground"
            onClick={() =>
              column.toggleSorting(column.getIsSorted() === "asc")
            }
          >
            Datum
            <ArrowUpDown className="h-4 w-4" />
          </button>
        ),
        cell: ({ getValue }) => formatDate(getValue<string>()),
      },
      {
        accessorKey: "betrag",
        header: ({ column }) => (
          <button
            className="flex items-center gap-1 hover:text-foreground"
            onClick={() =>
              column.toggleSorting(column.getIsSorted() === "asc")
            }
          >
            Betrag
            <ArrowUpDown className="h-4 w-4" />
          </button>
        ),
        cell: ({ getValue }) => {
          const amount = getValue<number>()
          return (
            <span
              className={cn(
                "font-medium",
                amount >= 0 ? "text-green-700" : "text-red-700"
              )}
            >
              {formatEuro(amount)}
            </span>
          )
        },
      },
      {
        accessorKey: "beschreibung",
        header: "Beschreibung",
        enableSorting: false,
      },
      {
        accessorKey: "konto",
        header: "Konto",
      },
      {
        accessorKey: "gegenkonto",
        header: "Gegenkonto",
      },
      {
        accessorKey: "sphare",
        header: "Sphäre",
        cell: ({ getValue }) => {
          const sphare = getValue<Buchung["sphare"]>()
          const config = sphereConfig[sphare]
          return (
            <span
              className={cn(
                "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
                config.className
              )}
            >
              {config.label}
            </span>
          )
        },
      },
    ],
    []
  )

  const filteredData = useMemo(() => {
    if (!sphereFilter || sphereFilter === "alle") return buchungen
    return buchungen.filter((b) => b.sphare === sphereFilter)
  }, [buchungen, sphereFilter])

  const table = useReactTable({
    data: filteredData,
    columns,
    state: {
      sorting,
      pagination,
    },
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
      {/* Filter */}
      <div className="flex flex-wrap items-center gap-4">
        <Select value={sphereFilter} onValueChange={setSphereFilter}>
          <SelectTrigger className="w-52" data-testid="sphere-filter">
            <SelectValue placeholder="Sphäre filtern" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="alle">Alle Sphären</SelectItem>
            <SelectItem value="ideell">Ideell</SelectItem>
            <SelectItem value="zweckbetrieb">Zweckbetrieb</SelectItem>
            <SelectItem value="vermoegensverwaltung">
              Vermögensverwaltung
            </SelectItem>
            <SelectItem value="wirtschaftlich">Wirtschaftlich</SelectItem>
          </SelectContent>
        </Select>
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
                      : flexRender(
                          header.column.columnDef.header,
                          header.getContext()
                        )}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows?.length ? (
              table.getRowModel().rows.map((row) => (
                <TableRow key={row.id} data-testid="booking-row">
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext()
                      )}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell
                  colSpan={columns.length}
                  className="h-24 text-center"
                >
                  Keine Buchungen gefunden.
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
          {table.getPageCount() || 1} ({filteredData.length} Einträge)
        </p>
        <div className="flex items-center gap-2">
          <button
            className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-input bg-transparent text-sm font-medium shadow-sm hover:bg-accent hover:text-accent-foreground disabled:pointer-events-none disabled:opacity-50"
            onClick={() => table.previousPage()}
            disabled={!table.getCanPreviousPage()}
            data-testid="prev-page"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <button
            className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-input bg-transparent text-sm font-medium shadow-sm hover:bg-accent hover:text-accent-foreground disabled:pointer-events-none disabled:opacity-50"
            onClick={() => table.nextPage()}
            disabled={!table.getCanNextPage()}
            data-testid="next-page"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  )
}
