import { render, screen } from "@testing-library/react"
import { describe, it, expect } from "vitest"
import { AdminPage } from "@/pages/admin"

describe("AdminPage", () => {
  it("renders the admin page header", () => {
    render(<AdminPage />)
    expect(
      screen.getByRole("heading", { name: /administration/i })
    ).toBeInTheDocument()
  })

  it("renders the token management section", () => {
    render(<AdminPage />)
    expect(screen.getByText("API-Token Verwaltung")).toBeInTheDocument()
  })

  it("renders the token table with headers", () => {
    render(<AdminPage />)
    expect(screen.getByText("Name")).toBeInTheDocument()
    expect(screen.getByText("Erstellt am")).toBeInTheDocument()
    expect(screen.getByText("Zuletzt verwendet")).toBeInTheDocument()
    expect(screen.getByText("Status")).toBeInTheDocument()
    expect(screen.getByText("Aktionen")).toBeInTheDocument()
  })

  it("renders mock token rows", () => {
    render(<AdminPage />)
    expect(screen.getByText("Backend-Service")).toBeInTheDocument()
    expect(screen.getByText("CI/CD Pipeline")).toBeInTheDocument()
    expect(screen.getByText("Alter Testtoken")).toBeInTheDocument()
  })

  it("renders the create button", () => {
    render(<AdminPage />)
    expect(
      screen.getByRole("button", { name: /neuer token/i })
    ).toBeInTheDocument()
  })

  it("renders active and inactive badges", () => {
    render(<AdminPage />)
    const activeBadges = screen.getAllByText("aktiv")
    const inactiveBadges = screen.getAllByText("inaktiv")
    expect(activeBadges.length).toBe(2)
    expect(inactiveBadges.length).toBe(1)
  })
})
