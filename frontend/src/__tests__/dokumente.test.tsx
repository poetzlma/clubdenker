import { render, screen } from "@testing-library/react"
import { describe, it, expect, vi } from "vitest"
import { DokumentePage } from "@/pages/dokumente"

// Mock the API module used by child components
vi.mock("@/lib/api", () => ({
  default: {
    get: vi.fn().mockResolvedValue([]),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}))

describe("DokumentePage", () => {
  it("renders the page title", () => {
    render(<DokumentePage />)
    expect(
      screen.getByRole("heading", { name: /Dokumente/i })
    ).toBeInTheDocument()
  })

  it("renders the page description", () => {
    render(<DokumentePage />)
    expect(
      screen.getByText(
        "Protokolle, Vorlagen und Vereinsdokumente verwalten."
      )
    ).toBeInTheDocument()
  })

  it("renders the tab triggers", () => {
    render(<DokumentePage />)
    expect(
      screen.getByRole("tab", { name: /Protokolle/i })
    ).toBeInTheDocument()
    expect(
      screen.getByRole("tab", { name: /Vorlagen/i })
    ).toBeInTheDocument()
  })
})
