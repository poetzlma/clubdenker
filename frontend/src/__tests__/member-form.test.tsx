import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, it, expect, vi, beforeEach } from "vitest"
import { MemberForm } from "@/components/mitglieder/member-form"
import type { Member } from "@/types/member"

// Mock fetch for the departments API call
beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve([
          { name: "Fussball" },
          { name: "Tennis" },
          { name: "Schwimmen" },
        ]),
    })
  )
})

const noop = vi.fn().mockResolvedValue(undefined)

function renderForm(props: { member?: Member | null } = {}) {
  return render(
    <MemberForm
      open={true}
      onOpenChange={vi.fn()}
      onSubmit={noop}
      member={props.member ?? null}
    />
  )
}

const sampleMember: Member = {
  id: 1,
  mitgliedsnummer: "M-001",
  vorname: "Max",
  nachname: "Mustermann",
  email: "max@beispiel.de",
  telefon: "+49 170 1234567",
  geburtsdatum: "1990-05-15",
  strasse: "Musterstr. 1",
  plz: "12345",
  ort: "Musterstadt",
  eintrittsdatum: "2023-01-01",
  austrittsdatum: null,
  status: "aktiv",
  beitragskategorie: "erwachsene",
  notizen: "Testnotiz",
  abteilungen: ["Fussball"],
}

describe("MemberForm", () => {
  it("renders all form fields", async () => {
    renderForm()

    // Labels for required fields
    expect(screen.getByPlaceholderText("Vorname")).toBeInTheDocument()
    expect(screen.getByPlaceholderText("Nachname")).toBeInTheDocument()
    expect(screen.getByPlaceholderText("email@beispiel.de")).toBeInTheDocument()
    expect(screen.getByPlaceholderText("+49 ...")).toBeInTheDocument()

    // Geburtsdatum is a date input (no placeholder), check by label
    expect(screen.getByText("Geburtsdatum")).toBeInTheDocument()

    // Address fields
    expect(screen.getByPlaceholderText("Musterstraße 1")).toBeInTheDocument()
    expect(screen.getByPlaceholderText("12345")).toBeInTheDocument()
    expect(screen.getByPlaceholderText("Musterstadt")).toBeInTheDocument()

    // Beitragskategorie select
    expect(screen.getByText("Beitragskategorie")).toBeInTheDocument()

    // Notizen textarea
    expect(
      screen.getByPlaceholderText("Zusätzliche Notizen...")
    ).toBeInTheDocument()
  })

  it("renders submit button with 'Erstellen' for new member", () => {
    renderForm()
    expect(
      screen.getByRole("button", { name: /Erstellen/i })
    ).toBeInTheDocument()
  })

  it("renders submit button with 'Aktualisieren' for editing", () => {
    renderForm({ member: sampleMember })
    expect(
      screen.getByRole("button", { name: /Aktualisieren/i })
    ).toBeInTheDocument()
  })

  it("shows validation errors on empty submit", async () => {
    const user = userEvent.setup()
    renderForm()

    const submitButton = screen.getByRole("button", { name: /Erstellen/i })
    await user.click(submitButton)

    await waitFor(() => {
      expect(
        screen.getByText("Vorname ist erforderlich")
      ).toBeInTheDocument()
      expect(
        screen.getByText("Nachname ist erforderlich")
      ).toBeInTheDocument()
      expect(
        screen.getByText("E-Mail ist erforderlich")
      ).toBeInTheDocument()
      expect(
        screen.getByText("Geburtsdatum ist erforderlich")
      ).toBeInTheDocument()
    })

    // onSubmit should not have been called
    expect(noop).not.toHaveBeenCalled()
  })

  it("pre-fills form fields in edit mode", () => {
    renderForm({ member: sampleMember })

    expect(screen.getByPlaceholderText("Vorname")).toHaveValue("Max")
    expect(screen.getByPlaceholderText("Nachname")).toHaveValue("Mustermann")
    expect(screen.getByPlaceholderText("email@beispiel.de")).toHaveValue(
      "max@beispiel.de"
    )
    expect(screen.getByPlaceholderText("+49 ...")).toHaveValue(
      "+49 170 1234567"
    )
    expect(screen.getByPlaceholderText("Musterstraße 1")).toHaveValue(
      "Musterstr. 1"
    )
    expect(screen.getByPlaceholderText("12345")).toHaveValue("12345")
    expect(screen.getByPlaceholderText("Musterstadt")).toHaveValue(
      "Musterstadt"
    )
  })

  it("shows dialog title 'Neues Mitglied' for new member", () => {
    renderForm()
    expect(
      screen.getByText("Neues Mitglied")
    ).toBeInTheDocument()
  })

  it("shows dialog title 'Mitglied bearbeiten' in edit mode", () => {
    renderForm({ member: sampleMember })
    expect(
      screen.getByText("Mitglied bearbeiten")
    ).toBeInTheDocument()
  })

  it("renders department buttons in create mode", async () => {
    renderForm()
    await waitFor(() => {
      expect(screen.getByText("Fussball")).toBeInTheDocument()
      expect(screen.getByText("Tennis")).toBeInTheDocument()
      expect(screen.getByText("Schwimmen")).toBeInTheDocument()
    })
  })

  it("hides department buttons in edit mode", () => {
    renderForm({ member: sampleMember })
    expect(screen.queryByText("Abteilungen")).not.toBeInTheDocument()
  })

  it("clears validation error when field is filled", async () => {
    const user = userEvent.setup()
    renderForm()

    // Trigger validation
    await user.click(screen.getByRole("button", { name: /Erstellen/i }))
    await waitFor(() => {
      expect(
        screen.getByText("Vorname ist erforderlich")
      ).toBeInTheDocument()
    })

    // Fill the vorname field
    await user.type(screen.getByPlaceholderText("Vorname"), "Anna")

    // Error should be cleared
    await waitFor(() => {
      expect(
        screen.queryByText("Vorname ist erforderlich")
      ).not.toBeInTheDocument()
    })
  })
})
