import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { SepaGenerator } from "@/components/finanzen/sepa-generator"

const mockInvoices = [
  {
    id: 3,
    rechnungsnummer: "RE-2025-003",
    rechnungstyp: "mitgliedsbeitrag",
    status: "faellig",
    mahnstufe: 0,
    empfaenger_typ: "mitglied",
    empfaenger_name: "Weber, Klaus",
    mitglied_id: 3,
    mitglied_name: "Weber, Klaus",
    rechnungsdatum: "2025-01-15",
    faelligkeitsdatum: "2025-02-15",
    summe_netto: 60.0,
    summe_steuer: 0,
    summe_brutto: 60.0,
    betrag: 60.0,
    bezahlt_betrag: 0,
    offener_betrag: 60.0,
    sphaere: "ideell",
    zahlungsziel_tage: 14,
    verwendungszweck: "Jahresbeitrag Jugend 2025",
    positionen: [],
    created_at: "2025-01-15T10:00:00Z",
  },
  {
    id: 5,
    rechnungsnummer: "RE-2025-005",
    rechnungstyp: "mitgliedsbeitrag",
    status: "mahnung_1",
    mahnstufe: 1,
    empfaenger_typ: "mitglied",
    empfaenger_name: "Becker, Stefan",
    mitglied_id: 5,
    mitglied_name: "Becker, Stefan",
    rechnungsdatum: "2025-01-15",
    faelligkeitsdatum: "2025-02-15",
    summe_netto: 120.0,
    summe_steuer: 0,
    summe_brutto: 120.0,
    betrag: 120.0,
    bezahlt_betrag: 0,
    offener_betrag: 120.0,
    sphaere: "ideell",
    zahlungsziel_tage: 14,
    verwendungszweck: "Jahresbeitrag 2025",
    positionen: [],
    created_at: "2025-01-15T10:00:00Z",
  },
  {
    id: 6,
    rechnungsnummer: "RE-2025-006",
    rechnungstyp: "mitgliedsbeitrag",
    status: "faellig",
    mahnstufe: 0,
    empfaenger_typ: "mitglied",
    empfaenger_name: "Hoffmann, Lisa",
    mitglied_id: 6,
    mitglied_name: "Hoffmann, Lisa",
    rechnungsdatum: "2025-01-15",
    faelligkeitsdatum: "2025-02-15",
    summe_netto: 80.0,
    summe_steuer: 0,
    summe_brutto: 80.0,
    betrag: 80.0,
    bezahlt_betrag: 0,
    offener_betrag: 80.0,
    sphaere: "ideell",
    zahlungsziel_tage: 14,
    verwendungszweck: "Jahresbeitrag Passiv 2025",
    positionen: [],
    created_at: "2025-01-15T10:00:00Z",
  },
]

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ items: mockInvoices }),
    })
  )
})

function renderComponent() {
  return render(<SepaGenerator />)
}

describe("SepaGenerator", () => {
  it("renders step indicators", async () => {
    renderComponent()
    await waitFor(() => {
      expect(screen.getByText("Rechnungen auswählen")).toBeInTheDocument()
    })
    expect(screen.getByText("Vorschau")).toBeInTheDocument()
    expect(screen.getByText("Ergebnis")).toBeInTheDocument()
  })

  it("renders invoice list", async () => {
    renderComponent()
    await waitFor(() => {
      expect(screen.getByText("RE-2025-003")).toBeInTheDocument()
    })
    expect(screen.getByText("RE-2025-005")).toBeInTheDocument()
    expect(screen.getByText("RE-2025-006")).toBeInTheDocument()
  })

  it("select and deselect invoice", async () => {
    const user = userEvent.setup()
    renderComponent()

    await waitFor(() => {
      expect(screen.getByText("RE-2025-003")).toBeInTheDocument()
    })

    // The checkboxes are inside labels alongside the invoice info.
    // Get the individual invoice checkboxes (skip the "Alle auswählen" one).
    const checkboxes = screen.getAllByRole("checkbox")
    const invoiceCheckbox = checkboxes[1] // first invoice checkbox

    expect(invoiceCheckbox).not.toBeChecked()

    await user.click(invoiceCheckbox)
    expect(invoiceCheckbox).toBeChecked()

    await user.click(invoiceCheckbox)
    expect(invoiceCheckbox).not.toBeChecked()
  })

  it("shows total for selected invoices", async () => {
    const user = userEvent.setup()
    renderComponent()

    await waitFor(() => {
      expect(screen.getByText("RE-2025-003")).toBeInTheDocument()
    })

    expect(screen.getByText(/0 von 3 ausgewählt/)).toBeInTheDocument()

    const checkboxes = screen.getAllByRole("checkbox")
    // Select first invoice (60 EUR) and second invoice (120 EUR)
    await user.click(checkboxes[1])
    await user.click(checkboxes[2])

    expect(screen.getByText(/2 von 3 ausgewählt/)).toBeInTheDocument()
  })

  it("step navigation - clicking Weiter advances to step 2", async () => {
    const user = userEvent.setup()
    renderComponent()

    await waitFor(() => {
      expect(screen.getByText("RE-2025-003")).toBeInTheDocument()
    })

    // Select an invoice first (Weiter is disabled with 0 selected)
    const checkboxes = screen.getAllByRole("checkbox")
    await user.click(checkboxes[1])

    // Click Weiter
    const weiterButton = screen.getByRole("button", { name: /Weiter/i })
    await user.click(weiterButton)

    // Step 2 shows the preview card with "Vorschau SEPA-Lastschrift"
    await waitFor(() => {
      expect(screen.getByText("Vorschau SEPA-Lastschrift")).toBeInTheDocument()
    })
    // The selected invoice should appear in the preview
    expect(screen.getByText("RE-2025-003")).toBeInTheDocument()
    // Step 2 has a "SEPA-XML generieren" button
    expect(screen.getByRole("button", { name: /SEPA-XML generieren/i })).toBeInTheDocument()
  })
})
