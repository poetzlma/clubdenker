import { useState, useMemo, useEffect, useCallback } from "react"
import {
  type ColumnDef,
  type SortingState,
  type PaginationState,
  type RowSelectionState,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  getPaginationRowModel,
  useReactTable,
} from "@tanstack/react-table"
import type { Rechnung, RechnungStatus } from "@/types/finance"
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
import { InvoiceDialog } from "@/components/finanzen/invoice-dialog"
import { VersandDialog } from "@/components/finanzen/versand-dialog"
import {
  RECHNUNG_STATUS_COLORS,
  RECHNUNG_TYP_LABELS,
  SPHERE_COLORS,
} from "@/constants/design"
import { cn } from "@/lib/utils"
import {
  ArrowUpDown,
  ChevronLeft,
  ChevronRight,
  Download,
  FileText,
  FileCode,
  MoreHorizontal,
  Plus,
  Send,
} from "lucide-react"

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

const mockInvoices: Rechnung[] = [
  {
    id: 1, rechnungsnummer: "RE-2026-001", rechnungstyp: "mitgliedsbeitrag",
    status: "mahnung_2", mahnstufe: 2, empfaenger_typ: "mitglied",
    empfaenger_name: "Schmidt, Thomas", mitglied_id: 1, mitglied_name: "Schmidt, Thomas",
    rechnungsdatum: "2026-01-15", faelligkeitsdatum: "2026-01-29",
    summe_netto: 120.0, summe_steuer: 0, summe_brutto: 120.0,
    betrag: 120.0, bezahlt_betrag: 0, offener_betrag: 120.0,
    sphaere: "ideell", zahlungsziel_tage: 14, positionen: [],
    created_at: "2026-01-15T10:00:00Z",
  },
  {
    id: 2, rechnungsnummer: "RE-2026-002", rechnungstyp: "mitgliedsbeitrag",
    status: "gestellt", mahnstufe: 0, empfaenger_typ: "mitglied",
    empfaenger_name: "Müller, Anna", mitglied_id: 2, mitglied_name: "Müller, Anna",
    rechnungsdatum: "2026-02-15", faelligkeitsdatum: "2026-03-01",
    summe_netto: 60.0, summe_steuer: 0, summe_brutto: 60.0,
    betrag: 60.0, bezahlt_betrag: 0, offener_betrag: 60.0,
    sphaere: "ideell", zahlungsziel_tage: 14, positionen: [],
    created_at: "2026-02-15T10:00:00Z",
  },
  {
    id: 3, rechnungsnummer: "RE-2026-003", rechnungstyp: "mitgliedsbeitrag",
    status: "bezahlt", mahnstufe: 0, empfaenger_typ: "mitglied",
    empfaenger_name: "Weber, Klaus", mitglied_id: 3, mitglied_name: "Weber, Klaus",
    rechnungsdatum: "2026-01-15", faelligkeitsdatum: "2026-02-15",
    summe_netto: 120.0, summe_steuer: 0, summe_brutto: 120.0,
    betrag: 120.0, bezahlt_betrag: 120.0, offener_betrag: 0,
    sphaere: "ideell", zahlungsziel_tage: 14, bezahlt_am: "2026-02-10",
    positionen: [], created_at: "2026-01-15T10:00:00Z",
  },
  {
    id: 4, rechnungsnummer: "RE-2026-004", rechnungstyp: "mitgliedsbeitrag",
    status: "storniert", mahnstufe: 0, empfaenger_typ: "mitglied",
    empfaenger_name: "Fischer, Maria", mitglied_id: 4, mitglied_name: "Fischer, Maria",
    rechnungsdatum: "2026-01-15", faelligkeitsdatum: "2026-02-15",
    summe_netto: 0.0, summe_steuer: 0, summe_brutto: 0.0,
    betrag: 0.0, bezahlt_betrag: 0, offener_betrag: 0,
    sphaere: "ideell", zahlungsziel_tage: 14, positionen: [],
    created_at: "2026-01-15T10:00:00Z",
  },
  {
    id: 5, rechnungsnummer: "RE-2026-005", rechnungstyp: "mitgliedsbeitrag",
    status: "mahnung_1", mahnstufe: 1, empfaenger_typ: "mitglied",
    empfaenger_name: "Becker, Stefan", mitglied_id: 5, mitglied_name: "Becker, Stefan",
    rechnungsdatum: "2026-01-15", faelligkeitsdatum: "2026-02-01",
    summe_netto: 120.0, summe_steuer: 0, summe_brutto: 120.0,
    betrag: 120.0, bezahlt_betrag: 0, offener_betrag: 120.0,
    sphaere: "ideell", zahlungsziel_tage: 14, positionen: [],
    created_at: "2026-01-15T10:00:00Z",
  },
  {
    id: 6, rechnungsnummer: "RE-2026-006", rechnungstyp: "hallenmiete",
    status: "gestellt", mahnstufe: 0, empfaenger_typ: "extern",
    empfaenger_name: "Turnverein Nachbarstadt",
    rechnungsdatum: "2026-02-20", faelligkeitsdatum: "2026-03-20",
    summe_netto: 250.0, summe_steuer: 47.50, summe_brutto: 297.50,
    betrag: 297.50, bezahlt_betrag: 0, offener_betrag: 297.50,
    sphaere: "vermoegensverwaltung", zahlungsziel_tage: 28, positionen: [],
    created_at: "2026-02-20T10:00:00Z",
  },
  {
    id: 7, rechnungsnummer: "RE-2026-007", rechnungstyp: "kursgebuehr",
    status: "bezahlt", mahnstufe: 0, empfaenger_typ: "mitglied",
    empfaenger_name: "Klein, Tom", mitglied_id: 7, mitglied_name: "Klein, Tom",
    rechnungsdatum: "2026-01-15", faelligkeitsdatum: "2026-02-15",
    summe_netto: 80.0, summe_steuer: 5.60, summe_brutto: 85.60,
    betrag: 85.60, bezahlt_betrag: 85.60, offener_betrag: 0,
    sphaere: "zweckbetrieb", zahlungsziel_tage: 14, bezahlt_am: "2026-02-01",
    positionen: [], created_at: "2026-01-15T10:00:00Z",
  },
  {
    id: 8, rechnungsnummer: "RE-2026-008", rechnungstyp: "sponsoring",
    status: "teilbezahlt", mahnstufe: 0, empfaenger_typ: "sponsor",
    empfaenger_name: "Autohaus Müller GmbH",
    rechnungsdatum: "2026-01-15", faelligkeitsdatum: "2026-02-15",
    summe_netto: 2000.0, summe_steuer: 380.0, summe_brutto: 2380.0,
    betrag: 2380.0, bezahlt_betrag: 1000.0, offener_betrag: 1380.0,
    sphaere: "wirtschaftlich", zahlungsziel_tage: 30, positionen: [],
    created_at: "2026-01-15T10:00:00Z",
  },
  {
    id: 9, rechnungsnummer: "RE-2026-009", rechnungstyp: "sonstige",
    status: "entwurf", mahnstufe: 0, empfaenger_typ: "extern",
    empfaenger_name: "Braun, Sabine",
    rechnungsdatum: "2026-03-01", faelligkeitsdatum: "2026-03-15",
    summe_netto: 50.0, summe_steuer: 0, summe_brutto: 50.0,
    betrag: 50.0, bezahlt_betrag: 0, offener_betrag: 50.0,
    sphaere: "ideell", zahlungsziel_tage: 14, positionen: [],
    created_at: "2026-03-01T10:00:00Z",
  },
  {
    id: 10, rechnungsnummer: "RE-2026-010", rechnungstyp: "mitgliedsbeitrag",
    status: "faellig", mahnstufe: 0, empfaenger_typ: "mitglied",
    empfaenger_name: "Koch, Michael", mitglied_id: 10, mitglied_name: "Koch, Michael",
    rechnungsdatum: "2026-02-01", faelligkeitsdatum: "2026-03-01",
    summe_netto: 120.0, summe_steuer: 0, summe_brutto: 120.0,
    betrag: 120.0, bezahlt_betrag: 0, offener_betrag: 120.0,
    sphaere: "ideell", zahlungsziel_tage: 14, positionen: [],
    created_at: "2026-02-01T10:00:00Z",
  },
  {
    id: 11, rechnungsnummer: "RE-2026-011", rechnungstyp: "mitgliedsbeitrag",
    status: "abgeschrieben", mahnstufe: 3, empfaenger_typ: "mitglied",
    empfaenger_name: "Wagner, Peter", mitglied_id: 8, mitglied_name: "Wagner, Peter",
    rechnungsdatum: "2025-06-01", faelligkeitsdatum: "2025-06-15",
    summe_netto: 120.0, summe_steuer: 0, summe_brutto: 120.0,
    betrag: 120.0, bezahlt_betrag: 0, offener_betrag: 120.0,
    sphaere: "ideell", zahlungsziel_tage: 14, positionen: [],
    created_at: "2025-06-01T10:00:00Z",
  },
]

