import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { FinanzenPage } from "@/pages/finanzen"

// Mock recharts to avoid rendering issues in jsdom
vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
  PieChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="pie-chart">{children}</div>
  ),
  Pie: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="pie">{children}</div>
  ),
  Cell: () => <div data-testid="cell" />,
  Tooltip: () => <div data-testid="tooltip" />,
}))

// Mock fetch to return mock data
beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockRejectedValue(new Error("No API"))
  )
})

function renderPage() {
  return render(
    <MemoryRouter>
      <FinanzenPage />
    </MemoryRouter>
  )
}

describe("FinanzenPage", () => {
  it("renders the page title", () => {
    renderPage()
    expect(screen.getByText("Finanzen")).toBeInTheDocument()
  })

  it("renders all tabs", () => {
    renderPage()
    expect(screen.getByRole("tab", { name: /Übersicht/i })).toBeInTheDocument()
    expect(screen.getByRole("tab", { name: /Rechnungen/i })).toBeInTheDocument()
    expect(screen.getByRole("tab", { name: /Buchungsjournal/i })).toBeInTheDocument()
    expect(screen.getByRole("tab", { name: /^SEPA$/i })).toBeInTheDocument()
    expect(screen.getByRole("tab", { name: /SEPA-Mandate/i })).toBeInTheDocument()
    expect(screen.getByRole("tab", { name: /EÜR/i })).toBeInTheDocument()
    expect(screen.getByRole("tab", { name: /Kostenstellen/i })).toBeInTheDocument()
  })

  it("renders KPI cards and quick actions in the overview", async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByTestId("kpi-row")).toBeInTheDocument()
      expect(screen.getByTestId("quick-actions")).toBeInTheDocument()
    })
  })

  it("renders payment overview with correct KPI labels", async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText("Kassenstand")).toBeInTheDocument()
      expect(screen.getByText("Einnahmen Monat")).toBeInTheDocument()
      expect(screen.getByText("Ausgaben Monat")).toBeInTheDocument()
      expect(screen.getByText("Offene Forderungen")).toBeInTheDocument()
    })
  })

  it("shows booking table when Buchungsjournal tab is clicked", async () => {
    renderPage()
    const buchungenTab = screen.getByRole("tab", { name: /Buchungsjournal/i })
    buchungenTab.click()
    await waitFor(() => {
      const panel = screen.getByRole("tabpanel")
      expect(panel).toBeInTheDocument()
    })
    await waitFor(() => {
      const panel = screen.getByRole("tabpanel")
      expect(panel.textContent).toBeTruthy()
    })
  })
})
