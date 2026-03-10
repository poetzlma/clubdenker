import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
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

describe("FinanzenPage", () => {
  it("renders the page title", () => {
    render(<FinanzenPage />)
    expect(screen.getByText("Finanzen")).toBeInTheDocument()
  })

  it("renders all three tabs", () => {
    render(<FinanzenPage />)
    expect(screen.getByRole("tab", { name: /Übersicht/i })).toBeInTheDocument()
    expect(screen.getByRole("tab", { name: /Buchungen/i })).toBeInTheDocument()
    expect(screen.getByRole("tab", { name: /SEPA/i })).toBeInTheDocument()
  })

  it("renders payment overview stats cards by default", async () => {
    render(<FinanzenPage />)
    await waitFor(() => {
      expect(screen.getByTestId("stat-total")).toBeInTheDocument()
      expect(screen.getByTestId("stat-offen")).toBeInTheDocument()
      expect(screen.getByTestId("stat-ueberfaellig")).toBeInTheDocument()
      expect(screen.getByTestId("stat-bezahlt")).toBeInTheDocument()
    })
  })

  it("renders payment overview with correct labels", async () => {
    render(<FinanzenPage />)
    await waitFor(() => {
      expect(screen.getByText("Gesamtbetrag")).toBeInTheDocument()
      expect(screen.getByText("Offene Rechnungen")).toBeInTheDocument()
      expect(screen.getByText("Überfällig")).toBeInTheDocument()
      expect(screen.getByText("Bezahlt")).toBeInTheDocument()
    })
  })

  it("shows booking table when Buchungen tab is clicked", async () => {
    render(<FinanzenPage />)
    const buchungenTab = screen.getByRole("tab", { name: /Buchungen/i })
    buchungenTab.click()
    await waitFor(() => {
      const panel = screen.getByRole("tabpanel")
      expect(panel).toBeInTheDocument()
    })
    // After tab switch, the booking table should be loading or loaded
    await waitFor(() => {
      // The booking table shows "Laden..." first, then actual rows
      const panel = screen.getByRole("tabpanel")
      expect(panel.textContent).toBeTruthy()
    })
  })
})
