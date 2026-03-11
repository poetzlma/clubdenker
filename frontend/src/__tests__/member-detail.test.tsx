import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, it, expect, vi } from "vitest"
import { MemberDetail } from "@/components/mitglieder/member-detail"
import type { Member } from "@/types/member"

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
  abteilungen: ["Fußball", "Tennis"],
}

function renderDetail(overrides: Partial<Parameters<typeof MemberDetail>[0]> = {}) {
  return render(
    <MemberDetail
      open={true}
      onOpenChange={vi.fn()}
      member={sampleMember}
      onEdit={vi.fn()}
      onCancel={vi.fn().mockResolvedValue(undefined)}
      onAddDepartment={vi.fn().mockResolvedValue(undefined)}
      onRemoveDepartment={vi.fn().mockResolvedValue(undefined)}
      {...overrides}
    />
  )
}

describe("MemberDetail", () => {
  it("renders member name and mitgliedsnummer", () => {
    renderDetail()
    expect(screen.getByText("Max Mustermann")).toBeInTheDocument()
    expect(screen.getByText(/M-001/)).toBeInTheDocument()
  })

  it("renders nothing when member is null", () => {
    const { container } = render(
      <MemberDetail
        open={true}
        onOpenChange={vi.fn()}
        member={null}
      />
    )
    expect(container.innerHTML).toBe("")
  })

  it("displays stammdaten fields in the default tab", () => {
    renderDetail()
    expect(screen.getByText("max@beispiel.de")).toBeInTheDocument()
    expect(screen.getByText("+49 170 1234567")).toBeInTheDocument()
    expect(screen.getByText("Musterstr. 1")).toBeInTheDocument()
    expect(screen.getByText("Erwachsene")).toBeInTheDocument()
    expect(screen.getByText("Testnotiz")).toBeInTheDocument()
  })

  it("shows cancel confirmation flow", async () => {
    const user = userEvent.setup()
    const onCancel = vi.fn().mockResolvedValue(undefined)
    renderDetail({ onCancel })

    // Click "Kündigen" button
    const cancelBtn = screen.getByRole("button", { name: "Kündigen" })
    await user.click(cancelBtn)

    // Confirmation prompt appears
    expect(screen.getByText("Wirklich kündigen?")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Ja" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Nein" })).toBeInTheDocument()
  })

  it("calls onCancel when confirmed", async () => {
    const user = userEvent.setup()
    const onCancel = vi.fn().mockResolvedValue(undefined)
    const onOpenChange = vi.fn()
    renderDetail({ onCancel, onOpenChange })

    await user.click(screen.getByRole("button", { name: "Kündigen" }))
    await user.click(screen.getByRole("button", { name: "Ja" }))

    await waitFor(() => {
      expect(onCancel).toHaveBeenCalledWith(sampleMember)
    })
  })

  it("hides Kündigen button for gekuendigt members", () => {
    const gekuendigtMember = { ...sampleMember, status: "gekuendigt" as const }
    renderDetail({ member: gekuendigtMember })
    expect(screen.queryByRole("button", { name: "Kündigen" })).not.toBeInTheDocument()
  })

  it("calls onEdit when Bearbeiten is clicked", async () => {
    const user = userEvent.setup()
    const onEdit = vi.fn()
    renderDetail({ onEdit })

    await user.click(screen.getByRole("button", { name: "Bearbeiten" }))
    expect(onEdit).toHaveBeenCalledWith(sampleMember)
  })

  it("shows departments in the Abteilungen tab", async () => {
    const user = userEvent.setup()
    renderDetail()

    await user.click(screen.getByRole("tab", { name: "Abteilungen" }))

    await waitFor(() => {
      expect(screen.getByText("Fußball")).toBeInTheDocument()
      expect(screen.getByText("Tennis")).toBeInTheDocument()
    })
  })

  it("shows available departments to add", async () => {
    const user = userEvent.setup()
    renderDetail()

    await user.click(screen.getByRole("tab", { name: "Abteilungen" }))

    await waitFor(() => {
      // Schwimmen is not in member's departments, so it should be addable
      expect(screen.getByText("+ Schwimmen")).toBeInTheDocument()
      expect(screen.getByText("+ Leichtathletik")).toBeInTheDocument()
    })
  })
})
