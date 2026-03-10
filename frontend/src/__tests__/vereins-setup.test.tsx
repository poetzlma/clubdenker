import { render, screen, fireEvent } from "@testing-library/react"
import { describe, it, expect, vi } from "vitest"
import { VereinsSetupPage } from "@/pages/vereins-setup"

// Mock the api module to always reject so mock data is used
vi.mock("@/lib/api", () => ({
  default: {
    get: vi.fn().mockRejectedValue(new Error("mock")),
    post: vi.fn().mockRejectedValue(new Error("mock")),
    put: vi.fn().mockRejectedValue(new Error("mock")),
    delete: vi.fn().mockRejectedValue(new Error("mock")),
  },
}))

describe("VereinsSetupPage", () => {
  it("renders the page header", () => {
    render(<VereinsSetupPage />)
    expect(
      screen.getByRole("heading", { name: /vereins-setup/i })
    ).toBeInTheDocument()
    expect(
      screen.getByText("Grundeinstellungen des Vereins verwalten.")
    ).toBeInTheDocument()
  })

  it("renders all 4 tabs", () => {
    render(<VereinsSetupPage />)
    expect(screen.getByRole("tab", { name: /abteilungen/i })).toBeInTheDocument()
    expect(screen.getByRole("tab", { name: /beitragskategorien/i })).toBeInTheDocument()
    expect(screen.getByRole("tab", { name: /kostenstellen/i })).toBeInTheDocument()
    expect(screen.getByRole("tab", { name: /stammdaten/i })).toBeInTheDocument()
  })

  it("shows the Abteilungen table with mock data", async () => {
    render(<VereinsSetupPage />)
    // Abteilungen is the default tab, mock data loads after API rejects
    expect(await screen.findByText("Fussball")).toBeInTheDocument()
    expect(screen.getByText("Tennis")).toBeInTheDocument()
    expect(screen.getByText("Schwimmen")).toBeInTheDocument()
  })

  it("shows 'Neue Abteilung' button that opens dialog", async () => {
    render(<VereinsSetupPage />)
    await screen.findByText("Fussball")
    const btn = screen.getByRole("button", { name: /neue abteilung/i })
    expect(btn).toBeInTheDocument()
    fireEvent.click(btn)
    expect(await screen.findByText("Neue Abteilung", { selector: "[role='dialog'] *" })).toBeInTheDocument()
  })
})
