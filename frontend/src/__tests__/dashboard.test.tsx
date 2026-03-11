import { render, screen, waitFor } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { describe, it, expect, beforeEach, vi } from "vitest"
import { DashboardPage } from "@/pages/dashboard"
import { Sidebar } from "@/components/layout/sidebar"

// Mock recharts to avoid rendering issues in jsdom
vi.mock("recharts", () => {
  const MockResponsiveContainer = ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  )
  const MockLineChart = ({ children }: { children: React.ReactNode }) => (
    <div data-testid="line-chart">{children}</div>
  )
  const MockAreaChart = ({ children }: { children: React.ReactNode }) => (
    <div data-testid="area-chart">{children}</div>
  )
  const MockBarChart = ({ children }: { children: React.ReactNode }) => (
    <div data-testid="bar-chart">{children}</div>
  )
  const MockPieChart = ({ children }: { children: React.ReactNode }) => (
    <div data-testid="pie-chart">{children}</div>
  )
  const MockLine = () => <div data-testid="line" />
  const MockArea = () => <div data-testid="area" />
  const MockBar = () => <div data-testid="bar" />
  const MockPie = () => <div data-testid="pie" />
  const MockCell = () => <div data-testid="cell" />
  const MockXAxis = () => <div data-testid="x-axis" />
  const MockYAxis = () => <div data-testid="y-axis" />
  const MockCartesianGrid = () => <div data-testid="cartesian-grid" />
  const MockTooltip = () => <div data-testid="tooltip" />

  return {
    ResponsiveContainer: MockResponsiveContainer,
    LineChart: MockLineChart,
    AreaChart: MockAreaChart,
    BarChart: MockBarChart,
    PieChart: MockPieChart,
    Line: MockLine,
    Area: MockArea,
    Bar: MockBar,
    Pie: MockPie,
    Cell: MockCell,
    XAxis: MockXAxis,
    YAxis: MockYAxis,
    CartesianGrid: MockCartesianGrid,
    Tooltip: MockTooltip,
  }
})

// Mock the API module
const mockVorstandResponse = {
  kpis: {
    active_members: 248,
    total_balance: 14520,
    open_fees_count: 23,
    open_fees_amount: 4850,
    compliance_score: 94,
  },
  member_trend: [
    { month: "2026-01", total: 240, by_department: { Fussball: 93, Tennis: 51, Fitness: 48, Leichtathletik: 33 } },
    { month: "2026-02", total: 245, by_department: { Fussball: 94, Tennis: 52, Fitness: 48, Leichtathletik: 33 } },
    { month: "2026-03", total: 248, by_department: { Fussball: 95, Tennis: 53, Fitness: 49, Leichtathletik: 34 } },
  ],
  cashflow: [
    { month: "2026-01", income: 12500, expenses: 6800 },
    { month: "2026-02", income: 8900, expenses: 7100 },
    { month: "2026-03", income: 9300, expenses: 6500 },
  ],
  open_actions: [
    { type: "overdue_fees", title: "Ueberfaellige Beitraege", detail: "3 Rechnungen", severity: "high" },
  ],
}

vi.mock("@/lib/api", () => ({
  default: {
    get: vi.fn().mockImplementation((path: string) => {
      if (path.includes("/api/dashboard/vorstand")) {
        return Promise.resolve(mockVorstandResponse)
      }
      return Promise.resolve({})
    }),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}))

describe("DashboardPage", () => {
  it("renders top nav with view switcher", () => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    )

    expect(screen.getByText("klubdenker.com")).toBeInTheDocument()
    expect(screen.getByText("Vorstand")).toBeInTheDocument()
    expect(screen.getByText("Schatzmeister")).toBeInTheDocument()
    expect(screen.getByText("Spartenleiter")).toBeInTheDocument()
  })

  it("renders Vorstand KPIs after loading", async () => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    )

    // Initially shows loading
    expect(screen.getByText("Laden...")).toBeInTheDocument()

    // After API resolves, shows KPI labels
    await waitFor(() => {
      expect(screen.getByText("Mitglieder")).toBeInTheDocument()
    })
    expect(screen.getByText("Kassenstand")).toBeInTheDocument()
    expect(screen.getByText("Offene Posten")).toBeInTheDocument()
    expect(screen.getByText("Compliance")).toBeInTheDocument()
  })

  it("renders Mitgliederentwicklung chart after loading", async () => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText("Mitgliederentwicklung")).toBeInTheDocument()
    })
  })

  it("renders interactive KPI cards with role=button after loading", async () => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText("Kassenstand")).toBeInTheDocument()
    })

    // Vorstand view has 4 KPI cards; 3 are interactive (have href), 1 (Compliance) is not
    const buttons = screen.getAllByRole("button")
    // Find KPI card buttons by their label text inside
    const mitgliederCard = buttons.find((btn) =>
      btn.textContent?.includes("Mitglieder") && btn.textContent?.includes("vs. Vormonat")
    )
    const kassenstandCard = buttons.find((btn) =>
      btn.textContent?.includes("Kassenstand")
    )
    const offenePostenCard = buttons.find((btn) =>
      btn.textContent?.includes("Offene Posten") && btn.textContent?.includes("vs. Vormonat")
    )

    expect(mitgliederCard).toBeDefined()
    expect(kassenstandCard).toBeDefined()
    expect(offenePostenCard).toBeDefined()
  })
})

describe("Sidebar", () => {
  beforeEach(() => {
    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    )
  })

  it("renders navigation sidebar", () => {
    expect(screen.getByTestId("sidebar")).toBeInTheDocument()
  })

  it("renders nav items", () => {
    expect(screen.getByText("Dashboard")).toBeInTheDocument()
    expect(screen.getByText("Mitglieder")).toBeInTheDocument()
    expect(screen.getByText("Finanzen")).toBeInTheDocument()
    expect(screen.getByText("Admin")).toBeInTheDocument()
  })

  it("renders logo title", () => {
    expect(screen.getByText("Klubdenker")).toBeInTheDocument()
  })
})
