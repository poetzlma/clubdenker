import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import { BookingTable } from "@/components/finanzen/booking-table"
import type { Buchung } from "@/types/finance"

// Mock child dialogs to avoid pulling in their dependencies
vi.mock("@/components/finanzen/booking-dialog", () => ({
  BookingDialog: () => null,
}))
vi.mock("@/components/finanzen/datev-export-dialog", () => ({
  DatevExportDialog: () => null,
}))

const mockBookings: Buchung[] = [
  {
    id: 1,
    buchungsdatum: "2025-01-15",
    betrag: 120.0,
    beschreibung: "Mitgliedsbeitrag Max Mustermann",
    konto: "1200",
    gegenkonto: "8100",
    sphare: "ideell",
    kostenstelle: "Verwaltung",
    mitglied_id: 1,
    created_at: "2025-01-15T10:00:00Z",
  },
  {
    id: 2,
    buchungsdatum: "2025-01-20",
    betrag: -250.0,
    beschreibung: "Sportgeraete Einkauf",
    konto: "4800",
    gegenkonto: "1200",
    sphare: "zweckbetrieb",
    kostenstelle: null,
    mitglied_id: null,
    created_at: "2025-01-20T10:00:00Z",
  },
  {
    id: 3,
    buchungsdatum: "2025-02-01",
    betrag: 500.0,
    beschreibung: "Hallenmiete Einnahmen",
    konto: "1200",
    gegenkonto: "8200",
    sphare: "vermoegensverwaltung",
    kostenstelle: "Verwaltung",
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
    kostenstelle: null,
    mitglied_id: null,
    created_at: "2025-02-10T10:00:00Z",
  },
]

function mockFetchSuccess(data: Buchung[]) {
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

describe("BookingTable", () => {
  it("renders table headers", async () => {
    mockFetchSuccess(mockBookings)
    render(<BookingTable />)

    await waitFor(() => {
      expect(screen.getByText("Datum")).toBeInTheDocument()
      expect(screen.getByText("Betrag")).toBeInTheDocument()
      expect(screen.getByText("Beschreibung")).toBeInTheDocument()
      expect(screen.getByText("Konto")).toBeInTheDocument()
      expect(screen.getByText("Gegenkonto")).toBeInTheDocument()
      expect(screen.getByText("Kostenstelle")).toBeInTheDocument()
    })
    // Sphare header uses umlaut
    expect(screen.getByText("Sph\u00e4re")).toBeInTheDocument()
  })

  it("renders booking rows", async () => {
    mockFetchSuccess(mockBookings)
    render(<BookingTable />)

    await waitFor(() => {
      expect(screen.getByText("Mitgliedsbeitrag Max Mustermann")).toBeInTheDocument()
      expect(screen.getByText("Sportgeraete Einkauf")).toBeInTheDocument()
      expect(screen.getByText("Hallenmiete Einnahmen")).toBeInTheDocument()
      expect(screen.getByText("Sponsoring Vereinsfest")).toBeInTheDocument()
    })

    const rows = screen.getAllByTestId("booking-row")
    expect(rows).toHaveLength(4)
  })

  it("shows empty state when no bookings", async () => {
    mockFetchEmpty()
    render(<BookingTable />)

    await waitFor(() => {
      expect(screen.getByText("Keine Buchungen gefunden.")).toBeInTheDocument()
    })
  })

  it("formats currency in EUR format", async () => {
    mockFetchSuccess(mockBookings)
    render(<BookingTable />)

    await waitFor(() => {
      expect(screen.getAllByTestId("booking-row")).toHaveLength(4)
    })
    // Verify currency symbol and amounts appear in the table
    const tableText = screen.getByRole("table").textContent ?? ""
    expect(tableText).toMatch(/€/)
    expect(tableText).toMatch(/120/)
    expect(tableText).toMatch(/250/)
    expect(tableText).toMatch(/500/)
    expect(tableText).toMatch(/1.?500/)
  })

  it("renders sphere badges for each booking", async () => {
    mockFetchSuccess(mockBookings)
    render(<BookingTable />)

    await waitFor(() => {
      expect(screen.getByText("Ideell")).toBeInTheDocument()
      expect(screen.getByText("Zweckbetrieb")).toBeInTheDocument()
    })
    expect(screen.getByText("Wirtschaftlich")).toBeInTheDocument()
    // The umlaut label
    expect(screen.getByText(/Verm.gensverwaltung/)).toBeInTheDocument()
  })
})
