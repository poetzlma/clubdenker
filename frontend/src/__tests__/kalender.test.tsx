import { render, screen } from "@testing-library/react"
import { describe, it, expect, vi } from "vitest"
import { KalenderPage } from "@/pages/kalender"

// Mock the API module
vi.mock("@/lib/api", () => ({
  default: {
    get: vi.fn().mockResolvedValue([]),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}))

describe("KalenderPage", () => {
  it("renders the page title", () => {
    render(<KalenderPage />)
    expect(
      screen.getByRole("heading", { name: /Kalender/i })
    ).toBeInTheDocument()
  })

  it("renders the page description", () => {
    render(<KalenderPage />)
    expect(
      screen.getByText("Wochenansicht aller Trainingseinheiten.")
    ).toBeInTheDocument()
  })

  it("renders the Heute button", () => {
    render(<KalenderPage />)
    expect(
      screen.getByRole("button", { name: /Heute/i })
    ).toBeInTheDocument()
  })

  it("renders navigation buttons", () => {
    render(<KalenderPage />)
    // There should be prev/next buttons (icon buttons)
    const buttons = screen.getAllByRole("button")
    expect(buttons.length).toBeGreaterThanOrEqual(3)
  })

  it("shows loading state initially", () => {
    render(<KalenderPage />)
    expect(screen.getByText("Laden...")).toBeInTheDocument()
  })
})
