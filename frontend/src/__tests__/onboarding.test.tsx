import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { OnboardingPage } from "@/pages/onboarding"

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockRejectedValue(new Error("No API"))
  )
})

function renderOnboarding() {
  return render(
    <MemoryRouter>
      <OnboardingPage />
    </MemoryRouter>
  )
}

describe("OnboardingPage", () => {
  it("renders the onboarding form", () => {
    renderOnboarding()
    expect(screen.getByText("Schnell-Onboarding")).toBeInTheDocument()
    expect(
      screen.getByText("Neues Mitglied am Infostand schnell registrieren.")
    ).toBeInTheDocument()
  })

  it("renders all required input fields", () => {
    renderOnboarding()
    expect(screen.getByTestId("input-vorname")).toBeInTheDocument()
    expect(screen.getByTestId("input-nachname")).toBeInTheDocument()
    expect(screen.getByTestId("input-email")).toBeInTheDocument()
    expect(screen.getByTestId("input-telefon")).toBeInTheDocument()
    expect(screen.getByTestId("input-geburtsdatum")).toBeInTheDocument()
    expect(screen.getByTestId("input-strasse")).toBeInTheDocument()
    expect(screen.getByTestId("input-plz")).toBeInTheDocument()
    expect(screen.getByTestId("input-ort")).toBeInTheDocument()
  })

  it("renders the submit button", () => {
    renderOnboarding()
    expect(screen.getByTestId("submit-button")).toBeInTheDocument()
    expect(screen.getByTestId("submit-button")).toHaveTextContent(
      "Mitglied anlegen"
    )
  })

  it("renders Abteilungen selector", () => {
    renderOnboarding()
    expect(screen.getByTestId("abteilungen-select")).toBeInTheDocument()
    expect(screen.getByText("Fussball")).toBeInTheDocument()
    expect(screen.getByText("Tennis")).toBeInTheDocument()
  })

  it("shows error when required fields are empty", async () => {
    renderOnboarding()
    fireEvent.click(screen.getByTestId("submit-button"))
    await waitFor(() => {
      expect(screen.getByTestId("error-message")).toHaveTextContent(
        "Bitte mindestens Vorname, Nachname und E-Mail ausfüllen."
      )
    })
  })

  it("shows success state after successful submission", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ id: 1, mitgliedsnummer: "M-001" }),
      })
    )

    renderOnboarding()

    fireEvent.change(screen.getByTestId("input-vorname"), {
      target: { value: "Max" },
    })
    fireEvent.change(screen.getByTestId("input-nachname"), {
      target: { value: "Mustermann" },
    })
    fireEvent.change(screen.getByTestId("input-email"), {
      target: { value: "max@beispiel.de" },
    })
    fireEvent.click(screen.getByTestId("submit-button"))

    await waitFor(() => {
      expect(
        screen.getByText("Mitglied erfolgreich angelegt!")
      ).toBeInTheDocument()
    })

    expect(screen.getByTestId("add-another")).toBeInTheDocument()
  })

  it("resets form when 'add another' is clicked", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ id: 1, mitgliedsnummer: "M-001" }),
      })
    )

    renderOnboarding()

    fireEvent.change(screen.getByTestId("input-vorname"), {
      target: { value: "Max" },
    })
    fireEvent.change(screen.getByTestId("input-nachname"), {
      target: { value: "Mustermann" },
    })
    fireEvent.change(screen.getByTestId("input-email"), {
      target: { value: "max@beispiel.de" },
    })
    fireEvent.click(screen.getByTestId("submit-button"))

    await waitFor(() => {
      expect(screen.getByTestId("add-another")).toBeInTheDocument()
    })

    fireEvent.click(screen.getByTestId("add-another"))

    await waitFor(() => {
      expect(screen.getByTestId("input-vorname")).toBeInTheDocument()
      expect(screen.getByTestId("input-vorname")).toHaveValue("")
    })
  })
})
