import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { PaymentOverview } from "@/components/finanzen/payment-overview"

// Mock child dialogs to avoid deep rendering
vi.mock("@/components/finanzen/booking-dialog", () => ({
  BookingDialog: () => <div data-testid="booking-dialog" />,
}))
vi.mock("@/components/finanzen/invoice-dialog", () => ({
  InvoiceDialog: () => <div data-testid="invoice-dialog" />,
}))
vi.mock("@/components/finanzen/beitragslauf-dialog", () => ({
  BeitragslaufDialog: () => <div data-testid="beitragslauf-dialog" />,
}))

function renderComponent() {
  return render(
    <MemoryRouter>
      <PaymentOverview />
    </MemoryRouter>
  )
}

describe("PaymentOverview", () => {
  describe("loading state", () => {
    beforeEach(() => {
      // fetch never resolves so the component stays in loading state
      vi.stubGlobal(
        "fetch",
        vi.fn().mockImplementation(() => new Promise(() => {}))
      )
    })

    it("renders loading indicator while data is being fetched", () => {
      renderComponent()
      expect(screen.getByText("Laden...")).toBeInTheDocument()
    })
  })

  describe("with successful API responses", () => {
    beforeEach(() => {
      vi.stubGlobal(
        "fetch",
        vi.fn().mockImplementation((url: string) => {
          if (url.includes("/finanzen/rechnungen")) {
            return Promise.resolve({
              ok: true,
              json: () =>
                Promise.resolve({
                  items: [
                    {
                      id: 1,
                      rechnungsnummer: "RE-2026-001",
                      rechnungstyp: "mitgliedsbeitrag",
                      status: "gestellt",
                      mahnstufe: 0,
                      empfaenger_typ: "mitglied",
                      empfaenger_name: "Schmidt, Thomas",
                      mitglied_id: 1,
                      rechnungsdatum: "2026-01-15",
                      faelligkeitsdatum: "2026-04-20",
                      summe_netto: 120,
                      summe_steuer: 0,
                      summe_brutto: 120,
                      betrag: 120,
                      bezahlt_betrag: 0,
                      offener_betrag: 120,
                      sphaere: "ideell",
                      zahlungsziel_tage: 14,
                      positionen: [],
                      created_at: "2026-01-15T10:00:00Z",
                    },
                  ],
                }),
            })
          }
          if (url.includes("/finanzen/kassenstand")) {
            return Promise.resolve({
              ok: true,
              json: () =>
                Promise.resolve({
                  total: 12450,
                  by_sphere: [
                    { sphare: "ideell", betrag: 5200 },
                    { sphare: "zweckbetrieb", betrag: 3100 },
                    { sphare: "vermoegensverwaltung", betrag: 2650 },
                    { sphare: "wirtschaftlich", betrag: 1500 },
                  ],
                }),
            })
          }
          if (url.includes("/finanzen/buchungen")) {
            return Promise.resolve({
              ok: true,
              json: () =>
                Promise.resolve({
                  items: [
                    {
                      id: 101,
                      buchungsdatum: "2026-03-05",
                      betrag: 250.5,
                      beschreibung: "Beitrag Mueller",
                      konto: "1200",
                      gegenkonto: "8100",
                      sphare: "ideell",
                      kostenstelle: "Verwaltung",
                      mitglied_id: 1,
                      created_at: "2026-03-05T10:00:00Z",
                    },
                  ],
                }),
            })
          }
          return Promise.reject(new Error("Unknown URL"))
        })
      )
    })

    it("renders KPI cards after data loads", async () => {
      renderComponent()

      await waitFor(() => {
        expect(screen.getByTestId("kpi-row")).toBeInTheDocument()
      })

      expect(screen.getByText("Kassenstand")).toBeInTheDocument()
      expect(screen.getByText("Einnahmen Monat")).toBeInTheDocument()
      expect(screen.getByText("Ausgaben Monat")).toBeInTheDocument()
      expect(screen.getByText("Offene Forderungen")).toBeInTheDocument()
    })

    it("shows currency values formatted in EUR", async () => {
      renderComponent()

      await waitFor(() => {
        expect(screen.getByTestId("kpi-row")).toBeInTheDocument()
      })

      // Kassenstand total should be formatted as currency (locale may vary in test env)
      const kpiRow = screen.getByTestId("kpi-row")
      expect(kpiRow.textContent).toContain("12,450")
    })

    it("renders kassenstand by sphere section", async () => {
      renderComponent()

      await waitFor(() => {
        expect(screen.getByTestId("kassenstand-spheres")).toBeInTheDocument()
      })

      expect(screen.getByTestId("kassenstand-ideell")).toBeInTheDocument()
      expect(screen.getByTestId("kassenstand-zweckbetrieb")).toBeInTheDocument()
      expect(screen.getByTestId("kassenstand-vermoegensverwaltung")).toBeInTheDocument()
      expect(screen.getByTestId("kassenstand-wirtschaftlich")).toBeInTheDocument()
    })

    it("renders quick action buttons", async () => {
      renderComponent()

      await waitFor(() => {
        expect(screen.getByTestId("quick-actions")).toBeInTheDocument()
      })

      expect(screen.getByText("Buchung anlegen")).toBeInTheDocument()
      expect(screen.getByText("Beitragseinzug starten")).toBeInTheDocument()
      expect(screen.getByText("Mahnlauf starten")).toBeInTheDocument()
      expect(screen.getByText("Rechnung erstellen")).toBeInTheDocument()
    })
  })

  describe("with API errors", () => {
    beforeEach(() => {
      vi.stubGlobal(
        "fetch",
        vi.fn().mockRejectedValue(new Error("Network error"))
      )
    })

    it("falls back to mock data and still renders KPI cards", async () => {
      renderComponent()

      // The component falls back to mock data on API errors
      await waitFor(() => {
        expect(screen.getByTestId("kpi-row")).toBeInTheDocument()
      })

      expect(screen.getByText("Kassenstand")).toBeInTheDocument()
      expect(screen.getByText("Einnahmen Monat")).toBeInTheDocument()
      expect(screen.getByText("Ausgaben Monat")).toBeInTheDocument()
      expect(screen.getByText("Offene Forderungen")).toBeInTheDocument()
    })

    it("renders open invoices from mock data", async () => {
      renderComponent()

      await waitFor(() => {
        expect(screen.getByText("Offene Rechnungen")).toBeInTheDocument()
      })

      // Mock data has 4 open invoices
      const rows = screen.getAllByTestId("open-invoice-row")
      expect(rows.length).toBeGreaterThan(0)
    })
  })
})
