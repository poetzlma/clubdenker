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
  const MockLine = () => <div data-testid="line" />
  const MockXAxis = () => <div data-testid="x-axis" />
  const MockYAxis = () => <div data-testid="y-axis" />
  const MockCartesianGrid = () => <div data-testid="cartesian-grid" />
  const MockTooltip = () => <div data-testid="tooltip" />

  return {
    ResponsiveContainer: MockResponsiveContainer,
    LineChart: MockLineChart,
    Line: MockLine,
    XAxis: MockXAxis,
    YAxis: MockYAxis,
    CartesianGrid: MockCartesianGrid,
    Tooltip: MockTooltip,
  }
})

describe("DashboardPage", () => {
  it("renders KPI cards", () => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    )

    expect(screen.getByTestId("kpi-cards")).toBeInTheDocument()
    expect(screen.getByText("Aktive Mitglieder")).toBeInTheDocument()
    expect(screen.getByText("Neue diesen Monat")).toBeInTheDocument()
    expect(screen.getByText("Kassenstand")).toBeInTheDocument()
    expect(screen.getByText("Offene Beiträge")).toBeInTheDocument()
  })

  it("renders member trend chart", () => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    )

    expect(screen.getByText("Mitgliederentwicklung")).toBeInTheDocument()
  })

  it("renders recent activity", () => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    )

    expect(screen.getByText("Letzte Aktivitäten")).toBeInTheDocument()
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
