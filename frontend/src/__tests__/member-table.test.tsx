import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { MemberTable } from "@/components/mitglieder/member-table"
import type { Member } from "@/types/member"

const mockMembers: Member[] = [
  {
    id: 1,
    mitgliedsnummer: "M-001",
    vorname: "Max",
    nachname: "Mustermann",
    email: "max@beispiel.de",
    telefon: "+49 170 1234567",
    geburtsdatum: "1990-05-15",
    strasse: "Hauptstraße 1",
    plz: "10115",
    ort: "Berlin",
    eintrittsdatum: "2020-01-15",
    austrittsdatum: null,
    status: "aktiv",
    beitragskategorie: "erwachsene",
    notizen: null,
    abteilungen: ["Fußball", "Tennis"],
  },
  {
    id: 2,
    mitgliedsnummer: "M-002",
    vorname: "Anna",
    nachname: "Schmidt",
    email: "anna@beispiel.de",
    telefon: "+49 171 9876543",
    geburtsdatum: "1985-08-22",
    strasse: "Gartenweg 5",
    plz: "80331",
    ort: "München",
    eintrittsdatum: "2019-06-01",
    austrittsdatum: null,
    status: "passiv",
    beitragskategorie: "passiv",
    notizen: null,
    abteilungen: ["Tennis"],
  },
  {
    id: 3,
    mitgliedsnummer: "M-003",
    vorname: "Stefan",
    nachname: "Weber",
    email: "stefan@beispiel.de",
    telefon: "",
    geburtsdatum: "1978-07-04",
    strasse: "Lindenstraße 8",
    plz: "60313",
    ort: "Frankfurt",
    eintrittsdatum: "2018-02-15",
    austrittsdatum: "2024-12-31",
    status: "gekuendigt",
    beitragskategorie: "erwachsene",
    notizen: null,
    abteilungen: ["Handball"],
  },
]

describe("MemberTable", () => {
  it("renders the member table", () => {
    render(<MemberTable data={mockMembers} />)

    // Check table headers
    expect(screen.getByText("Name")).toBeInTheDocument()
    expect(screen.getByText("E-Mail")).toBeInTheDocument()
    expect(screen.getByText("Abteilung(en)")).toBeInTheDocument()
    expect(screen.getByText("Status")).toBeInTheDocument()
    expect(screen.getByText("Beitragskategorie")).toBeInTheDocument()
    expect(screen.getByText("Eintrittsdatum")).toBeInTheDocument()
  })

  it("renders filter controls", () => {
    render(<MemberTable data={mockMembers} />)

    expect(screen.getByTestId("name-filter")).toBeInTheDocument()
    expect(screen.getByTestId("status-filter")).toBeInTheDocument()
    expect(screen.getByTestId("department-filter")).toBeInTheDocument()
  })

  it("renders mock data rows", () => {
    render(<MemberTable data={mockMembers} />)

    // Check member names render
    expect(screen.getByText("Max Mustermann")).toBeInTheDocument()
    expect(screen.getByText("Anna Schmidt")).toBeInTheDocument()
    expect(screen.getByText("Stefan Weber")).toBeInTheDocument()

    // Check emails
    expect(screen.getByText("max@beispiel.de")).toBeInTheDocument()
    expect(screen.getByText("anna@beispiel.de")).toBeInTheDocument()

    // Check statuses
    expect(screen.getByText("Aktiv")).toBeInTheDocument()
    expect(screen.getAllByText("Passiv").length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText("Gekündigt")).toBeInTheDocument()

    // Check rows are present
    const rows = screen.getAllByTestId("member-row")
    expect(rows).toHaveLength(3)
  })

  it("renders pagination controls", () => {
    render(<MemberTable data={mockMembers} />)

    expect(screen.getByTestId("prev-page")).toBeInTheDocument()
    expect(screen.getByTestId("next-page")).toBeInTheDocument()
    expect(screen.getByText(/Seite 1 von/)).toBeInTheDocument()
  })
})
