import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import { InvoiceTable } from "@/components/finanzen/invoice-table"
import type { Rechnung } from "@/types/finance"

// Mock child dialogs to avoid pulling in their dependencies
vi.mock("@/components/finanzen/invoice-dialog", () => ({
  InvoiceDialog: () => null,
}))
vi.mock("@/components/finanzen/versand-dialog", () => ({
  VersandDialog: () => null,
}))

const mockInvoices: Rechnung[] = [
  {
    id: 1,
    rechnungsnummer: "RE-2026-001",
    rechnungstyp: "mitgliedsbeitrag",
    status: "entwurf",
    mahnstufe: 0,
    empfaenger_typ: "mitglied",
    empfaenger_name: "Schmidt, Thomas",
    mitglied_id: 1,
    mitglied_name: "Schmidt, Thomas",
    rechnungsdatum: "2026-01-15",
    faelligkeitsdatum: "2026-01-29",
    summe_netto: 120.0,
    summe_steuer: 0,
    summe_brutto: 120.0,
    betrag: 120.0,
    bezahlt_betrag: 0,
    offener_betrag: 120.0,
    sphaere: "ideell",
    zahlungsziel_tage: 14,
    positionen: [],
    created_at: "2026-01-15T10:00:00Z",
  },
  {
    id: 2,
    rechnungsnummer: "RE-2026-002",
    rechnungstyp: "kursgebuehr",
    status: "gestellt",
    mahnstufe: 0,
    empfaenger_typ: "mitglied",
    empfaenger_name: "Mueller, Anna",
    mitglied_id: 2,
    mitglied_name: "Mueller, Anna",
    rechnungsdatum: "2026-02-15",
    faelligkeitsdatum: "2026-03-01",
    summe_netto: 60.0,
    summe_steuer: 4.2,
    summe_brutto: 64.2,
    betrag: 64.2,
    bezahlt_betrag: 0,
    offener_betrag: 64.2,
    sphaere: "zweckbetrieb",
    zahlungsziel_tage: 14,
    positionen: [],
    created_at: "2026-02-15T10:00:00Z",
  },
  {
    id: 3,
    rechnungsnummer: "RE-2026-003",
    rechnungstyp: "hallenmiete",
    status: "bezahlt",
    mahnstufe: 0,
    empfaenger_typ: "extern",
    empfaenger_name: "Weber, Klaus",
    rechnungsdatum: "2026-01-15",
    faelligkeitsdatum: "2026-02-15",
    summe_netto: 200.0,
    summe_steuer: 38.0,
    summe_brutto: 238.0,
    betrag: 238.0,
    bezahlt_betrag: 238.0,
    offener_betrag: 0,
    sphaere: "vermoegensverwaltung",
    zahlungsziel_tage: 14,
    bezahlt_am: "2026-02-10",
    positionen: [],
    created_at: "2026-01-15T10:00:00Z",
  },
]

function mockFetchSuccess(data: Rechnung[]) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ items: data }),
    })
  )
}

function mockFetchEmpty() {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ items: [] }),
    })
  )
}

beforeEach(() => {
  vi.restoreAllMocks()
})

describe("InvoiceTable", () => {
  it("renders table headers", async () => {
    mockFetchSuccess(mockInvoices)
    render(<InvoiceTable />)

    await waitFor(() => {
      expect(screen.getByText("RE-Nr.")).toBeInTheDocument()
    })
    expect(screen.getByText("Typ")).toBeInTheDocument()
    expect(screen.getByText("Empfaenger")).toBeInTheDocument()
    expect(screen.getByText("Sphaere")).toBeInTheDocument()
    expect(screen.getByText("Netto / Brutto")).toBeInTheDocument()
    expect(screen.getByText("Faellig am")).toBeInTheDocument()
    expect(screen.getByText("Status")).toBeInTheDocument()
    expect(screen.getByText("Offen")).toBeInTheDocument()
    // "Aktionen" appears both as header and sr-only button text
    const headerCells = document.querySelectorAll("th")
    const headerTexts = Array.from(headerCells).map((th) => th.textContent)
    expect(headerTexts).toContain("Aktionen")
  })

  it("renders invoice rows from API", async () => {
    mockFetchSuccess(mockInvoices)
    render(<InvoiceTable />)

    await waitFor(() => {
      expect(screen.getByText("RE-2026-001")).toBeInTheDocument()
      expect(screen.getByText("RE-2026-002")).toBeInTheDocument()
      expect(screen.getByText("RE-2026-003")).toBeInTheDocument()
    })

    expect(screen.getByText("Schmidt, Thomas")).toBeInTheDocument()
    expect(screen.getByText("Mueller, Anna")).toBeInTheDocument()
    expect(screen.getByText("Weber, Klaus")).toBeInTheDocument()

    const rows = screen.getAllByTestId("invoice-row")
    expect(rows).toHaveLength(3)
  })

  it("shows status badges with correct text", async () => {
    mockFetchSuccess(mockInvoices)
    render(<InvoiceTable />)

    await waitFor(() => {
      expect(screen.getAllByTestId("invoice-row")).toHaveLength(3)
    })

    // Status labels from RECHNUNG_STATUS_COLORS
    expect(screen.getByText("Entwurf")).toBeInTheDocument()
    expect(screen.getByText("Gestellt")).toBeInTheDocument()
    expect(screen.getByText("Bezahlt")).toBeInTheDocument()
  })

  it("shows empty state when no invoices", async () => {
    mockFetchEmpty()
    render(<InvoiceTable />)

    await waitFor(() => {
      expect(
        screen.getByText("Keine Rechnungen gefunden.")
      ).toBeInTheDocument()
    })
  })

  it("renders action buttons for each row", async () => {
    mockFetchSuccess(mockInvoices)
    render(<InvoiceTable />)

    await waitFor(() => {
      expect(screen.getAllByTestId("invoice-row")).toHaveLength(3)
    })

    // Each row has an action dropdown trigger button with sr-only "Aktionen" text
    const actionButtons = screen.getAllByRole("button", { name: "Aktionen" })
    expect(actionButtons).toHaveLength(3)
  })
})