function RechnungStatusBadge({ status }: { status: string }) {
  const config = RECHNUNG_STATUS_COLORS[status as keyof typeof RECHNUNG_STATUS_COLORS]
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

function RechnungTypBadge({ typ }: { typ: string }) {
  const label = RECHNUNG_TYP_LABELS[typ] ?? typ
  return (
    <span className="inline-flex items-center rounded-full bg-gray-50 px-2 py-0.5 text-xs font-medium text-gray-700">
      {label}
    </span>
  )
}

function SphaereBadge({ sphaere }: { sphaere?: string }) {
  if (!sphaere) return <span className="text-xs text-gray-400">--</span>
  const config = SPHERE_COLORS[sphaere as keyof typeof SPHERE_COLORS]
  if (!config) return <span className="text-xs">{sphaere}</span>
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

function downloadFile(url: string, fallbackFilename: string) {
  const link = document.createElement("a")
  link.href = url
  link.download = fallbackFilename
  link.target = "_blank"
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

export function InvoiceTable() {
  const [invoices, setInvoices] = useState<Rechnung[]>([])
  const [loading, setLoading] = useState(true)
  const [sorting, setSorting] = useState<SortingState>([])
  const [pagination, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: 10,
  })
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({})
  const [statusFilter, setStatusFilter] = useState<string>("alle")
  const [typFilter, setTypFilter] = useState<string>("alle")
  const [sphaereFilter, setSphaereFilter] = useState<string>("alle")
  const [searchTerm, setSearchTerm] = useState("")
  const [dateFrom, setDateFrom] = useState("")
  const [dateTo, setDateTo] = useState("")
  const [invoiceDialogOpen, setInvoiceDialogOpen] = useState(false)
  const [versandDialogOpen, setVersandDialogOpen] = useState(false)
  const [versandInvoice, setVersandInvoice] = useState<Rechnung | null>(null)
  const [exportYear, setExportYear] = useState(new Date().getFullYear().toString())
  const [exporting, setExporting] = useState(false)

  const fetchInvoices = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/finanzen/rechnungen`)
      if (!res.ok) throw new Error("API error")
      const data = await res.json()
      const items = data.items ?? data
      setInvoices(
        items.map((r: Rechnung) => ({
          ...r,
          empfaenger_name: r.empfaenger_name ?? r.mitglied_name ?? `#${r.mitglied_id ?? "?"}`,
          betrag: r.betrag ?? r.summe_brutto ?? 0,
          offener_betrag: r.offener_betrag ?? r.betrag ?? 0,
          bezahlt_betrag: r.bezahlt_betrag ?? 0,
          summe_netto: r.summe_netto ?? r.betrag ?? 0,
          summe_steuer: r.summe_steuer ?? 0,
          summe_brutto: r.summe_brutto ?? r.betrag ?? 0,
          positionen: r.positionen ?? [],
          mahnstufe: r.mahnstufe ?? 0,
          zahlungsziel_tage: r.zahlungsziel_tage ?? 14,
          rechnungstyp: r.rechnungstyp ?? "sonstige",
          empfaenger_typ: r.empfaenger_typ ?? "mitglied",
          status: r.status ?? "entwurf",
        }))
      )
    } catch {
      setInvoices(mockInvoices)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchInvoices()
  }, [fetchInvoices])

  async function handleAction(
    invoice: Rechnung,
    action: "stellen" | "stornieren" | "zahlung"
  ) {
    if (action === "stellen") {
      try {
        await fetch(`${API_BASE}/finanzen/rechnungen/${invoice.id}/stellen`, { method: "POST" })
      } catch {
        // optimistic
      }
      setInvoices((prev) =>
        prev.map((r) =>
          r.id === invoice.id ? { ...r, status: "gestellt" as RechnungStatus } : r
        )
      )
    } else if (action === "stornieren") {
      try {
        await fetch(`${API_BASE}/finanzen/rechnungen/${invoice.id}/stornieren`, { method: "POST" })
      } catch {
        // optimistic
      }
      setInvoices((prev) =>
        prev.map((r) =>
          r.id === invoice.id ? { ...r, status: "storniert" as RechnungStatus } : r
        )
      )
    } else if (action === "zahlung") {
      try {
        await fetch(`${API_BASE}/finanzen/rechnungen/${invoice.id}/zahlungen`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ betrag: invoice.offener_betrag }),
        })
      } catch {
        // optimistic
      }
      setInvoices((prev) =>
        prev.map((r) =>
          r.id === invoice.id
            ? {
                ...r,
                status: "bezahlt" as RechnungStatus,
                bezahlt_betrag: r.summe_brutto,
                offener_betrag: 0,
              }
            : r
        )
      )
    }
  }

  function handleDownloadPdf(invoice: Rechnung) {
    downloadFile(
      `${API_BASE}/finanzen/rechnungen/${invoice.id}/pdf`,
      `RE-${invoice.rechnungsnummer}.pdf`
    )
  }

  function handleDownloadXml(invoice: Rechnung) {
    downloadFile(
      `${API_BASE}/finanzen/rechnungen/${invoice.id}/xml`,
      `RE-${invoice.rechnungsnummer}-zugferd.xml`
    )
  }

  function handleVersenden(invoice: Rechnung) {
    setVersandInvoice(invoice)
    setVersandDialogOpen(true)
  }

  async function handleExportZip() {
    const year = parseInt(exportYear)
    if (isNaN(year)) return
    setExporting(true)
    try {
      const res = await fetch(`${API_BASE}/finanzen/rechnungen/export?jahr=${year}`)
      if (!res.ok) throw new Error("Export fehlgeschlagen")
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      downloadFile(url, `Rechnungen-${year}.zip`)
      URL.revokeObjectURL(url)
    } catch {
      // silently fail — user sees no download
    } finally {
      setExporting(false)
    }
  }

  const columns = useMemo<ColumnDef<Rechnung>[]>(
    () => [
      {
        id: "select",
        header: ({ table: tbl }) => (
          <input
            type="checkbox"
            checked={tbl.getIsAllPageRowsSelected()}
            onChange={tbl.getToggleAllPageRowsSelectedHandler()}
            className="h-4 w-4 accent-blue-600"
            aria-label="Alle auswaehlen"
          />
        ),
        cell: ({ row }) => (
          <input
            type="checkbox"
            checked={row.getIsSelected()}
            onChange={row.getToggleSelectedHandler()}
            className="h-4 w-4 accent-blue-600"
            aria-label="Zeile auswaehlen"
          />
        ),
        enableSorting: false,
        size: 32,
      },
      {
        accessorKey: "rechnungsnummer",
        header: ({ column }) => (
          <button
            className="flex items-center gap-1 hover:text-foreground"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          >
            RE-Nr.
            <ArrowUpDown className="h-4 w-4" />
          </button>
        ),
        cell: ({ getValue }) => (
          <span className="font-medium text-sm">{getValue<string>()}</span>
        ),
      },
      {
        accessorKey: "rechnungstyp",
        header: "Typ",
        cell: ({ getValue }) => <RechnungTypBadge typ={getValue<string>()} />,
      },
      {
        id: "empfaenger",
        header: ({ column }) => (
          <button
            className="flex items-center gap-1 hover:text-foreground"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          >
            Empfaenger
            <ArrowUpDown className="h-4 w-4" />
          </button>
        ),
        accessorFn: (row) => row.empfaenger_name ?? row.mitglied_name ?? "",
        cell: ({ getValue }) => (
          <span className="text-sm">{getValue<string>()}</span>
        ),
      },
      {
        accessorKey: "sphaere",
        header: "Sphaere",
        cell: ({ getValue }) => <SphaereBadge sphaere={getValue<string>()} />,
      },
      {
        id: "netto_brutto",
        header: ({ column }) => (
          <button
            className="flex items-center gap-1 hover:text-foreground"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          >
            Netto / Brutto
            <ArrowUpDown className="h-4 w-4" />
          </button>
        ),
        accessorFn: (row) => row.summe_brutto,
        cell: ({ row }) => (
          <div className="text-right">
            <div className="text-xs text-muted-foreground tabular-nums">
              {formatEuro(row.original.summe_netto)}
            </div>
            <div className="font-medium tabular-nums">
              {formatEuro(row.original.summe_brutto)}
            </div>
          </div>
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
        cell: ({ getValue }) => <RechnungStatusBadge status={getValue<string>()} />,
      },
      {
        accessorKey: "offener_betrag",
        header: () => <span className="text-right block">Offen</span>,
        cell: ({ getValue }) => {
          const val = getValue<number>()
          return (
            <span
              className={cn(
                "block text-right font-medium tabular-nums text-sm",
                val > 0 ? "text-red-600" : "text-gray-400"
              )}
            >
              {formatEuro(val)}
            </span>
          )
        },
      },
      {
        id: "aktionen",
        header: "Aktionen",
        enableSorting: false,
        cell: ({ row }) => {
          const invoice = row.original
          const s = invoice.status
          const canSend = s !== "entwurf" && s !== "storniert" && s !== "abgeschrieben"

          return (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                  <MoreHorizontal className="h-4 w-4" />
                  <span className="sr-only">Aktionen</span>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuLabel>E-Rechnung</DropdownMenuLabel>
                <DropdownMenuItem onClick={() => handleDownloadPdf(invoice)}>
                  <FileText className="h-4 w-4" />
                  PDF herunterladen
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => handleDownloadXml(invoice)}>
                  <FileCode className="h-4 w-4" />
                  ZUGFeRD-XML herunterladen
                </DropdownMenuItem>

                {canSend && (
                  <>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onClick={() => handleVersenden(invoice)}>
                      <Send className="h-4 w-4" />
                      Versenden
                    </DropdownMenuItem>
                  </>
                )}

                <DropdownMenuSeparator />
                <DropdownMenuLabel>Status</DropdownMenuLabel>

                {s === "entwurf" && (
                  <DropdownMenuItem onClick={() => handleAction(invoice, "stellen")}>
                    Stellen
                  </DropdownMenuItem>
                )}
                {(s === "gestellt" || s === "faellig" || s === "mahnung_1" || s === "mahnung_2" || s === "mahnung_3") && (
                  <DropdownMenuItem onClick={() => handleAction(invoice, "zahlung")}>
                    Zahlung verbuchen
                  </DropdownMenuItem>
                )}
                {(s === "entwurf" || s === "gestellt") && (
                  <DropdownMenuItem
                    className="text-red-600 focus:text-red-600"
                    onClick={() => handleAction(invoice, "stornieren")}
                  >
                    Stornieren
                  </DropdownMenuItem>
                )}
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
    if (statusFilter && statusFilter !== "alle") {
      data = data.filter((r) => r.status === statusFilter)
    }
    if (typFilter && typFilter !== "alle") {
      data = data.filter((r) => r.rechnungstyp === typFilter)
    }
    if (sphaereFilter && sphaereFilter !== "alle") {
      data = data.filter((r) => r.sphaere === sphaereFilter)
    }
    if (searchTerm) {
      const term = searchTerm.toLowerCase()
      data = data.filter(
        (r) =>
          (r.empfaenger_name ?? "").toLowerCase().includes(term) ||
          (r.mitglied_name ?? "").toLowerCase().includes(term) ||
          r.rechnungsnummer.toLowerCase().includes(term)
      )
    }
    if (dateFrom) {
      data = data.filter((r) => r.rechnungsdatum >= dateFrom)
    }
    if (dateTo) {
      data = data.filter((r) => r.rechnungsdatum <= dateTo)
    }
    return data
  }, [invoices, statusFilter, typFilter, sphaereFilter, searchTerm, dateFrom, dateTo])

  // Determine which invoices are selected (from filtered data)
  const selectedInvoices = useMemo(() => {
    const selectedIndices = Object.keys(rowSelection).filter((k) => rowSelection[k])
    return selectedIndices
      .map((idx) => filteredData[parseInt(idx)])
      .filter(Boolean) as Rechnung[]
  }, [rowSelection, filteredData])

  const table = useReactTable({
    data: filteredData,
    columns,
    state: { sorting, pagination, rowSelection },
    onSortingChange: setSorting,
    onPaginationChange: setPagination,
    onRowSelectionChange: setRowSelection,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    enableRowSelection: true,
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
      {/* Filters + Actions */}
      <div className="flex flex-wrap items-center gap-3">
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-40" data-testid="status-filter">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="alle">Alle Status</SelectItem>
            {Object.entries(RECHNUNG_STATUS_COLORS).map(([key, config]) => (
              <SelectItem key={key} value={key}>
                {config.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={typFilter} onValueChange={setTypFilter}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="Typ" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="alle">Alle Typen</SelectItem>
            {Object.entries(RECHNUNG_TYP_LABELS).map(([key, label]) => (
              <SelectItem key={key} value={key}>
                {label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={sphaereFilter} onValueChange={setSphaereFilter}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="Sphaere" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="alle">Alle Sphaeren</SelectItem>
            {Object.entries(SPHERE_COLORS).map(([key, config]) => (
              <SelectItem key={key} value={key}>
                {config.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Input
          type="date"
          className="w-36"
          placeholder="Von"
          value={dateFrom}
          onChange={(e) => setDateFrom(e.target.value)}
        />
        <Input
          type="date"
          className="w-36"
          placeholder="Bis"
          value={dateTo}
          onChange={(e) => setDateTo(e.target.value)}
        />
        <Input
          className="w-48"
          placeholder="Suche..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
        <div className="ml-auto">
          <Button onClick={() => setInvoiceDialogOpen(true)}>
            <Plus className="h-4 w-4" />
            Neue Rechnung
          </Button>
        </div>
      </div>

      {/* Batch actions toolbar */}
      <div className="flex flex-wrap items-center gap-3">
        {/* ZIP export */}
        <div className="flex items-center gap-2">
          <Input
            type="number"
            className="w-24"
            value={exportYear}
            onChange={(e) => setExportYear(e.target.value)}
            min="2020"
            max="2099"
            placeholder="Jahr"
          />
          <Button
            variant="outline"
            size="sm"
            onClick={handleExportZip}
            disabled={exporting}
          >
            <Download className="h-4 w-4" />
            {exporting ? "Exportiert..." : "Export Jahr als ZIP"}
          </Button>
        </div>

        {/* Selection-dependent batch actions */}
        {selectedInvoices.length > 0 && (
          <div className="flex items-center gap-2 ml-auto">
            <span className="text-sm text-muted-foreground">
              {selectedInvoices.length} ausgewaehlt
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                // For batch send, open dialog for the first selected invoice
                // In a real app this would be a batch dialog
                const sendable = selectedInvoices.filter(
                  (inv) =>
                    inv.status !== "entwurf" &&
                    inv.status !== "storniert" &&
                    inv.status !== "abgeschrieben"
                )
                if (sendable.length > 0) {
                  setVersandInvoice(sendable[0])
                  setVersandDialogOpen(true)
                }
              }}
            >
              <Send className="h-4 w-4" />
              Ausgewaehlte versenden
            </Button>
          </div>
        )}
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
                <TableRow
                  key={row.id}
                  data-testid="invoice-row"
                  data-state={row.getIsSelected() && "selected"}
                >
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
                  Keine Rechnungen gefunden.
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

      {/* Invoice Dialog */}
      <InvoiceDialog
        open={invoiceDialogOpen}
        onOpenChange={setInvoiceDialogOpen}
        onSuccess={fetchInvoices}
      />

      {/* Versand Dialog */}
      <VersandDialog
        open={versandDialogOpen}
        onOpenChange={setVersandDialogOpen}
        invoice={versandInvoice}
        onSuccess={fetchInvoices}
      />
    </div>
  )
}
