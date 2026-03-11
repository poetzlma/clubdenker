import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter } from "react-router-dom"
import { AgentDashboard } from "@/components/admin/agent-dashboard"

function renderComponent() {
  return render(
    <MemoryRouter>
      <AgentDashboard />
    </MemoryRouter>
  )
}

describe("AgentDashboard", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new Error("No API"))
    )
  })

  it("renders all 4 agent cards", () => {
    renderComponent()

    expect(screen.getByTestId("agent-beitragseinzug")).toBeInTheDocument()
    expect(screen.getByTestId("agent-mahnwesen")).toBeInTheDocument()
    expect(screen.getByTestId("agent-aufwand")).toBeInTheDocument()
    expect(screen.getByTestId("agent-compliance")).toBeInTheDocument()
  })

  it("renders card titles for all agents", () => {
    renderComponent()

    expect(screen.getByText("Beitragseinzug")).toBeInTheDocument()
    expect(screen.getByText("Mahnwesen")).toBeInTheDocument()
    expect(screen.getByText("Aufwands-Monitor")).toBeInTheDocument()
    expect(screen.getByText("Compliance-Monitor")).toBeInTheDocument()
  })

  it("renders execute buttons for all agents", () => {
    renderComponent()

    expect(screen.getByTestId("run-beitragseinzug")).toBeInTheDocument()
    expect(screen.getByTestId("run-mahnwesen")).toBeInTheDocument()
    expect(screen.getByTestId("run-aufwand")).toBeInTheDocument()
    expect(screen.getByTestId("run-compliance")).toBeInTheDocument()
  })

  it("shows loading state when Beitragseinzug is running", async () => {
    // fetch never resolves to keep the agent in loading state
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation(() => new Promise(() => {}))
    )
    const user = userEvent.setup()
    renderComponent()

    const btn = screen.getByTestId("run-beitragseinzug")
    await user.click(btn)

    // Button should be disabled during loading
    expect(btn).toBeDisabled()
  })

  it("shows loading state when Mahnwesen is running", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation(() => new Promise(() => {}))
    )
    const user = userEvent.setup()
    renderComponent()

    const btn = screen.getByTestId("run-mahnwesen")
    await user.click(btn)

    expect(btn).toBeDisabled()
  })

  it("handles Beitragseinzug execution success and shows result", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: "completed",
            year: 2026,
            month: 3,
            processed: 42,
            total_amount: 5040,
            errors: [],
          }),
      })
    )
    const user = userEvent.setup()
    renderComponent()

    await user.click(screen.getByTestId("run-beitragseinzug"))

    await waitFor(() => {
      expect(screen.getByText("42")).toBeInTheDocument()
    })
  })

  it("handles Mahnwesen execution success and shows result", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: "completed",
            reminders_sent: 3,
            overdue_members: 5,
            total_overdue_amount: 360,
          }),
      })
    )
    const user = userEvent.setup()
    renderComponent()

    await user.click(screen.getByTestId("run-mahnwesen"))

    await waitFor(() => {
      expect(screen.getByText("3")).toBeInTheDocument()
      expect(screen.getByText("5")).toBeInTheDocument()
    })
  })

  it("handles agent execution error by falling back to mock data", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new Error("API error"))
    )
    const user = userEvent.setup()
    renderComponent()

    await user.click(screen.getByTestId("run-beitragseinzug"))

    // On error, the component falls back to mock data with processed: 42
    await waitFor(() => {
      expect(screen.getByText("42")).toBeInTheDocument()
    })
  })

  it("handles Aufwand-Monitor execution and shows cost center warnings", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new Error("API error"))
    )
    const user = userEvent.setup()
    renderComponent()

    await user.click(screen.getByTestId("run-aufwand"))

    // Falls back to mock data with cost center warnings
    await waitFor(() => {
      expect(screen.getByText("Tennis")).toBeInTheDocument()
      expect(screen.getByText("85% Auslastung")).toBeInTheDocument()
    })
  })

  it("handles Compliance-Monitor execution and shows findings", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new Error("API error"))
    )
    const user = userEvent.setup()
    renderComponent()

    await user.click(screen.getByTestId("run-compliance"))

    // Falls back to mock data with compliance findings
    await waitFor(() => {
      expect(
        screen.getByText("Freistellungsbescheid laeuft in 45 Tagen ab.")
      ).toBeInTheDocument()
      expect(screen.getByText("Warnung")).toBeInTheDocument()
    })
  })
})
