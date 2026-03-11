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
import type { Aufwandsentschaedigung, FreibetragSummary } from "@/types/finance"
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
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import { UTILIZATION } from "@/constants/design"
import {
  ArrowUpDown,
  ChevronLeft,
  ChevronRight,
} from "lucide-react"

const API_BASE = "/api"

const AUFWAND_TYP_LABELS: Record<string, string> = {
  uebungsleiter: "Uebungsleiterpauschale",
  ehrenamt: "Ehrenamtspauschale",
}

const AUFWAND_TYP_LIMITS: Record<string, number> = {
  uebungsleiter: 3000,
  ehrenamt: 840,
}

function formatEuro(amount: number | null | undefined): string {
  return (amount ?? 0).toLocaleString("de-DE", {
    style: "currency",
    currency: "EUR",
  })
}

function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return "--"
  const d = new Date(dateStr)
  const day = String(d.getDate()).padStart(2, "0")
  const month = String(d.getMonth() + 1).padStart(2, "0")
  const year = d.getFullYear()
  return `${day}.${month}.${year}`
}

function getUtilizationColor(percent: number): string {
  if (percent >= UTILIZATION.warning.max) return UTILIZATION.danger.color
  if (percent >= UTILIZATION.ok.max) return UTILIZATION.warning.color
  return UTILIZATION.ok.color
}

function getProgressBarColor(percent: number): string {
  if (percent >= UTILIZATION.warning.max) return "bg-red-500"
  if (percent >= UTILIZATION.ok.max) return "bg-amber-500"
  return "bg-emerald-500"
}

export function EhrenamtTab() {
  const currentYear = new Date().getFullYear()
  const [year, setYear] = useState(currentYear)
  const [typFilter, setTypFilter] = useState<string>("alle")
  const [entries, setEntries] = useState<Aufwandsentschaedigung[]>([])
  const [summaries, setSummaries] = useState<FreibetragSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [sorting, setSorting] = useState<SortingState>([])
  const [pagination, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: 10,
  })

  const yearOptions = useMemo(() => {
    const years: number[] = []
    for (let y = currentYear; y >= currentYear - 5; y--) {
      years.push(y)
    }
    return years
  }, [currentYear])

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({ year: String(year) })
      if (typFilter && typFilter !== "alle") {
        params.set("typ", typFilter)
      }

      const [entriesRes, summaryRes] = await Promise.all([
        fetch(`${API_BASE}/finanzen/ehrenamt?${params}`),
        fetch(`${API_BASE}/finanzen/ehrenamt/freibetrag?year=${year}`),
      ])

      if (entriesRes.ok) {
        const data = await entriesRes.json()
        setEntries(data.items ?? [])
      } else {
        setEntries([])
      }

      if (summaryRes.ok) {
        const data = await summaryRes.json()
        setSummaries(data.items ?? [])
      } else {
        setSummaries([])
      }
    } catch {
      setEntries([])
      setSummaries([])
    } finally {
      setLoading(false)
    }
  }, [year, typFilter])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const columns = useMemo<ColumnDef<Aufwandsentschaedigung>[]>(
    () => [
      {
        accessorKey: "mitglied_name",
        header: ({ column }) => (
          <button
            className="flex items-center gap-1 hover:text-foreground"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          >
            Person
            <ArrowUpDown className="h-4 w-4" />
          </button>
        ),
        cell: ({ getValue }) => (
          <span className="font-medium text-sm">{getValue<string>()}</span>
        ),
      },
      {
        accessorKey: "betrag",
        header: ({ column }) => (
          <button
            className="flex items-center gap-1 hover:text-foreground"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          >
            Betrag
            <ArrowUpDown className="h-4 w-4" />
          </button>
        ),
        cell: ({ getValue }) => (
          <span className="font-medium tabular-nums text-right">
            {formatEuro(getValue<number>())}
          </span>
        ),
      },
      {
        accessorKey: "datum",
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
        accessorKey: "typ",
        header: "Kategorie",
        cell: ({ getValue }) => {
          const typ = getValue<string>()
          return (
            <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-blue-50 text-blue-700">
              {AUFWAND_TYP_LABELS[typ] ?? typ}
            </span>
          )
        },
      },
      {
        accessorKey: "beschreibung",
        header: "Beschreibung",
        cell: ({ getValue }) => (
          <span className="text-sm text-muted-foreground">
            {getValue<string>()}
          </span>
        ),
      },
    ],
    []
  )

  const table = useReactTable({
    data: entries,
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
    <div className="space-y-6">
      {/* Freibetrag Summary Cards */}
      {summaries.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-muted-foreground mb-3">
            Freibetrag-Auslastung {year}
          </h3>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {summaries.map((s) => {
              const typLabel = AUFWAND_TYP_LABELS[s.typ] ?? s.typ
              const limit = AUFWAND_TYP_LIMITS[s.typ] ?? s.limit
              return (
                <Card
                  key={`${s.mitglied_id}-${s.typ}`}
                  data-testid="freibetrag-card"
                  className={cn(s.warning && "border-amber-400")}
                >
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base">{s.mitglied_name}</CardTitle>
                    <p className="text-xs text-muted-foreground">{typLabel}</p>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">Verbraucht</span>
                      <span className="font-medium tabular-nums">
                        {formatEuro(s.total)} / {formatEuro(limit)}
                      </span>
                    </div>
                    <div className="space-y-1">
                      <div className="flex justify-between text-sm">
                        <span className="text-muted-foreground">Auslastung</span>
                        <span
                          className={cn(
                            "font-medium tabular-nums",
                            getUtilizationColor(s.percent)
                          )}
                        >
                          {s.percent.toFixed(1)}%
                        </span>
                      </div>
                      <div className="h-2 w-full overflow-hidden rounded-full bg-primary/20">
                        <div
                          className={cn(
                            "h-full rounded-full transition-all",
                            getProgressBarColor(s.percent)
                          )}
                          style={{ width: `${Math.min(s.percent, 100)}%` }}
                          data-testid="freibetrag-progress"
                        />
                      </div>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">Verbleibend</span>
                      <span className="font-medium tabular-nums">
                        {formatEuro(s.remaining)}
                      </span>
                    </div>
                    {s.warning && (
                      <p
                        className="text-xs font-medium text-amber-600"
                        data-testid="freibetrag-warning"
                      >
                        Achtung: Ueber 80% des Freibetrags ausgeschoepft
                      </p>
                    )}
                  </CardContent>
                </Card>
              )
            })}
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <Select
          value={String(year)}
          onValueChange={(v) => setYear(Number(v))}
        >
          <SelectTrigger className="w-32" data-testid="ehrenamt-year-filter">
            <SelectValue placeholder="Jahr" />
          </SelectTrigger>
          <SelectContent>
            {yearOptions.map((y) => (
              <SelectItem key={y} value={String(y)}>
                {y}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={typFilter} onValueChange={setTypFilter}>
          <SelectTrigger className="w-56" data-testid="ehrenamt-typ-filter">
            <SelectValue placeholder="Kategorie" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="alle">Alle Kategorien</SelectItem>
            {Object.entries(AUFWAND_TYP_LABELS).map(([key, label]) => (
              <SelectItem key={key} value={key}>
                {label}
              </SelectItem>
            ))}
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
                      : flexRender(header.column.columnDef.header, header.getContext())}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows?.length ? (
              table.getRowModel().rows.map((row) => (
                <TableRow key={row.id} data-testid="ehrenamt-row">
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
                  Keine Aufwandsentschaedigungen fuer {year} gefunden.
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
          {table.getPageCount() || 1} ({entries.length} Eintraege)
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
