import { render, screen } from "@testing-library/react"
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

describe("DashboardPage", () => {
  it("renders top nav with view switcher", () => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    )

    expect(screen.getByText("VereinsOS")).toBeInTheDocument()
    expect(screen.getByText("Vorstand")).toBeInTheDocument()
    expect(screen.getByText("Schatzmeister")).toBeInTheDocument()
    expect(screen.getByText("Spartenleiter")).toBeInTheDocument()
  })

  it("renders Vorstand KPIs by default", () => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    )

    expect(screen.getByText("Mitglieder")).toBeInTheDocument()
    expect(screen.getByText("Kassenstand")).toBeInTheDocument()
    expect(screen.getByText("Offene Posten")).toBeInTheDocument()
    expect(screen.getByText("Compliance")).toBeInTheDocument()
  })

  it("renders Mitgliederentwicklung chart", () => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    )

    expect(screen.getByText("Mitgliederentwicklung")).toBeInTheDocument()
  })

  it("renders interactive KPI cards with role=button", () => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    )

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
    expect(screen.getByText("Sportverein")).toBeInTheDocument()
  })
})
