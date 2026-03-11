import { render, screen } from "@testing-library/react"
import { describe, it, expect, vi } from "vitest"
import { TrainingPage } from "@/pages/training"

// Mock the API module used by child components
vi.mock("@/lib/api", () => ({
  default: {
    get: vi.fn().mockResolvedValue([]),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}))

describe("TrainingPage", () => {
  it("renders the page title", () => {
    render(<TrainingPage />)
    expect(
      screen.getByRole("heading", { name: /Training/i })
    ).toBeInTheDocument()
  })

  it("renders the page description", () => {
    render(<TrainingPage />)
    expect(
      screen.getByText(
        "Trainingsgruppen, Anwesenheiten und Lizenzen verwalten."
      )
    ).toBeInTheDocument()
  })

  it("renders the tab triggers", () => {
    render(<TrainingPage />)
    expect(
      screen.getByRole("tab", { name: /Trainingsgruppen/i })
    ).toBeInTheDocument()
    expect(
      screen.getByRole("tab", { name: /Anwesenheit/i })
    ).toBeInTheDocument()
    expect(
      screen.getByRole("tab", { name: /Lizenzen/i })
    ).toBeInTheDocument()
  })
})
