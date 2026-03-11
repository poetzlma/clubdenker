import { render, screen, waitFor } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { describe, it, expect, vi } from "vitest"
import { MitgliederPage } from "@/pages/mitglieder"

// Mock the API module
vi.mock("@/lib/api", () => ({
  default: {
    get: vi.fn().mockImplementation((path: string) => {
      if (path.includes("/api/mitglieder")) {
        return Promise.resolve({ items: [], total: 0 })
      }
      return Promise.resolve({})
    }),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}))

describe("MitgliederPage", () => {
  function renderPage() {
    return render(
      <MemoryRouter>
        <MitgliederPage />
      </MemoryRouter>
    )
  }

  it("renders the page title", () => {
    renderPage()
    expect(
      screen.getByRole("heading", { name: /Mitglieder/i })
    ).toBeInTheDocument()
  })

  it("renders the page description", () => {
    renderPage()
    expect(
      screen.getByText("Verwalten Sie die Mitglieder Ihres Vereins.")
    ).toBeInTheDocument()
  })

  it("renders the Neues Mitglied button", () => {
    renderPage()
    expect(
      screen.getByRole("button", { name: /Neues Mitglied/i })
    ).toBeInTheDocument()
  })

  it("shows loading state initially", () => {
    renderPage()
    expect(screen.getByText("Laden...")).toBeInTheDocument()
  })

  it("renders member table after loading", async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.queryByText("Laden...")).not.toBeInTheDocument()
    })
  })
})
