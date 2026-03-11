import { render, screen, waitFor } from "@testing-library/react"
import { describe, it, expect, vi, beforeEach } from "vitest"
import { AuditLogViewer } from "@/components/admin/audit-log-viewer"

// Mock fetch to fail so the component falls back to mock data
beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockRejectedValue(new Error("network error"))
  )
})

describe("AuditLogViewer", () => {
  it("renders the title and table headers", async () => {
    render(<AuditLogViewer />)

    await waitFor(() => {
      expect(screen.getByText("Protokoll")).toBeInTheDocument()
    })

    // Wait for loading to finish and table headers to appear
    await waitFor(() => {
      expect(screen.getByText("Zeitpunkt")).toBeInTheDocument()
      expect(screen.getByText("Benutzer")).toBeInTheDocument()
      expect(screen.getByText("Aktion")).toBeInTheDocument()
      expect(screen.getByText("Bereich")).toBeInTheDocument()
      expect(screen.getByText("Details")).toBeInTheDocument()
    })
  })

  it("shows loading state initially", () => {
    render(<AuditLogViewer />)
    expect(screen.getByText("Laden...")).toBeInTheDocument()
  })

  it("renders audit entries from mock data after loading", async () => {
    render(<AuditLogViewer />)

    await waitFor(() => {
      expect(screen.queryByText("Laden...")).not.toBeInTheDocument()
    })

    // Check some entries from the mock data
    expect(screen.getByText(/Weber, Thomas angelegt/)).toBeInTheDocument()
    expect(screen.getByText(/Buchung #42 geändert/)).toBeInTheDocument()
  })

  it("displays total entries count", async () => {
    render(<AuditLogViewer />)

    await waitFor(() => {
      expect(screen.getByText("10 Einträge gesamt")).toBeInTheDocument()
    })
  })

  it("renders action badges with correct labels", async () => {
    render(<AuditLogViewer />)

    await waitFor(() => {
      expect(screen.queryByText("Laden...")).not.toBeInTheDocument()
    })

    // Check action badges
    const erstellt = screen.getAllByText("Erstellt")
    expect(erstellt.length).toBeGreaterThan(0)

    const aktualisiert = screen.getAllByText("Aktualisiert")
    expect(aktualisiert.length).toBeGreaterThan(0)

    const geloescht = screen.getAllByText("Gelöscht")
    expect(geloescht.length).toBeGreaterThan(0)
  })

  it("renders entity type labels in German", async () => {
    render(<AuditLogViewer />)

    await waitFor(() => {
      expect(screen.queryByText("Laden...")).not.toBeInTheDocument()
    })

    // Entity types from mock data
    expect(screen.getAllByText("Mitglied").length).toBeGreaterThan(0)
    expect(screen.getAllByText("Buchung").length).toBeGreaterThan(0)
    expect(screen.getAllByText("Rechnung").length).toBeGreaterThan(0)
  })

  it("renders with API data when fetch succeeds", async () => {
    const apiEntries = [
      {
        id: 100,
        user_id: 1,
        action: "create",
        entity_type: "mitglied",
        entity_id: 99,
        details: "API-Testeintrag",
        ip_address: "10.0.0.1",
        created_at: "2026-03-11T10:00:00Z",
      },
    ]

    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ items: apiEntries, total: 1 }),
      })
    )

    render(<AuditLogViewer />)

    await waitFor(() => {
      expect(screen.getByText("API-Testeintrag")).toBeInTheDocument()
      expect(screen.getByText("1 Einträge gesamt")).toBeInTheDocument()
    })
  })
})
