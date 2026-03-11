import { render, screen } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { describe, it, expect, vi } from "vitest"
import { LoginPage } from "@/pages/login"

describe("LoginPage", () => {
  const mockOnLogin = vi.fn()

  function renderPage() {
    return render(
      <MemoryRouter>
        <LoginPage onLogin={mockOnLogin} />
      </MemoryRouter>
    )
  }

  it("renders the Sportverein title", () => {
    renderPage()
    expect(screen.getByText("Sportverein")).toBeInTheDocument()
  })

  it("renders the login description", () => {
    renderPage()
    expect(
      screen.getByText("Bitte melden Sie sich an, um fortzufahren.")
    ).toBeInTheDocument()
  })

  it("renders the Anmeldung and API Token tabs", () => {
    renderPage()
    expect(screen.getByRole("tab", { name: /Anmeldung/i })).toBeInTheDocument()
    expect(screen.getByRole("tab", { name: /API Token/i })).toBeInTheDocument()
  })

  it("renders email and password fields in the login tab", () => {
    renderPage()
    expect(screen.getByLabelText("E-Mail")).toBeInTheDocument()
    expect(screen.getByLabelText("Passwort")).toBeInTheDocument()
  })

  it("renders the Anmelden button", () => {
    renderPage()
    expect(
      screen.getByRole("button", { name: /Anmelden/i })
    ).toBeInTheDocument()
  })

  it("renders the onboarding link", () => {
    renderPage()
    expect(
      screen.getByText("Schnell-Onboarding (Infostand)")
    ).toBeInTheDocument()
  })
})
