import { useState, useMemo } from "react"
import {
  type ColumnDef,
  type SortingState,
  type ColumnFiltersState,
  type PaginationState,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  useReactTable,
} from "@tanstack/react-table"
import type { Member } from "@/types/member"
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
import { STATUS_COLORS } from "@/constants/design"

function formatDate(dateStr: string): string {
  if (!dateStr) return ""
  const date = new Date(dateStr)
  const day = String(date.getDate()).padStart(2, "0")
  const month = String(date.getMonth() + 1).padStart(2, "0")
  const year = date.getFullYear()
  return `${day}.${month}.${year}`
}

const beitragLabels: Record<Member["beitragskategorie"], string> = {
  erwachsene: "Erwachsene",
  jugend: "Jugend",
  familie: "Familie",
  passiv: "Passiv",
  ehrenmitglied: "Ehrenmitglied",
}

const allDepartments = [
  "Fußball",
  "Tennis",
  "Schwimmen",
  "Leichtathletik",
  "Turnen",
  "Handball",
]

interface MemberTableProps {
  data: Member[]
  onRowClick?: (member: Member) => void
}

export function MemberTable({ data, onRowClick }: MemberTableProps) {
  const [sorting, setSorting] = useState<SortingState>([])
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([])
  const [pagination, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: 10,
  })
  const [nameFilter, setNameFilter] = useState("")
  const [statusFilter, setStatusFilter] = useState<string>("alle")
  const [departmentFilter, setDepartmentFilter] = useState<string>("alle")

  const columns = useMemo<ColumnDef<Member>[]>(
    () => [
      {
        id: "name",
        accessorFn: (row) => `${row.vorname} ${row.nachname}`,
        header: ({ column }) => (
          <button
            className="flex items-center gap-1 hover:text-foreground"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          >
            Name
            <ArrowUpDown className="h-4 w-4" />
          </button>
        ),
        cell: ({ getValue }) => (
          <span className="font-medium">{getValue<string>()}</span>
        ),
      },
      {
        accessorKey: "email",
        header: ({ column }) => (
          <button
            className="flex items-center gap-1 hover:text-foreground"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          >
            E-Mail
            <ArrowUpDown className="h-4 w-4" />
          </button>
        ),
      },
      {
        accessorKey: "abteilungen",
        header: "Abteilung(en)",
        cell: ({ getValue }) => {
          const depts = getValue<string[]>()
          return (
            <div className="flex flex-wrap gap-1">
              {depts.map((dept) => (
                <span
                  key={dept}
                  className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-700"
                >
                  {dept}
                </span>
              ))}
            </div>
          )
        },
        enableSorting: false,
      },
      {
        accessorKey: "status",
        header: ({ column }) => (
          <button
            className="flex items-center gap-1 hover:text-foreground"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          >
            Status
            <ArrowUpDown className="h-4 w-4" />
          </button>
        ),
        cell: ({ getValue }) => {
          const status = getValue<Member["status"]>()
          const config = STATUS_COLORS[status]
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
        },
      },
      {
        accessorKey: "beitragskategorie",
        header: ({ column }) => (
          <button
            className="flex items-center gap-1 hover:text-foreground"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          >
            Beitragskategorie
            <ArrowUpDown className="h-4 w-4" />
          </button>
        ),
        cell: ({ getValue }) => {
          const kat = getValue<Member["beitragskategorie"]>()
          return beitragLabels[kat]
        },
      },
      {
        accessorKey: "eintrittsdatum",
        header: ({ column }) => (
          <button
            className="flex items-center gap-1 hover:text-foreground"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          >
            Eintrittsdatum
            <ArrowUpDown className="h-4 w-4" />
          </button>
        ),
        cell: ({ getValue }) => formatDate(getValue<string>()),
      },
    ],
    []
  )

  const filteredData = useMemo(() => {
    let result = data
    if (nameFilter) {
      const lower = nameFilter.toLowerCase()
      result = result.filter(
        (m) =>
          m.vorname.toLowerCase().includes(lower) ||
          m.nachname.toLowerCase().includes(lower)
      )
    }
    if (statusFilter && statusFilter !== "alle") {
      result = result.filter((m) => m.status === statusFilter)
    }
    if (departmentFilter && departmentFilter !== "alle") {
      result = result.filter((m) => m.abteilungen.includes(departmentFilter))
    }
    return result
  }, [data, nameFilter, statusFilter, departmentFilter])

  // eslint-disable-next-line react-hooks/incompatible-library
  const table = useReactTable({
    data: filteredData,
    columns,
    state: {
      sorting,
      columnFilters,
      pagination,
    },
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onPaginationChange: setPagination,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
  })

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap items-center gap-4">
        <input
          type="text"
          placeholder="Name suchen..."
          value={nameFilter}
          onChange={(e) => setNameFilter(e.target.value)}
          className="h-9 w-64 rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          data-testid="name-filter"
        />
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-40" data-testid="status-filter">
            <SelectValue placeholder="Status filtern" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="alle">Alle Status</SelectItem>
            <SelectItem value="aktiv">Aktiv</SelectItem>
            <SelectItem value="passiv">Passiv</SelectItem>
            <SelectItem value="gekuendigt">Gekündigt</SelectItem>
            <SelectItem value="ehrenmitglied">Ehrenmitglied</SelectItem>
          </SelectContent>
        </Select>
        <Select value={departmentFilter} onValueChange={setDepartmentFilter}>
          <SelectTrigger className="w-48" data-testid="department-filter">
            <SelectValue placeholder="Abteilung filtern" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="alle">Alle Abteilungen</SelectItem>
            {allDepartments.map((dept) => (
              <SelectItem key={dept} value={dept}>
                {dept}
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
                <TableRow
                  key={row.id}
                  className="cursor-pointer"
                  onClick={() => onRowClick?.(row.original)}
                  data-testid="member-row"
                >
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
                  Keine Mitglieder gefunden.
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
