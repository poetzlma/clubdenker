import { useState, useEffect, useCallback } from "react"
import type { Member } from "@/types/member"
import type { MemberFormData } from "@/components/mitglieder/member-form"
import { MemberTable } from "@/components/mitglieder/member-table"
import { MemberForm } from "@/components/mitglieder/member-form"
import { MemberDetail } from "@/components/mitglieder/member-detail"
import { Plus } from "lucide-react"

const API_BASE = "/api"

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
    status: "aktiv",
    beitragskategorie: "erwachsene",
    notizen: "Trainerin Jugend-Tennis",
    abteilungen: ["Tennis"],
  },
  {
    id: 3,
    mitgliedsnummer: "M-003",
    vorname: "Tom",
    nachname: "Klein",
    email: "tom@beispiel.de",
    telefon: "+49 172 5555555",
    geburtsdatum: "2008-03-10",
    strasse: "Schulstraße 12",
    plz: "50667",
    ort: "Köln",
    eintrittsdatum: "2021-09-01",
    austrittsdatum: null,
    status: "aktiv",
    beitragskategorie: "jugend",
    notizen: null,
    abteilungen: ["Schwimmen", "Leichtathletik"],
  },
  {
    id: 4,
    mitgliedsnummer: "M-004",
    vorname: "Erika",
    nachname: "Müller",
    email: "erika@beispiel.de",
    telefon: "",
    geburtsdatum: "1945-11-30",
    strasse: "Am Park 3",
    plz: "20095",
    ort: "Hamburg",
    eintrittsdatum: "1975-04-01",
    austrittsdatum: null,
    status: "ehrenmitglied",
    beitragskategorie: "ehrenmitglied",
    notizen: "Gründungsmitglied",
    abteilungen: ["Turnen"],
  },
  {
    id: 5,
    mitgliedsnummer: "M-005",
    vorname: "Stefan",
    nachname: "Weber",
    email: "stefan@beispiel.de",
    telefon: "+49 173 1111111",
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
  {
    id: 6,
    mitgliedsnummer: "M-006",
    vorname: "Laura",
    nachname: "Fischer",
    email: "laura@beispiel.de",
    telefon: "+49 174 2222222",
    geburtsdatum: "1995-12-20",
    strasse: "Waldweg 2",
    plz: "70173",
    ort: "Stuttgart",
    eintrittsdatum: "2022-03-01",
    austrittsdatum: null,
    status: "passiv",
    beitragskategorie: "passiv",
    notizen: "Vorübergehend im Ausland",
    abteilungen: ["Fußball"],
  },
]

export function MitgliederPage() {
  const [members, setMembers] = useState<Member[]>([])
  const [loading, setLoading] = useState(true)
  const [formOpen, setFormOpen] = useState(false)
  const [editMember, setEditMember] = useState<Member | null>(null)
  const [detailMember, setDetailMember] = useState<Member | null>(null)
  const [detailOpen, setDetailOpen] = useState(false)

  const fetchMembers = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/members`)
      if (!res.ok) throw new Error("API error")
      const data = await res.json()
      setMembers(data.items ?? data)
    } catch {
      // Fallback to mock data
      setMembers(mockMembers)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchMembers()
  }, [fetchMembers])

  function handleRowClick(member: Member) {
    setDetailMember(member)
    setDetailOpen(true)
  }

  function handleNewMember() {
    setEditMember(null)
    setFormOpen(true)
  }

  function handleEditFromDetail(member: Member) {
    setDetailOpen(false)
    setEditMember(member)
    setFormOpen(true)
  }

  async function handleFormSubmit(data: MemberFormData) {
    const url = editMember
      ? `${API_BASE}/members/${editMember.id}`
      : `${API_BASE}/members`
    const method = editMember ? "PUT" : "POST"

    try {
      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      })
      if (!res.ok) throw new Error("API error")
    } catch {
      // In mock mode, simulate locally
      if (editMember) {
        setMembers((prev) =>
          prev.map((m) =>
            m.id === editMember.id ? { ...m, ...data } : m
          )
        )
      } else {
        const newMember: Member = {
          id: Date.now(),
          mitgliedsnummer: `M-${String(members.length + 1).padStart(3, "0")}`,
          ...data,
          eintrittsdatum: new Date().toISOString().split("T")[0],
          austrittsdatum: null,
          status: "aktiv",
          abteilungen: [],
        }
        setMembers((prev) => [...prev, newMember])
      }
    }
    await fetchMembers()
  }

  async function handleCancelMembership(member: Member) {
    try {
      const res = await fetch(`${API_BASE}/members/${member.id}/cancel`, {
        method: "POST",
      })
      if (!res.ok) throw new Error("API error")
    } catch {
      // Mock: update locally
      setMembers((prev) =>
        prev.map((m) =>
          m.id === member.id
            ? {
                ...m,
                status: "gekuendigt" as const,
                austrittsdatum: new Date().toISOString().split("T")[0],
              }
            : m
        )
      )
    }
  }

  async function handleAddDepartment(memberId: number, department: string) {
    try {
      const res = await fetch(
        `${API_BASE}/members/${memberId}/departments`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ department }),
        }
      )
      if (!res.ok) throw new Error("API error")
    } catch {
      // Mock
      setMembers((prev) =>
        prev.map((m) =>
          m.id === memberId
            ? { ...m, abteilungen: [...m.abteilungen, department] }
            : m
        )
      )
      setDetailMember((prev) =>
        prev && prev.id === memberId
          ? { ...prev, abteilungen: [...prev.abteilungen, department] }
          : prev
      )
    }
  }

  async function handleRemoveDepartment(memberId: number, department: string) {
    try {
      const res = await fetch(
        `${API_BASE}/members/${memberId}/departments/${encodeURIComponent(department)}`,
        { method: "DELETE" }
      )
      if (!res.ok) throw new Error("API error")
    } catch {
      // Mock
      setMembers((prev) =>
        prev.map((m) =>
          m.id === memberId
            ? { ...m, abteilungen: m.abteilungen.filter((d) => d !== department) }
            : m
        )
      )
      setDetailMember((prev) =>
        prev && prev.id === memberId
          ? { ...prev, abteilungen: prev.abteilungen.filter((d) => d !== department) }
          : prev
      )
    }
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Mitglieder</h1>
          <p className="text-muted-foreground">
            Verwalten Sie die Mitglieder Ihres Vereins.
          </p>
        </div>
        <button
          onClick={handleNewMember}
          className="inline-flex h-9 items-center justify-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow hover:bg-primary/90"
        >
          <Plus className="h-4 w-4" />
          Neues Mitglied
        </button>
      </div>

      {/* Table */}
      {loading ? (
        <div className="flex h-64 items-center justify-center">
          <p className="text-muted-foreground">Laden...</p>
        </div>
      ) : (
        <MemberTable data={members} onRowClick={handleRowClick} />
      )}

      {/* Form Dialog */}
      <MemberForm
        open={formOpen}
        onOpenChange={setFormOpen}
        member={editMember}
        onSubmit={handleFormSubmit}
      />

      {/* Detail Dialog */}
      <MemberDetail
        open={detailOpen}
        onOpenChange={setDetailOpen}
        member={detailMember}
        onEdit={handleEditFromDetail}
        onCancel={handleCancelMembership}
        onAddDepartment={handleAddDepartment}
        onRemoveDepartment={handleRemoveDepartment}
      />
    </div>
  )
}
